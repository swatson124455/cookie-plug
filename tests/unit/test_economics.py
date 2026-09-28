"""Unit tests for leadgen.economics."""

import pytest

from leadgen.economics import FunnelAssumptions, ReferralTerms, account_value, funnel_plan


def test_account_value_first_year():
    terms = ReferralTerms(referral_pct=5, years_paid=1, annual_retention=1.0)
    value = account_value(400_000, terms)
    assert value.first_year_payout == 20_000
    assert value.lifetime_payout == 20_000


def test_account_value_two_years_with_retention():
    terms = ReferralTerms(referral_pct=5, years_paid=2, annual_retention=0.85)
    value = account_value(400_000, terms)
    assert value.lifetime_payout == pytest.approx(20_000 + 17_000)
    assert "lifetime=37000" in repr(value)


def test_account_value_fractional_years():
    terms = ReferralTerms(referral_pct=10, years_paid=1.5, annual_retention=1.0)
    assert account_value(100_000, terms).lifetime_payout == pytest.approx(15_000)


def test_account_value_rejects_negative():
    with pytest.raises(ValueError):
        account_value(-1, ReferralTerms(referral_pct=5, years_paid=2))


def test_funnel_plan_works_backwards():
    plan = funnel_plan(3, FunnelAssumptions())
    assert plan.handoffs_needed == 6
    assert plan.samples_needed == 12
    assert plan.calls_needed == 24
    assert plan.replies_needed == 60
    assert plan.contacts_needed == 1000
    assert "contacts=1000" in repr(plan)


def test_funnel_plan_rounds_up():
    plan = funnel_plan(1, FunnelAssumptions(contact_to_reply=0.03, reply_to_call=0.3, call_to_sample=0.3, sample_to_handoff=0.3, handoff_to_close=0.3))
    assert plan.handoffs_needed == 4
    assert plan.contacts_needed >= plan.replies_needed / 0.03


def test_funnel_plan_validation():
    with pytest.raises(ValueError):
        funnel_plan(0, FunnelAssumptions())
    with pytest.raises(ValueError):
        funnel_plan(1, FunnelAssumptions(contact_to_reply=0))


def test_contact_to_close_product():
    assumptions = FunnelAssumptions()
    assert assumptions.contact_to_close() == pytest.approx(0.06 * 0.4 * 0.5 * 0.5 * 0.5)
    assert "FunnelAssumptions" in repr(assumptions)
    assert "ReferralTerms" in repr(ReferralTerms(referral_pct=5, years_paid=2))
