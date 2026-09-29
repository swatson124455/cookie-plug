"""Unit tests for leadgen.models."""

import pytest
from pydantic import ValidationError

from leadgen.models import Category, Lead, LeadSignals, Stage


def test_website_gets_scheme_and_no_trailing_slash():
    lead = Lead(company="A", website="Example.com/")
    assert lead.website == "https://example.com"
    assert lead.domain == "example.com"


def test_domain_strips_www():
    assert Lead(company="A", website="https://www.foo.co.uk/shop").domain == "foo.co.uk"


def test_blank_company_rejected():
    with pytest.raises(ValidationError):
        Lead(company="   ")


def test_invalid_email_rejected():
    with pytest.raises(ValidationError):
        Lead(company="A", email="nope")


def test_email_lowercased():
    assert Lead(company="A", email="Jo@Example.com").email == "jo@example.com"


def test_first_name_fallback():
    assert Lead(company="A").first_name == "there"
    assert Lead(company="A", contact_name="Jordan Lee").first_name == "Jordan"


def test_touch_updates_timestamp():
    lead = Lead(company="A")
    before = lead.updated_at
    lead.touch()
    assert lead.updated_at >= before


def test_repr_is_informative(strong_lead):
    text = repr(strong_lead)
    assert "Crumb Co" in text and "cookie" in text and "score=0" in text
    assert "is_shopify" in repr(strong_lead.signals)


def test_stage_order_starts_new_ends_closed():
    assert list(Stage)[0] is Stage.NEW
    assert list(Stage)[-1] is Stage.CLOSED_LOST


def test_signals_default_empty():
    signals = LeadSignals()
    assert signals.product_count is None
    assert signals.detected_categories == []
    assert Category.COOKIE.value == "cookie"


def test_tags_add_and_remove():
    lead = Lead(company="A")
    assert lead.add_tag(" Spear ") and lead.tags == ["spear"]
    assert not lead.add_tag("spear") and not lead.add_tag("  ")
    assert lead.remove_tag("SPEAR") and lead.tags == []
    assert not lead.remove_tag("spear")
