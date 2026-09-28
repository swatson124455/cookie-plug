"""Lead discovery: CSV import, dedupe, and search-query generation.

Zero-cost discovery is deliberately manual-assisted. Protected platforms
(LinkedIn, Amazon, Faire) forbid automated scraping, so instead of a brittle
scraper this module generates the exact searches to run and ingests the CSV
you export from them. That path works today and survives site changes.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Iterable

from pydantic import ValidationError

from leadgen.models import Category, Lead, LeadSignals, Segment

REQUIRED_COLUMNS = ("company",)
OPTIONAL_COLUMNS = (
    "website", "category", "segment", "contact_name", "contact_title",
    "email", "linkedin_url", "city", "state", "source", "notes",
)
# Boolean signal columns a researcher can fill by hand. They seed
# LeadSignals so a trigger found in the news counts before enrichment runs.
SIGNAL_COLUMNS = (
    "in_national_retail", "recent_funding", "recent_retail_launch",
    "hiring_ops_or_production", "sells_wholesale", "mentions_copacker",
    "mentions_private_label", "out_of_stock", "has_pet_and_human_lines",
    "explicit_own_facility_only",
)
TRUE_VALUES = {"true", "yes", "y", "1", "x"}


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
    return Lead(**payload, signals=_row_signals(row))


def _row_signals(row: dict[str, str]) -> LeadSignals:
    """Build seed signals from any boolean columns present in the row."""
    flags = {
        column: (row.get(column) or "").strip().lower() in TRUE_VALUES
        for column in SIGNAL_COLUMNS
        if column in row
    }
    return LeadSignals(**flags)


def _coerce_enum(value: str, enum_cls: type, fallback):  # type: ignore[no-untyped-def]
    """Map a free-text CSV value onto an enum member, falling back quietly."""
    normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
    try:
        return enum_cls(normalized)
    except ValueError:
        return fallback


_NAME_SUFFIXES = ("llc", "inc", "co", "company", "corp", "ltd", "the")


def normalized_name(company: str) -> str:
    """Collapse a company name to a comparison key: lowercase, alphanumeric, no suffixes."""
    words = re.sub(r"[^a-z0-9 ]", " ", company.lower()).split()
    kept = [w for w in words if w not in _NAME_SUFFIXES]
    return "".join(kept)


def dedupe(leads: Iterable[Lead]) -> list[Lead]:
    """Merge duplicates by domain, then by normalized company name.

    Two research passes often find the same brand with different amounts of
    detail. Merging keeps the website, unions the boolean signals, and joins
    the evidence notes so nothing a researcher found is lost.
    """
    by_key: dict[str, Lead] = {}
    order: list[str] = []
    name_to_key: dict[str, str] = {}
    for lead in leads:
        name_key = normalized_name(lead.company)
        known = name_to_key.get(name_key) or _containing_name(name_key, name_to_key)
        key = lead.domain if lead.domain and lead.domain in by_key else (known or lead.domain or name_key)
        if key in by_key:
            _merge_into(by_key[key], lead)
        else:
            by_key[key] = lead
            order.append(key)
        name_to_key.setdefault(name_key, key)
    return [by_key[k] for k in order]


_MIN_CONTAINMENT_LENGTH = 8


def _containing_name(name_key: str, known: dict[str, str]) -> str | None:
    """Match "mightylicious" to "mightyliciousglutenfree" and vice versa.

    Only long keys qualify so short names like "rogue" never swallow others.
    """
    if len(name_key) < _MIN_CONTAINMENT_LENGTH:
        return None
    for other, key in known.items():
        if len(other) >= _MIN_CONTAINMENT_LENGTH and (name_key in other or other in name_key):
            return key
    return None


def _merge_into(target: Lead, other: Lead) -> None:
    """Fold ``other`` into ``target`` without overwriting known facts."""
    for field in ("website", "contact_name", "contact_title", "email", "linkedin_url", "city", "state"):
        if not getattr(target, field) and getattr(other, field):
            setattr(target, field, getattr(other, field))
    if target.category == Category.OTHER:
        target.category = other.category
    if target.segment == Segment.UNKNOWN:
        target.segment = other.segment
    if other.notes and other.notes not in target.notes:
        target.notes = f"{target.notes} || {other.notes}".strip(" |")
    if other.source and other.source not in target.source:
        target.source = f"{target.source}+{other.source}"
    merged = target.signals.model_dump()
    for name, value in other.signals.model_dump().items():
        if value is True:
            merged[name] = True
    target.signals = LeadSignals(**merged)


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
