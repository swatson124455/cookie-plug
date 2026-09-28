"""Unit tests for leadgen.outreach."""

from leadgen.models import Category, Lead, LeadSignals
from leadgen.outreach import (
    SequenceTemplate,
    facility_line,
    personal_line_from_signals,
    proof_line,
    render_sequence,
)


def test_render_sequence_fills_every_placeholder(strong_lead, facility, sender, sequence_template):
    touches = render_sequence(strong_lead, facility, sender, sequence_template)
    assert len(touches) == 5
    for touch in touches:
        assert "{" not in touch.body and "{" not in touch.subject
        if touch.channel == "email":
            assert "Sam Watson" in touch.body
    assert touches[0].channel == "email"
    assert touches[1].channel == "linkedin"
    assert "Jordan" in touches[0].body
    assert "OutreachTouch" in repr(touches[0])


def test_first_email_is_short(strong_lead, facility, sender, sequence_template):
    first = render_sequence(strong_lead, facility, sender, sequence_template)[0]
    assert len(first.body.split()) < 140


def test_personal_line_priority_retail_first(strong_lead):
    assert "Whole Foods" in personal_line_from_signals(strong_lead)


def test_personal_line_variants():
    def lead_with(**kwargs):
        return Lead(company="Z", signals=LeadSignals(**kwargs))

    assert "sold out" in personal_line_from_signals(lead_with(out_of_stock=True))
    assert "hiring" in personal_line_from_signals(lead_with(hiring_ops_or_production=True))
    assert "outside manufacturing" in personal_line_from_signals(lead_with(mentions_copacker=True))
    assert "wholesale" in personal_line_from_signals(lead_with(sells_wholesale=True))
    assert "worth a short note" in personal_line_from_signals(lead_with())


def test_ai_personal_line_overrides_default(strong_lead, facility, sender, sequence_template):
    touches = render_sequence(strong_lead, facility, sender, sequence_template, personal_line="Custom opener.")
    assert touches[0].body.startswith("Hi Jordan,\n\nCustom opener.")


def test_proof_line_only_uses_confirmed_certifications(facility):
    line = proof_line(facility)
    assert "fda_registered" in line
    assert "TO_CONFIRM" not in line


def test_facility_line_names_lines(facility):
    lead = Lead(company="A", category=Category.PET_TREAT)
    assert "pet treat" in facility_line(facility, lead)


def test_empty_template_renders_nothing(strong_lead, facility, sender):
    assert render_sequence(strong_lead, facility, sender, SequenceTemplate()) == []
    assert "touches=0" in repr(SequenceTemplate())
