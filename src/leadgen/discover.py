"""Lead discovery: CSV import, dedupe, and search-query generation.

Zero-cost discovery is deliberately manual-assisted. Protected platforms
(LinkedIn, Amazon, Faire) forbid automated scraping, so instead of a brittle
scraper this module generates the exact searches to run and ingests the CSV
you export from them. That path works today and survives site changes.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from pydantic import ValidationError

from leadgen.models import Category, Lead, Segment

REQUIRED_COLUMNS = ("company",)
OPTIONAL_COLUMNS = (
    "website", "category", "segment", "contact_name", "contact_title",
    "email", "linkedin_url", "city", "state", "source", "notes",
)


class ImportReport:
    """Outcome of a CSV import: what loaded, what was skipped, and why."""

    def __init__(self) -> None:
        self.leads: list[Lead] = []
        self.skipped: list[tuple[int, str]] = []

    def __repr__(self) -> str:
        return f"ImportReport(loaded={len(self.leads)}, skipped={len(self.skipped)})"


def import_csv(path: str | Path, default_source: str = "csv") -> ImportReport:
    """Load leads from a CSV with at least a ``company`` column.

    Rows with invalid data are recorded in ``report.skipped`` with the
    validation message rather than crashing the whole import.
    """
    report = ImportReport()
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"CSV is missing required columns: {missing}")
        for row_number, row in enumerate(reader, start=2):
            try:
                report.leads.append(_row_to_lead(row, default_source))
            except ValidationError as exc:
                report.skipped.append((row_number, _first_error_message(exc)))
            except ValueError as exc:
                report.skipped.append((row_number, str(exc)))
    report.leads = dedupe(report.leads)
    return report


def _first_error_message(exc: ValidationError) -> str:
    """Turn a pydantic error into one line naming the field and the problem."""
    first = exc.errors()[0]
    field = ".".join(str(part) for part in first.get("loc", ())) or "row"
    return f"{field}: {first.get('msg', 'invalid value')}"


def _row_to_lead(row: dict[str, str], default_source: str) -> Lead:
    """Convert one CSV row into a Lead, tolerating blank optional columns."""
    payload: dict[str, str] = {"company": row.get("company", "")}
    for column in OPTIONAL_COLUMNS:
        value = (row.get(column) or "").strip()
        if value:
            payload[column] = value
    payload.setdefault("source", default_source)
    payload["category"] = _coerce_enum(payload.get("category", ""), Category, Category.OTHER).value
    payload["segment"] = _coerce_enum(payload.get("segment", ""), Segment, Segment.UNKNOWN).value
    return Lead(**payload)


def _coerce_enum(value: str, enum_cls: type, fallback):  # type: ignore[no-untyped-def]
    """Map a free-text CSV value onto an enum member, falling back quietly."""
    normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
    try:
        return enum_cls(normalized)
    except ValueError:
        return fallback


def dedupe(leads: Iterable[Lead]) -> list[Lead]:
    """Drop duplicates by domain (or lowercase company name when no website)."""
    seen: set[str] = set()
    unique: list[Lead] = []
    for lead in leads:
        key = lead.domain or lead.company.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(lead)
    return unique


SEARCH_TEMPLATES: dict[str, list[str]] = {
    "google": [
        'site:linkedin.com/in "founder" "{category}" brand',
        '"{category}" brand "now available at" (Target OR "Whole Foods" OR Sprouts OR Chewy)',
        '"{category}" "looking for a co-packer" OR "co-manufacturer"',
        '"{category}" startup raises seed OR "series a" 2026',
        '"{category}" "sold out" "restock" shopify',
        'site:faire.com "{category}"',
        'site:kickstarter.com "{category}"',
    ],
    "linkedin_jobs": [
        '"production manager" {category}',
        '"co-packer manager" OR "co-manufacturing manager" {category}',
        '"supply chain" {category} brand',
    ],
    "linkedin_people": [
        'founder {category} brand',
        '"head of operations" {category}',
        '"VP operations" pet food OR pet treats',
    ],
    "amazon": [
        'best sellers {category} (filter: small brands, 4+ stars, 500+ reviews)',
    ],
    "trade_shows": [
        'Expo West exhibitor list {category}',
        'SuperZoo exhibitor list pet treats',
        'Global Pet Expo exhibitor list',
        'Sweets & Snacks Expo exhibitor list',
        'Fancy Food Show exhibitor list bakery',
    ],
}

CATEGORY_SEARCH_TERMS: dict[Category, str] = {
    Category.COOKIE: "cookie",
    Category.BAKERY: "baked goods",
    Category.PET_TREAT: "dog treats",
    Category.PET_FOOD: "pet food",
    Category.SNACK: "snack",
    Category.OTHER: "food",
}


def search_queries(category: Category) -> dict[str, list[str]]:
    """Return ready-to-paste search strings for one category, keyed by channel."""
    term = CATEGORY_SEARCH_TERMS[category]
    return {channel: [q.format(category=term) for q in queries] for channel, queries in SEARCH_TEMPLATES.items()}
