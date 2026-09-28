"""Facility profile loading and validation.

The facility profile (``config/facility.yaml``) is the source of truth for
what the partner can produce. Scoring uses it for category fit and outreach
uses it for proof lines. Fields still marked ``TO_CONFIRM`` are surfaced so
they never leak into a customer-facing message.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from leadgen.models import Category

TO_CONFIRM = "TO_CONFIRM"


class FacilityProfile(BaseModel):
    """Typed view of the facility config."""

    name: str
    categories: list[Category]
    services: dict[str, bool] = Field(default_factory=dict)
    certifications: dict[str, Any] = Field(default_factory=dict)
    commercial: dict[str, Any] = Field(default_factory=dict)
    location: dict[str, Any] = Field(default_factory=dict)

    def unconfirmed_fields(self) -> list[str]:
        """Return dotted paths of every field still marked TO_CONFIRM.

        Commercial numbers left at zero count as unconfirmed too, because a
        zero MOQ or lead time is never a real answer.
        """
        pending: list[str] = []
        for section_name in ("certifications", "commercial", "location"):
            section = getattr(self, section_name)
            for key, value in section.items():
                if _is_unconfirmed(section_name, key, value):
                    pending.append(f"{section_name}.{key}")
        if self.name.upper().startswith("PARTNER FACILITY"):
            pending.append("name")
        return pending

    def confirmed_certifications(self) -> list[str]:
        """Certifications safe to mention in outreach (truthy and confirmed)."""
        safe: list[str] = []
        for key, value in self.certifications.items():
            if value is True or (isinstance(value, str) and value and value != TO_CONFIRM):
                safe.append(key if value is True else f"{key}: {value}")
        return safe

    def supports(self, category: Category) -> bool:
        """Whether the facility runs a line for this category."""
        return category in self.categories

    def spare_capacity_pct(self) -> int:
        return int(self.commercial.get("spare_capacity_pct", 0))

    def __repr__(self) -> str:
        cats = ",".join(c.value for c in self.categories)
        return f"FacilityProfile(name={self.name!r}, categories=[{cats}])"


def _is_unconfirmed(section: str, key: str, value: Any) -> bool:
    """A field is unconfirmed if it carries the marker or is a placeholder zero."""
    if value == TO_CONFIRM:
        return True
    is_placeholder_number = isinstance(value, (int, float)) and value == 0
    return section == "commercial" and key != "spare_capacity_pct" and is_placeholder_number


def load_facility(path: str | Path = "config/facility.yaml") -> FacilityProfile:
    """Load and validate the facility profile from YAML."""
    with open(path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return FacilityProfile(
        name=str(raw.get("name", "Partner Facility")),
        categories=[Category(c) for c in raw.get("categories", [])],
        services={k: bool(v) for k, v in (raw.get("services") or {}).items()},
        certifications=dict(raw.get("certifications") or {}),
        commercial=dict(raw.get("commercial") or {}),
        location=dict(raw.get("location") or {}),
    )
