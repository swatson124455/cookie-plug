"""The facility facts the site is allowed to say, derived from confirmed config only.

Everything a page states about the facility passes through ``FacilityFacts``.
A field still marked ``TO_CONFIRM`` (or a commercial number left at zero)
never becomes a fact, so filling in ``config/facility.yaml`` is the only way
to make the site say more.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from leadgen.facility import FacilityProfile
from leadgen.website.config import SiteConfig


@dataclass(frozen=True)
class Line:
    """A production line and its landing page."""

    key: str
    label: str
    slug: str
    open: bool


@dataclass(frozen=True)
class Service:
    """A turnkey service with a one-sentence explanation."""

    key: str
    label: str
    blurb: str


@dataclass(frozen=True)
class Fact:
    """A confirmed number shown in the facts panel and on the capabilities page."""

    label: str
    value: str


LINES: dict[str, tuple[str, str]] = {
    "cookie": ("Cookies", "cookie-co-packer"),
    "bakery": ("Baked goods", "bakery-co-packer"),
    "pet_treat": ("Pet treats", "dog-treat-co-packer"),
    "pet_food": ("Pet food", "pet-food-co-packer"),
}

SERVICES: tuple[tuple[str, str, str], ...] = (
    ("formulation", "Formulation and R&D",
     "A production recipe from your kitchen recipe, a product you want matched, or a concept, refined until you approve the sample."),
    ("contract_manufacturing", "Contract manufacturing", "Your recipe, made to your written spec, run after run."),
    ("private_label", "Private label", "No recipe yet? Start from one the facility develops with you, under your brand."),
    ("packaging", "Packaging", "Your product packed into its retail format."),
    ("labeling", "Labeling", "The label itself: ingredient statement, allergen declaration, and the other required elements."),
    ("nutrition_panels", "Nutrition panels", "Nutrition Facts panels and label compliance before anything prints."),
    ("shelf_ready", "Shelf-ready case packs", "Case packs and pallets built to your retailer's specifications."),
)

CERTIFICATIONS: dict[str, str] = {
    "fda_registered": "FDA-registered facility",
    "sqf": "SQF",
    "organic": "Certified organic",
    "gluten_free": "Gluten-free certified",
    "kosher": "Kosher",
    "non_gmo": "Non-GMO Project",
    "aafco_pet": "AAFCO-compliant pet formulations",
    "allergen_controlled_lines": "Allergen-controlled lines",
}

NUMBERS: tuple[tuple[str, str, str], ...] = (
    ("min_order_units", "Minimum run", "{value:,} units"),
    ("sampling_turnaround_days", "Benchmark sample", "about {value} days"),
    ("typical_lead_time_weeks", "Lead time, PO to ship", "about {value} weeks"),
    ("onboarding_weeks", "First production run", "about {value} weeks after approval"),
)


@dataclass
class FacilityFacts:
    """What the site may say about the facility, and nothing more."""

    lines: list[Line]
    services: list[Service]
    certifications: list[str]
    numbers: list[Fact]
    location: str = ""
    ships_nationwide: bool = False
    multiple_skus: bool = False
    as_of: str = ""
    confirmed: dict[str, Any] = field(default_factory=dict)

    @property
    def open_lines(self) -> list[Line]:
        """Lines with open capacity this month."""
        return [line for line in self.lines if line.open]

    def open_line_labels(self) -> str:
        """``Cookies, Baked goods, and Pet treats`` style list for sentences."""
        labels = [line.label.lower() if index else line.label for index, line in enumerate(self.open_lines)]
        if len(labels) <= 2:
            return " and ".join(labels)
        return ", ".join(labels[:-1]) + ", and " + labels[-1]

    def value(self, dotted: str) -> Any:
        """A confirmed config value by dotted path (``commercial.min_order_units``), else None."""
        return self.confirmed.get(dotted)

    def __repr__(self) -> str:
        return f"FacilityFacts(lines={len(self.lines)}, services={len(self.services)}, certifications={len(self.certifications)})"


def _confirmed_values(facility: FacilityProfile) -> dict[str, Any]:
    """Every certification, commercial, and location value that is confirmed and meaningful."""
    pending = set(facility.unconfirmed_fields())
    values: dict[str, Any] = {}
    for section in ("certifications", "commercial", "location"):
        for key, raw in getattr(facility, section).items():
            path = f"{section}.{key}"
            if path not in pending and raw not in (None, "", False, 0):
                values[path] = raw
    return values


def _certifications(facility: FacilityProfile) -> list[str]:
    """Human labels for confirmed certifications, with detail when given (``SQF (Level 2)``)."""
    labels: list[str] = []
    for item in facility.confirmed_certifications():
        key, _, detail = item.partition(": ")
        label = CERTIFICATIONS.get(key, key.replace("_", " "))
        if not detail:
            labels.append(label)
        else:
            labels.append(detail if label.lower() in detail.lower() else f"{label} ({detail})")
    return labels


def _numbers(confirmed: dict[str, Any]) -> list[Fact]:
    """Confirmed commercial numbers, formatted for display."""
    facts: list[Fact] = []
    for key, label, template in NUMBERS:
        raw = confirmed.get(f"commercial.{key}")
        if isinstance(raw, (int, float)) and raw > 0:
            facts.append(Fact(label, template.format(value=int(raw))))
    return facts


def _location(confirmed: dict[str, Any]) -> str:
    """``City, ST`` once both are confirmed, else empty."""
    city, state = confirmed.get("location.city"), confirmed.get("location.state")
    return f"{city}, {state}" if city and state else ""


def build_facts(facility: FacilityProfile, cfg: SiteConfig) -> FacilityFacts:
    """Combine confirmed facility config with this month's capacity status."""
    confirmed = _confirmed_values(facility)
    open_now = set(cfg.capacity.lines)
    lines = [Line(category.value, *LINES[category.value], open=category.value in open_now)
             for category in facility.categories if category.value in LINES]
    services = [Service(key, label, blurb) for key, label, blurb in SERVICES if facility.services.get(key)]
    return FacilityFacts(
        lines=lines,
        services=services,
        certifications=_certifications(facility),
        numbers=_numbers(confirmed),
        location=_location(confirmed),
        ships_nationwide=confirmed.get("location.ships_nationwide") is True,
        multiple_skus=confirmed.get("commercial.multiple_skus_welcome") is True,
        as_of=cfg.capacity.label(),
        confirmed=confirmed,
    )
