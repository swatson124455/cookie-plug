"""Unit tests for leadgen.ai with a fake Anthropic client. No network."""

from types import SimpleNamespace

import anthropic
import httpx
import pytest

from leadgen.ai import (
    ClaudeQualifier,
    OutreachDraft,
    QualifierError,
    RuleBasedQualifier,
    build_qualifier,
    lead_facts,
)
from leadgen.models import AiAssessment, Category, Lead, LeadSignals


class FakeMessages:
    def __init__(self, parsed=None, stop_reason="end_turn", error=None):
        self.parsed = parsed
        self.stop_reason = stop_reason
        self.error = error
        self.calls: list[dict] = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(parsed_output=self.parsed, stop_reason=self.stop_reason)


def fake_client(**kwargs):
    return SimpleNamespace(messages=FakeMessages(**kwargs))


def _api_error(cls, status):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(status, request=request)
    return cls("err", response=response, body=None)


def test_lead_facts_contains_signals_and_facility(strong_lead, facility):
    facts = lead_facts(strong_lead, facility)
    assert "in_national_retail" in facts
    assert "whole foods" in facts
    assert "cookie, bakery, pet_treat, pet_food" in facts
    assert "40%" in facts


def test_claude_qualifier_assess_uses_structured_output(strong_lead, facility, monkeypatch):
    monkeypatch.chdir(pytest.importorskip("pathlib").Path(__file__).resolve().parents[2])
    expected = AiAssessment(fit_score=88, reasoning="r", likely_pain="p", best_angle="a", personal_line="line")
    client = fake_client(parsed=expected)
    qualifier = ClaudeQualifier(client=client, model="claude-opus-5")
    result = qualifier.assess(strong_lead, facility)
    assert result == expected
    call = client.messages.calls[0]
    assert call["model"] == "claude-opus-5"
    assert call["output_format"] is AiAssessment
    assert "senior business-development analyst" in call["system"]
    assert "ClaudeQualifier" in repr(qualifier)


def test_claude_qualifier_draft_email(strong_lead, facility, sender, monkeypatch):
    monkeypatch.chdir(pytest.importorskip("pathlib").Path(__file__).resolve().parents[2])
    draft = OutreachDraft(subject="s", body="b")
    client = fake_client(parsed=draft)
    assert ClaudeQualifier(client=client).draft_email(strong_lead, facility, sender) == draft
    assert "Sam Watson" in client.messages.calls[0]["messages"][0]["content"]
    assert "OutreachDraft" in repr(draft)


@pytest.mark.parametrize(
    "error, message",
    [
        (_api_error(anthropic.AuthenticationError, 401), "API key"),
        (_api_error(anthropic.RateLimitError, 429), "rate limit"),
        (_api_error(anthropic.InternalServerError, 500), "500"),
        (anthropic.APIConnectionError(request=httpx.Request("POST", "https://x")), "could not reach"),
    ],
)
def test_claude_qualifier_error_chain(strong_lead, facility, monkeypatch, error, message):
    monkeypatch.chdir(pytest.importorskip("pathlib").Path(__file__).resolve().parents[2])
    qualifier = ClaudeQualifier(client=fake_client(error=error))
    with pytest.raises(QualifierError, match=message):
        qualifier.assess(strong_lead, facility)


def test_claude_qualifier_refusal_and_empty(strong_lead, facility, monkeypatch):
    monkeypatch.chdir(pytest.importorskip("pathlib").Path(__file__).resolve().parents[2])
    with pytest.raises(QualifierError, match="declined"):
        ClaudeQualifier(client=fake_client(parsed=None, stop_reason="refusal")).assess(strong_lead, facility)
    with pytest.raises(QualifierError, match="no structured output"):
        ClaudeQualifier(client=fake_client(parsed=None)).assess(strong_lead, facility)


def test_rule_based_qualifier_mirrors_score(strong_lead, facility):
    strong_lead.score = 72
    strong_lead.score_reasons = ["x"]
    assessment = RuleBasedQualifier().assess(strong_lead, facility)
    assert assessment.fit_score == 72
    assert assessment.disqualifiers == []
    assert "capacity" in assessment.likely_pain
    assert "Whole Foods" in assessment.personal_line
    assert repr(RuleBasedQualifier()) == "RuleBasedQualifier()"


def test_rule_based_qualifier_flags_disqualifiers(facility):
    lead = Lead(company="A", category=Category.SNACK, signals=LeadSignals(explicit_own_facility_only=True))
    assessment = RuleBasedQualifier().assess(lead, facility)
    assert len(assessment.disqualifiers) == 2


def test_rule_based_draft_email_uses_template(strong_lead, facility, sender, monkeypatch):
    monkeypatch.chdir(pytest.importorskip("pathlib").Path(__file__).resolve().parents[2])
    draft = RuleBasedQualifier().draft_email(strong_lead, facility, sender)
    assert "Crumb Co" in draft.subject
    assert "Jordan" in draft.body


def test_build_qualifier_picks_by_env(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    assert isinstance(build_qualifier(), RuleBasedQualifier)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("LEADGEN_MODEL", "claude-opus-5")
    assert isinstance(build_qualifier(), ClaudeQualifier)
