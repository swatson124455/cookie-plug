"""Unit tests for leadgen.discovery with a fake Anthropic client."""

from types import SimpleNamespace

import anthropic
import httpx
import pytest

from leadgen.ai import QualifierError
from leadgen.discovery import DiscoveredBrand, brand_to_lead, discover, parse_discovery, queries_for
from leadgen.models import Category, Segment

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


JSON = '''Here are the results:
[{"company": "Crumb Co", "website": "crumbco.com", "category": "cookie", "trigger": "transition", "evidence": "outgrew its commissary", "url": "https://e/1", "founder": "Jordan Lee, Founder"},
 {"company": "X", "website": "", "category": "cookie", "trigger": "", "evidence": "", "url": "", "founder": ""},
 {"company": "Barkery Lane", "category": "pet_treat", "trigger": "funding", "evidence": "raised", "url": "https://e/2", "founder": "Priya Nair"},
 {"bad": true}]'''


def test_queries_fill_year():
    assert all("2027" in q for q in queries_for(Category.COOKIE, 2027))
    assert queries_for(Category.OTHER) == []


def test_parse_discovery_validates_entries():
    brands = parse_discovery(JSON)
    assert [b.company for b in brands] == ["Crumb Co", "Barkery Lane"]
    assert parse_discovery("no json here") == []
    assert parse_discovery("[not valid") == []
    assert "DiscoveredBrand" in repr(brands[0])


def test_discover_runs_with_pause_turn(monkeypatch):
    monkeypatch.chdir(REPO)
    messages = _FakeMessages([_resp("pause_turn"), _resp("end_turn", JSON)])
    brands = discover(Category.COOKIE, SimpleNamespace(messages=messages))
    assert len(brands) == 2 and len(messages.calls) == 2
    assert "cookie" in messages.calls[0]["messages"][0]["content"]
    assert discover(Category.OTHER, SimpleNamespace(messages=messages)) == []


def test_discover_errors(monkeypatch):
    monkeypatch.chdir(REPO)
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    with pytest.raises(QualifierError, match="declined"):
        discover(Category.COOKIE, SimpleNamespace(messages=_FakeMessages([_resp("refusal")])))
    with pytest.raises(QualifierError, match="could not reach"):
        discover(Category.COOKIE, SimpleNamespace(messages=_FakeMessages([anthropic.APIConnectionError(request=request)])))


def test_brand_to_lead_maps_fields():
    brand = DiscoveredBrand(company="Crumb Co", website="crumbco.com", category=Category.COOKIE, trigger="transition", evidence="e", url="https://e/1", founder="Jordan Lee, Founder")
    lead = brand_to_lead(brand, Category.COOKIE)
    assert lead.segment == Segment.EMERGING_BRAND and lead.signals.transitioning
    assert lead.contact_name == "Jordan Lee" and lead.contact_title == "Founder"
    assert lead.source == "discover_cookie" and "https://e/1" in lead.notes
    plain = brand_to_lead(DiscoveredBrand(company="Yum Co", founder="Priya Nair"), Category.PET_TREAT)
    assert plain.contact_name == "Priya Nair" and plain.contact_title == "" and plain.category == Category.PET_TREAT
