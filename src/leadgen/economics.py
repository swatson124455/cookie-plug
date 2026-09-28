"""Deal economics and funnel math.

Two questions drive every prioritization decision in this partnership:
what is one account worth to me, and how many people do I need to contact
to land one. Both are simple arithmetic, but writing them down keeps the
weekly plan honest.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field


class ReferralTerms(BaseModel):
    """Commercial terms of the referral agreement."""

    referral_pct: float = Field(gt=0, lt=100, description="Percent of each purchase paid to you")
    years_paid: float = Field(gt=0, description="How long repurchases keep paying")
    annual_retention: float = Field(ge=0, le=1, default=0.85, description="Share of accounts still buying each year")

    def __repr__(self) -> str:
        return f"ReferralTerms(pct={self.referral_pct}, years={self.years_paid})"


class AccountValue(BaseModel):
    """Expected referral income from one account."""

    first_year_payout: float
    lifetime_payout: float
    years_paid: float

    def __repr__(self) -> str:
        return f"AccountValue(first_year={self.first_year_payout:.0f}, lifetime={self.lifetime_payout:.0f})"


def account_value(annual_purchases: float, terms: ReferralTerms) -> AccountValue:
    """Payout from an account buying ``annual_purchases`` dollars per year.

    Retention decays the expected purchases each year, so a two-year term at
    85% retention pays roughly 1.85 years of the first-year amount.
    """
    if annual_purchases < 0:
        raise ValueError("annual_purchases must be non-negative")
    rate = terms.referral_pct / 100.0
    first_year = annual_purchases * rate
    lifetime = 0.0
    remaining_years = terms.years_paid
    survival = 1.0
    while remaining_years > 0:
        fraction = min(1.0, remaining_years)
        lifetime += first_year * survival * fraction
        survival *= terms.annual_retention
        remaining_years -= 1
    return AccountValue(first_year_payout=round(first_year, 2), lifetime_payout=round(lifetime, 2), years_paid=terms.years_paid)


class FunnelAssumptions(BaseModel):
    """Stage-to-stage conversion assumptions. Defaults are conservative
    cold-outbound benchmarks for well-personalized B2B manufacturing outreach."""

    contact_to_reply: float = Field(default=0.06, ge=0, le=1)
    reply_to_call: float = Field(default=0.40, ge=0, le=1)
    call_to_sample: float = Field(default=0.50, ge=0, le=1)
    sample_to_handoff: float = Field(default=0.50, ge=0, le=1)
    handoff_to_close: float = Field(default=0.50, ge=0, le=1)

    def contact_to_close(self) -> float:
        return (
            self.contact_to_reply * self.reply_to_call * self.call_to_sample
            * self.sample_to_handoff * self.handoff_to_close
        )

    def __repr__(self) -> str:
        return f"FunnelAssumptions(contact_to_close={self.contact_to_close():.4f})"


class FunnelPlan(BaseModel):
    """How many leads each stage needs to hit a target number of closes."""

    target_closes: int
    contacts_needed: int
    replies_needed: int
    calls_needed: int
    samples_needed: int
    handoffs_needed: int

    def __repr__(self) -> str:
        return f"FunnelPlan(target={self.target_closes}, contacts={self.contacts_needed})"


def funnel_plan(target_closes: int, assumptions: FunnelAssumptions) -> FunnelPlan:
    """Work backwards from closes to the contacts required, rounding up."""
    if target_closes < 1:
        raise ValueError("target_closes must be at least 1")
    handoffs = _ceil_div(target_closes, assumptions.handoff_to_close)
    samples = _ceil_div(handoffs, assumptions.sample_to_handoff)
    calls = _ceil_div(samples, assumptions.call_to_sample)
    replies = _ceil_div(calls, assumptions.reply_to_call)
    contacts = _ceil_div(replies, assumptions.contact_to_reply)
    return FunnelPlan(
        target_closes=target_closes, contacts_needed=contacts, replies_needed=replies,
        calls_needed=calls, samples_needed=samples, handoffs_needed=handoffs,
    )


def _ceil_div(count: int, rate: float) -> int:
    if rate <= 0:
        raise ValueError("conversion rates must be positive")
    return math.ceil(count / rate)
