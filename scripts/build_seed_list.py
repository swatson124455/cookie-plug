"""Merge researched CSVs into one seed list, score it, and write review files.

Usage: python scripts/build_seed_list.py <csv> [<csv> ...]

Outputs (committed, so the seed list is versioned):
  leads/seed_list.csv         merged and deduped input rows
  leads/seed_list_scored.csv  every lead with score, reasons, and seed signals
  leads/top_drafts.md         the day-0 email for the top-ranked leads

Enrichment is not run here because it needs network access to each brand's
site; run ``leadgen enrich`` on a machine with open egress, then ``leadgen score``.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from leadgen.discover import OPTIONAL_COLUMNS, SIGNAL_COLUMNS, dedupe, import_csv  # noqa: E402
from leadgen.facility import load_facility  # noqa: E402
from leadgen.models import Lead  # noqa: E402
from leadgen.outreach import SenderIdentity, load_sequence, render_sequence  # noqa: E402
from leadgen.scoring import apply_score, load_weights  # noqa: E402

LEADS_DIR = Path("leads")
OVERRIDES_PATH = LEADS_DIR / "overrides.csv"
TOP_N = 15
WEAK_FIT_CAP = 34  # weak product fits never outrank a real fit; they stay in nurture

# Companies the research surfaced as triggers but that are not realistic
# buyers for this facility: national conglomerates, retailers whose recall
# concerned a supplier, and fresh, frozen, or raw-only brands.
EXCLUSIONS: dict[str, str] = {
    "general mills": "conglomerate; plant closure is a market signal, not a lead",
    "hostess": "conglomerate (J.M. Smucker)",
    "natures bakery": "owned by Mars",
    "hain celestial group": "conglomerate",
    "lidl us": "retailer; recall concerned an imported supplier",
    "lunds byerlys": "retailer; recall concerned a supplier",
    "target favorite day bakery": "retailer; recall concerned a Canadian supplier",
    "girl scouts of usa": "licensor; BARK is the manufacturer (kept separately)",
    "farmers dog": "fresh-only pet food, facility bakes",
    "omas pride": "raw pet food",
    "albrights raw pet food": "raw pet food",
}


def merge(paths: list[Path]) -> list[Lead]:
    """Import every CSV, report skips, and dedupe across files."""
    leads: list[Lead] = []
    for path in paths:
        report = import_csv(path, default_source=path.stem.replace("leads_", ""))
        print(f"{path.name}: loaded {len(report.leads)}, skipped {len(report.skipped)}")
        for row_number, reason in report.skipped:
            print(f"  row {row_number}: {reason}")
        leads.extend(report.leads)
    unique = dedupe(leads)
    kept = [lead for lead in unique if not _excluded(lead)]
    print(f"merged {len(leads)} -> {len(unique)} unique -> {len(kept)} after exclusions")
    return kept


def apply_overrides(leads: list[Lead], path: Path) -> list[Lead]:
    """Merge hand-verified facts from ``leads/overrides.csv``.

    Columns: company, website, contact_name, contact_title, email, fit_note,
    exclude_reason. A row with exclude_reason drops the lead; other columns
    fill blanks; fit_note is appended to notes and, when it starts with
    "WEAK FIT", the lead is demoted so it never ranks above real fits.
    """
    if not path.exists():
        return leads
    from leadgen.discover import normalized_name

    overrides = _load_overrides(path)
    kept: list[Lead] = []
    for lead in leads:
        row = overrides.get(normalized_name(lead.company))
        if row is None:
            kept.append(lead)
            continue
        if (row.get("exclude_reason") or "").strip():
            print(f"  excluded {lead.company}: {row['exclude_reason']}")
            continue
        # Hand-verified facts win over research rows; a contact chosen on
        # purpose (the ops lead, not the celebrity founder) must stick.
        if (row.get("contact_name") or "").strip():
            lead.contact_name = row["contact_name"].strip()
            lead.contact_title = (row.get("contact_title") or "").strip()
        for field in ("website", "email"):
            if (row.get(field) or "").strip():
                setattr(lead, field, row[field].strip())
        note = (row.get("fit_note") or "").strip()
        if note:
            lead.notes = f"{lead.notes} || {note}".strip(" |")
            if "TRANSITION:" in note.upper() or "CHANGE:" in note.upper():
                lead.signals.transitioning = True
            if "OWN PLANT:" in note.upper() or "OVERFLOW ONLY:" in note.upper():
                lead.signals.transitioning = False
                lead.signals.explicit_own_facility_only = False
            if "seeking" in note.lower() or "looking for a co-packer" in note.lower() or "third-party manufacturing" in note.lower():
                lead.signals.seeking_copacker = True
        kept.append(lead)
    return kept


def _load_overrides(path: Path) -> dict[str, dict[str, str]]:
    """Read overrides, merging repeated company rows: blanks fill, notes join."""
    from leadgen.discover import normalized_name

    merged: dict[str, dict[str, str]] = {}
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            key = normalized_name(row["company"])
            current = merged.setdefault(key, {})
            for field, value in row.items():
                value = (value or "").strip()
                if not value:
                    continue
                if field == "fit_note" and current.get(field):
                    current[field] = f"{current[field]} || {value}"
                elif not current.get(field):
                    current[field] = value
    return merged


def _excluded(lead: Lead) -> bool:
    from leadgen.discover import normalized_name

    key = normalized_name(lead.company)
    for name, reason in EXCLUSIONS.items():
        if normalized_name(name) in key:
            print(f"  excluded {lead.company}: {reason}")
            return True
    return False


def write_seed_csv(leads: list[Lead], path: Path) -> None:
    columns = ["company", *OPTIONAL_COLUMNS, *SIGNAL_COLUMNS]
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for lead in leads:
            row = lead.model_dump(mode="json")
            signals = {name: ("true" if getattr(lead.signals, name) else "") for name in SIGNAL_COLUMNS}
            writer.writerow({**{c: row.get(c, "") for c in columns}, **signals})


def write_scored_csv(leads: list[Lead], path: Path) -> None:
    columns = ["score", "company", "website", "category", "segment", "contact_name", "contact_title",
               "email", "city", "state", "source", "score_reasons", "notes"]
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for lead in leads:
            row = lead.model_dump(mode="json")
            row["score_reasons"] = "; ".join(lead.score_reasons)
            writer.writerow({c: row.get(c, "") for c in columns})


def write_top_drafts(leads: list[Lead], path: Path) -> None:
    facility = load_facility()
    template = load_sequence()
    sender = SenderIdentity(name="[Your name]", title="Partnerships")
    lines = ["# Day-0 drafts for the top-ranked seed leads", "",
             "Generated by `scripts/build_seed_list.py`. Edit the first line by hand where the evidence in `notes` gives something sharper.", ""]
    for lead in leads[:TOP_N]:
        first = render_sequence(lead, facility, sender, template)[0]
        lines += [f"## {lead.score} · {lead.company} ({lead.category.value}, {lead.segment.value})",
                  f"- Website: {lead.website or 'unknown'}",
                  f"- Evidence: {lead.notes or 'none recorded'}",
                  f"- Score reasons: {'; '.join(lead.score_reasons)}", "",
                  f"**Subject:** {first.subject}", "", "```", first.body, "```", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str]) -> int:
    paths = [Path(p) for p in argv]
    if not paths:
        print(__doc__)
        return 1
    LEADS_DIR.mkdir(exist_ok=True)
    leads = apply_overrides(merge(paths), OVERRIDES_PATH)
    weights, facility = load_weights(), load_facility()
    for lead in leads:
        apply_score(lead, weights, facility)
        if ("WEAK FIT" in lead.notes.upper() or "OWN PLANT:" in lead.notes.upper()) and lead.score > WEAK_FIT_CAP:
            lead.score = WEAK_FIT_CAP
            lead.score_reasons.append("capped: weak product fit, see notes")
    leads.sort(key=lambda l: (-l.score, l.company.lower()))
    write_seed_csv(leads, LEADS_DIR / "seed_list.csv")
    write_scored_csv(leads, LEADS_DIR / "seed_list_scored.csv")
    write_top_drafts(leads, LEADS_DIR / "top_drafts.md")
    buckets = {"50+": sum(l.score >= 50 for l in leads), "35-49": sum(35 <= l.score < 50 for l in leads), "<35": sum(l.score < 35 for l in leads)}
    print(f"scored {len(leads)} leads: {buckets}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
