"""Unit tests for leadgen.triggers."""

from datetime import date
from types import SimpleNamespace

import httpx
import anthropic
import pytest

from leadgen.models import Category
from leadgen.sources import RawItem
from leadgen.triggers import (
    ClaudeExtractor,
    RuleBasedExtractor,
    TriggerExtraction,
    classify_category,
    classify_trigger,
    company_from_headline,
    extraction_to_lead,
)

REPO = __import__("pathlib").Path(__file__).resolve().parents[2]


def test_classify_category_pet_before_human():
    assert classify_category("New dog treats shaped like cookies") == Category.PET_TREAT
    assert classify_category("Brownie brand expands") == Category.BAKERY
    assert classify_category("Kombucha startup raises") == Category.OTHER


def test_classify_trigger_priority():
    assert classify_trigger("Brand recalls cookies after launching at Target") == "recall"
    assert classify_trigger("Brand raises $2M seed") == "funding"
    assert classify_trigger("Brand launches at Whole Foods") == "retail_launch"
    assert classify_trigger("Brand is hiring a production manager") == "hiring"
    assert classify_trigger("Brand unveils new flavor") == "new_product"
    assert classify_trigger("Nothing here") == ""


@pytest.mark.parametrize("title, expected", [
    ("Crumb Co launches soft-baked cookies at Target nationwide", "Crumb Co"),
    ("Barkery Lane raises $2M seed to scale dog treats", "Barkery Lane"),
    ("Heavenly Hunks Expands Beyond Cookies, Launching Dupe Loops | NOSH", "Heavenly Hunks"),
    ("Why consumers love snacks: a trend report", ""),
    ("A" * 70 + " launches thing", ""),
])
def test_company_from_headline(title, expected):
    assert company_from_headline(title) == expected


def test_rule_based_extractor_relevance():
    item = RawItem(source="rss_x", title="Crumb Co launches cookies at Target", summary="", url="u", published=date(2026, 9, 21))
    result = RuleBasedExtractor().extract(item)
    assert result.is_relevant and result.company == "Crumb Co" and result.trigger == "retail_launch"
    assert result.category == Category.COOKIE
    boring = RuleBasedExtractor().extract(RawItem(source="rss_x", title="Why consumers love snacks", summary=""))
    assert not boring.is_relevant
    assert "RuleBasedExtractor" in repr(RuleBasedExtractor())


def test_rule_based_uses_company_hint():
    item = RawItem(source="fda_recall", title="Gregory's Foods recalls cookies", company_hint="Gregory's Foods")
    result = RuleBasedExtractor().extract(item)
    assert result.company == "Gregory's Foods" and result.trigger == "recall"


def test_extraction_to_lead_sets_signal_and_notes():
    item = RawItem(source="rss_x", title="t", url="https://e.com/a", published=date(2026, 9, 21))
    lead = extraction_to_lead(item, TriggerExtraction(is_relevant=True, company="Crumb Co", website="crumbco.com", category=Category.COOKIE, trigger="funding", evidence="raised $2M"))
    assert lead is not None and lead.signals.recent_funding and lead.source == "watch_rss_x"
    assert "2026-09-21" in lead.notes and "https://e.com/a" in lead.notes and lead.domain == "crumbco.com"
    recall = extraction_to_lead(item, TriggerExtraction(is_relevant=True, company="X", category=Category.BAKERY, trigger="closure"))
    assert recall is not None and recall.signals.recent_recall
    assert extraction_to_lead(item, TriggerExtraction(is_relevant=False, company="X")) is None
    assert extraction_to_lead(item, TriggerExtraction(is_relevant=True, company="")) is None


class _FakeMessages:
    def __init__(self, parsed=None, error=None, stop_reason="end_turn"):
        self.parsed, self.error, self.stop_reason = parsed, error, stop_reason

    def parse(self, **kwargs):
        if self.error:
            raise self.error
        return SimpleNamespace(parsed_output=self.parsed, stop_reason=self.stop_reason)


def test_claude_extractor_uses_model_output(monkeypatch):
    monkeypatch.chdir(REPO)
    expected = TriggerExtraction(is_relevant=True, company="Crumb Co", category=Category.COOKIE, trigger="funding", evidence="e")
    extractor = ClaudeExtractor(SimpleNamespace(messages=_FakeMessages(parsed=expected)))
    assert extractor.extract(RawItem(source="s", title="t")) == expected
    assert "ClaudeExtractor" in repr(extractor)


def test_claude_extractor_falls_back_on_error_or_refusal(monkeypatch):
    monkeypatch.chdir(REPO)
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    error = anthropic.APIConnectionError(request=request)
    item = RawItem(source="s", title="Crumb Co launches cookies at Target")
    assert ClaudeExtractor(SimpleNamespace(messages=_FakeMessages(error=error))).extract(item).company == "Crumb Co"
    assert ClaudeExtractor(SimpleNamespace(messages=_FakeMessages(parsed=None, stop_reason="refusal"))).extract(item).trigger == "retail_launch"
