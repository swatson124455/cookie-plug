"""Unit tests for leadgen.contacts."""

from leadgen.contacts import email_candidates, name_parts, render_pattern
from leadgen.models import Lead


def test_name_parts_strips_titles_and_accents():
    assert name_parts("Dr. Mahsa Vazin") == ("mahsa", "vazin")
    assert name_parts("Jeffrey Gamsey, JD") == ("jeffrey", "gamsey")
    assert name_parts("Stéphanie Lachance-Coward") == ("stephanie", "lachancecoward")
    assert name_parts("Madonna") == ("madonna", "")
    assert name_parts("") == ("", "")


def test_render_pattern_handles_missing_last_name():
    assert render_pattern("first", "ann", "") == "ann"
    assert render_pattern("first.last", "ann", "") is None
    assert render_pattern("flast", "ann", "lee") == "alee"
    assert render_pattern("unknown", "ann", "lee") is None


def test_candidates_ranked_and_generic_last():
    lead = Lead(company="Brune Kitchen", website="brunekitchen.com", contact_name="Tania Sweis")
    addresses = [c.address for c in email_candidates(lead)]
    assert addresses[0] == "tania@brunekitchen.com"
    assert "tania.sweis@brunekitchen.com" in addresses
    assert addresses[-1] == "partnerships@brunekitchen.com"
    assert all(not c.verified for c in email_candidates(lead))


def test_known_pattern_moves_first():
    lead = Lead(company="X", website="x.com", contact_name="Ann Lee")
    first = email_candidates(lead, known_pattern="first.last")[0]
    assert first.address == "ann.lee@x.com" and first.pattern == "first.last"
    assert "EmailCandidate" in repr(first)


def test_verified_email_short_circuits():
    lead = Lead(company="X", website="x.com", contact_name="Ann Lee", email="ann@x.com")
    result = email_candidates(lead)
    assert len(result) == 1 and result[0].verified


def test_no_domain_gives_nothing_and_no_contact_gives_generic_only():
    assert email_candidates(Lead(company="X", contact_name="Ann Lee")) == []
    generic = email_candidates(Lead(company="X", website="x.com"))
    assert [c.pattern for c in generic] == ["generic"] * 5
