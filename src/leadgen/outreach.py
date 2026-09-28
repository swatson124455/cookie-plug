"""Outreach sequence rendering from YAML templates.

Templates are deterministic and free. The AI layer can supply a sharper
``personal_line``; when it is absent we derive one from enrichment signals
so a first email is never generic.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from leadgen.facility import FacilityProfile
from leadgen.models import Category, Lead, OutreachTouch

CATEGORY_NOUNS: dict[Category, str] = {
    Category.COOKIE: "cookie",
    Category.BAKERY: "bakery",
    Category.PET_TREAT: "pet treat",
    Category.PET_FOOD: "pet food",
    Category.SNACK: "snack",
    Category.OTHER: "food",
}


class SenderIdentity(BaseModel):
    """Who the message is from."""

    name: str = "Your Name"
    title: str = "Partnerships"

    def __repr__(self) -> str:
        return f"SenderIdentity(name={self.name!r})"


class SequenceTemplate(BaseModel):
    """Parsed ``config/templates/sequence.yaml``."""

    touches: list[dict[str, object]] = Field(default_factory=list)

    def __repr__(self) -> str:
        return f"SequenceTemplate(touches={len(self.touches)})"


def load_sequence(path: str | Path = "config/templates/sequence.yaml") -> SequenceTemplate:
    """Load the sequence template from YAML."""
    with open(path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return SequenceTemplate(touches=list(raw.get("touches", [])))


def personal_line_from_signals(lead: Lead) -> str:
    """Derive a specific opening line from enrichment when AI is unavailable."""
    signals = lead.signals
    if signals.retailers_mentioned:
        retailer = signals.retailers_mentioned[0].title()
        return f"Congrats on getting {lead.company} onto {retailer} shelves. That kind of retail pull usually turns production into the bottleneck fast."
    if signals.out_of_stock:
        return f"Noticed a few {lead.company} products showing sold out. A good problem, but one that usually means demand has outrun production capacity."
    if signals.hiring_ops_or_production:
        return f"Saw {lead.company} is hiring on the operations side. Brands usually do that right before they hit a capacity wall."
    if signals.mentions_copacker or signals.mentions_private_label:
        return f"It looks like {lead.company} already works with outside manufacturing partners, so you know what a good one is worth."
    if signals.sells_wholesale:
        return f"Saw {lead.company} sells wholesale. Retail accounts tend to grow faster than a small production setup can keep up with."
    return f"I have been following what {lead.company} is building and thought this was worth a short note."


def pain_line(lead: Lead) -> str:
    """One sentence naming the operational pain for the lead's segment."""
    noun = CATEGORY_NOUNS[lead.category]
    return (
        f"Most {noun} brands at your stage hit the same wall: the next retail order or "
        f"launch needs more volume than the current setup can produce, and every co-packer "
        f"they call is booked out or wants a huge minimum."
    )


def facility_line(facility: FacilityProfile, lead: Lead) -> str:
    """Describe the facility without leaking unconfirmed claims."""
    noun = CATEGORY_NOUNS[lead.category]
    lines = ", ".join(c.value.replace("_", " ") for c in facility.categories)
    return f"I work with a US manufacturer that runs {lines} lines under one roof and is a strong fit for {noun} production."


def proof_line(facility: FacilityProfile) -> str:
    """Certifications and services, confirmed ones only."""
    certs = facility.confirmed_certifications()
    cert_text = f"Certified: {', '.join(certs)}." if certs else "Certification details on request."
    return f"Formulation, production, packaging, labeling, and nutrition panels are all in-house. {cert_text}"


def cta_line() -> str:
    return "Worth a 15-minute call to see if the capacity and the specs line up?"


def render_sequence(
    lead: Lead,
    facility: FacilityProfile,
    sender: SenderIdentity,
    template: SequenceTemplate,
    personal_line: str | None = None,
) -> list[OutreachTouch]:
    """Fill every touch in the sequence for one lead."""
    fields = {
        "first_name": lead.first_name,
        "company": lead.company,
        "category_noun": CATEGORY_NOUNS[lead.category],
        "personal_line": personal_line or personal_line_from_signals(lead),
        "pain_line": pain_line(lead),
        "facility_line": facility_line(facility, lead),
        "proof_line": proof_line(facility),
        "cta_line": cta_line(),
        "sender_name": sender.name,
        "sender_title": sender.title,
    }
    rendered: list[OutreachTouch] = []
    for touch in template.touches:
        rendered.append(
            OutreachTouch(
                day=int(touch.get("day", 0)),
                channel=str(touch.get("channel", "email")),
                subject=str(touch.get("subject", "")).format(**fields),
                body=str(touch.get("body", "")).format(**fields).strip(),
            )
        )
    return rendered
