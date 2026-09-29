"""Deterministic ICP scoring.

The scorer is rule-based on purpose: it costs nothing, runs offline, is
explainable to the facility partner, and gives the AI layer a baseline to
argue with. Weights live in ``config/icp.yaml`` so they can be tuned as
reply and close data comes in.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from leadgen.facility import FacilityProfile
from leadgen.models import Category, Lead, LeadSignals


class IcpWeights(BaseModel):
    """Point values for each scoring signal."""

    category_fit: dict[str, int] = Field(default_factory=dict)
    segment: dict[str, int] = Field(default_factory=dict)
    signals: dict[str, int] = Field(default_factory=dict)
    hard_disqualifiers: list[str] = Field(default_factory=list)

    def __repr__(self) -> str:
        return f"IcpWeights(signals={len(self.signals)}, disqualifiers={len(self.hard_disqualifiers)})"


class ScoreResult(BaseModel):
    """Score plus the human-readable reasons behind it."""

    score: int
    reasons: list[str] = Field(default_factory=list)
    disqualified: bool = False

    def __repr__(self) -> str:
        return f"ScoreResult(score={self.score}, disqualified={self.disqualified})"


def load_weights(path: str | Path = "config/icp.yaml") -> IcpWeights:
    """Load scoring weights from YAML."""
    with open(path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return IcpWeights(**raw)


def _signal_points(signals: LeadSignals, weights: dict[str, int]) -> list[tuple[str, int]]:
    """Map observed signals to (reason, points) pairs."""
    checks: list[tuple[str, bool]] = [
        ("is_shopify", signals.is_shopify),
        ("sells_wholesale", signals.sells_wholesale),
        ("in_national_retail", signals.in_national_retail),
        ("mentions_copacker", signals.mentions_copacker),
        ("mentions_private_label", signals.mentions_private_label),
        ("hiring_ops_or_production", signals.hiring_ops_or_production),
        ("out_of_stock", signals.out_of_stock),
        ("recent_funding", signals.recent_funding),
        ("recent_retail_launch", signals.recent_retail_launch),
        ("recent_recall", signals.recent_recall),
        ("new_product_launch", signals.new_product_launch),
        ("has_pet_and_human_lines", signals.has_pet_and_human_lines),
        ("product_count_20_plus", (signals.product_count or 0) >= 20),
        ("product_count_under_3", signals.product_count is not None and signals.product_count < 3),
    ]
    return [(name, weights.get(name, 0)) for name, present in checks if present and name in weights]


def _is_disqualified(lead: Lead, weights: IcpWeights) -> str | None:
    """Return the disqualifier name that fires, if any."""
    no_signals = not any(v for v in lead.signals.model_dump().values() if isinstance(v, bool))
    rules = {
        "category_other_no_signals": lead.category == Category.OTHER and no_signals,
        "explicit_own_facility_only": lead.signals.explicit_own_facility_only,
    }
    for name in weights.hard_disqualifiers:
        if rules.get(name, False):
            return name
    return None


def score_lead(lead: Lead, weights: IcpWeights, facility: FacilityProfile) -> ScoreResult:
    """Score one lead against the ICP and the facility's real capabilities.

    Category points only count when the facility actually runs that line;
    a great pet-food brand is worth nothing to a cookie-only plant.
    """
    disqualifier = _is_disqualified(lead, weights)
    if disqualifier:
        return ScoreResult(score=0, reasons=[f"disqualified: {disqualifier}"], disqualified=True)

    reasons: list[str] = []
    total = 0

    category_points = weights.category_fit.get(lead.category.value, 0)
    if category_points and not facility.supports(lead.category) and lead.category != Category.SNACK:
        category_points = 0
        reasons.append(f"category {lead.category.value} not supported by facility (+0)")
    elif category_points:
        reasons.append(f"category {lead.category.value} (+{category_points})")
    total += category_points

    segment_points = weights.segment.get(lead.segment.value, 0)
    if segment_points:
        reasons.append(f"segment {lead.segment.value} (+{segment_points})")
    total += segment_points

    for name, points in _signal_points(lead.signals, weights.signals):
        reasons.append(f"{name} ({points:+d})")
        total += points

    return ScoreResult(score=max(0, min(100, total)), reasons=reasons)


def apply_score(lead: Lead, weights: IcpWeights, facility: FacilityProfile) -> Lead:
    """Score a lead and write the result back onto it."""
    result = score_lead(lead, weights, facility)
    lead.score = result.score
    lead.score_reasons = result.reasons
    lead.touch()
    return lead
