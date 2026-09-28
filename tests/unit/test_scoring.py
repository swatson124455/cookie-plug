"""Unit tests for leadgen.scoring."""

from leadgen.facility import FacilityProfile
from leadgen.models import Category, Lead, LeadSignals, Segment
from leadgen.scoring import IcpWeights, apply_score, score_lead


def test_strong_lead_scores_high(strong_lead, weights, facility):
    result = score_lead(strong_lead, weights, facility)
    assert result.score >= 70
    assert not result.disqualified
    assert any("in_national_retail" in r for r in result.reasons)


def test_weak_lead_disqualified(weak_lead, weights, facility):
    result = score_lead(weak_lead, weights, facility)
    assert result.score == 0
    assert result.disqualified
    assert "disqualified" in repr(result) or result.disqualified


def test_own_facility_disqualifies(weights, facility):
    lead = Lead(company="A", category=Category.COOKIE, signals=LeadSignals(explicit_own_facility_only=True))
    assert score_lead(lead, weights, facility).disqualified


def test_category_not_supported_gives_zero_category_points(weights):
    cookie_only = FacilityProfile(name="X", categories=[Category.COOKIE])
    lead = Lead(company="A", category=Category.PET_FOOD, segment=Segment.ESTABLISHED_BRAND)
    result = score_lead(lead, weights, cookie_only)
    assert result.score == weights.segment["established_brand"]
    assert any("not supported" in r for r in result.reasons)


def test_snack_counts_even_if_not_a_facility_line(weights, facility):
    lead = Lead(company="A", category=Category.SNACK)
    assert score_lead(lead, weights, facility).score == weights.category_fit["snack"] + weights.segment["unknown"]


def test_negative_signal_reduces_score(weights, facility):
    base = Lead(company="A", category=Category.COOKIE)
    tiny = Lead(company="B", category=Category.COOKIE, signals=LeadSignals(product_count=1))
    assert score_lead(tiny, weights, facility).score < score_lead(base, weights, facility).score


def test_score_clamped_to_100(facility):
    weights = IcpWeights(category_fit={"cookie": 90}, segment={"unknown": 50}, signals={"is_shopify": 50})
    lead = Lead(company="A", category=Category.COOKIE, signals=LeadSignals(is_shopify=True))
    assert score_lead(lead, weights, facility).score == 100


def test_apply_score_writes_back(strong_lead, weights, facility):
    apply_score(strong_lead, weights, facility)
    assert strong_lead.score > 0
    assert strong_lead.score_reasons


def test_weights_repr(weights):
    assert "IcpWeights" in repr(weights)
