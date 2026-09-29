"""Unit tests for leadgen.dossier with a fake Anthropic client."""

from types import SimpleNamespace

import anthropic
import httpx
import pytest

from leadgen.ai import QualifierError
from leadgen.dossier import WEB_SEARCH_TOOL, build_dossier, dossier_path, save_dossier
from leadgen.models import Lead

REPO = __import__("pathlib").Path(__file__).resolve().parents[2]


class _FakeMessages:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _resp(stop_reason, text=""):
    blocks = [SimpleNamespace(type="server_tool_use", name="web_search")]
    if text:
        blocks.append(SimpleNamespace(type="text", text=text))
    return SimpleNamespace(stop_reason=stop_reason, content=blocks)


def test_build_dossier_resumes_after_pause_turn(monkeypatch, facility, strong_lead):
    monkeypatch.chdir(REPO)
    messages = _FakeMessages([_resp("pause_turn"), _resp("end_turn", "**Product line**\n- cookies")])
    text = build_dossier(strong_lead, facility, SimpleNamespace(messages=messages))
    assert text.startswith("**Product line**")
    assert len(messages.calls) == 2
    assert messages.calls[0]["tools"] == [WEB_SEARCH_TOOL]
    assert messages.calls[1]["messages"][1]["role"] == "assistant"
    assert "Crumb Co" in messages.calls[0]["messages"][0]["content"]


def test_build_dossier_stops_after_max_continuations(monkeypatch, facility, strong_lead):
    monkeypatch.chdir(REPO)
    messages = _FakeMessages([_resp("pause_turn")] * 5 + [_resp("end_turn", "done")])
    with pytest.raises(QualifierError, match="no dossier text"):
        build_dossier(strong_lead, facility, SimpleNamespace(messages=messages))
    assert len(messages.calls) == 5


def test_build_dossier_error_chain_and_refusal(monkeypatch, facility, strong_lead):
    monkeypatch.chdir(REPO)
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(429, request=request)
    with pytest.raises(QualifierError, match="rate limit"):
        build_dossier(strong_lead, facility, SimpleNamespace(messages=_FakeMessages([anthropic.RateLimitError("x", response=response, body=None)])))
    with pytest.raises(QualifierError, match="declined"):
        build_dossier(strong_lead, facility, SimpleNamespace(messages=_FakeMessages([_resp("refusal")])))
    with pytest.raises(QualifierError, match="could not reach"):
        build_dossier(strong_lead, facility, SimpleNamespace(messages=_FakeMessages([anthropic.APIConnectionError(request=request)])))


def test_save_dossier_writes_file(tmp_path):
    lead = Lead(company="Crumb Co", website="crumbco.com")
    path = save_dossier(lead, "**Trigger**\n- x", directory=tmp_path)
    assert path == dossier_path(lead, tmp_path) and path.name == "crumbco_com.md"
    assert "leadgen dossier" in path.read_text(encoding="utf-8")
    assert dossier_path(Lead(company="No Site Co"), tmp_path).name == "no_site_co.md"
