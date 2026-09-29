"""SQLite-backed lead store and pipeline reporting.

A single-file database is the right size for a solo operator proving the
model. Every lead is stored as JSON alongside indexed columns for the
fields we query on, and every stage change is logged as an activity so
the funnel can be reconstructed later.
"""

from __future__ import annotations

import json
import sqlite3
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

from leadgen.models import STAGE_ORDER, Lead, Stage

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    domain_key TEXT PRIMARY KEY,
    company TEXT NOT NULL,
    category TEXT NOT NULL,
    stage TEXT NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    payload TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_leads_stage ON leads(stage);
CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score DESC);
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_key TEXT NOT NULL,
    kind TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""


def _key(lead: Lead) -> str:
    return lead.domain or lead.company.lower()


class LeadStore:
    """Persistence for leads and their activity history."""

    def __init__(self, path: str | Path = "data/leads.sqlite3") -> None:
        self.path = Path(path)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)

    def __repr__(self) -> str:
        return f"LeadStore(path={str(self.path)!r}, leads={self.count()})"

    def __enter__(self) -> "LeadStore":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        self._conn.close()

    def upsert(self, lead: Lead) -> None:
        """Insert or replace a lead keyed by domain."""
        lead.touch()
        self._conn.execute(
            """
            INSERT INTO leads (domain_key, company, category, stage, score, payload, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(domain_key) DO UPDATE SET
                company=excluded.company, category=excluded.category, stage=excluded.stage,
                score=excluded.score, payload=excluded.payload, updated_at=excluded.updated_at
            """,
            (
                _key(lead), lead.company, lead.category.value, lead.stage.value,
                lead.score, lead.model_dump_json(), lead.updated_at.isoformat(),
            ),
        )
        self._conn.commit()

    def upsert_many(self, leads: list[Lead]) -> int:
        for lead in leads:
            self.upsert(lead)
        return len(leads)

    def get(self, domain_or_company: str) -> Lead | None:
        row = self._conn.execute(
            "SELECT payload FROM leads WHERE domain_key = ?", (domain_or_company.lower(),)
        ).fetchone()
        return Lead.model_validate_json(row["payload"]) if row else None

    def list(self, stage: Stage | None = None, min_score: int = 0, limit: int = 500, tag: str | None = None) -> list[Lead]:
        """Leads ordered by score, optionally filtered by stage, minimum score, and tag."""
        query = "SELECT payload FROM leads WHERE score >= ?"
        params: list[object] = [min_score]
        if stage is not None:
            query += " AND stage = ?"
            params.append(stage.value)
        query += " ORDER BY score DESC, company ASC"
        rows = self._conn.execute(query, params).fetchall()
        leads = [Lead.model_validate_json(r["payload"]) for r in rows]
        if tag:
            wanted = tag.strip().lower()
            leads = [lead for lead in leads if wanted in lead.tags]
        return leads[:limit]

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0])

    def advance(self, domain_or_company: str, stage: Stage, note: str = "") -> Lead:
        """Move a lead to a new stage and log the transition."""
        lead = self.get(domain_or_company)
        if lead is None:
            raise KeyError(f"no lead found for {domain_or_company!r}")
        previous = lead.stage
        lead.stage = stage
        self.upsert(lead)
        self.log_activity(_key(lead), "stage_change", f"{previous.value} -> {stage.value}. {note}".strip())
        return lead

    def log_activity(self, domain_key: str, kind: str, detail: str = "") -> None:
        self._conn.execute(
            "INSERT INTO activities (domain_key, kind, detail, created_at) VALUES (?, ?, ?, ?)",
            (domain_key, kind, detail, datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()

    def activities(self, domain_or_company: str) -> list[dict[str, str]]:
        rows = self._conn.execute(
            "SELECT kind, detail, created_at FROM activities WHERE domain_key = ? ORDER BY id",
            (domain_or_company.lower(),),
        ).fetchall()
        return [dict(r) for r in rows]

    def pipeline_report(self) -> "OrderedDict[str, int]":
        """Count of leads in each stage, in funnel order, including zeros."""
        rows = self._conn.execute("SELECT stage, COUNT(*) AS n FROM leads GROUP BY stage").fetchall()
        counts = {r["stage"]: int(r["n"]) for r in rows}
        return OrderedDict((stage.value, counts.get(stage.value, 0)) for stage in STAGE_ORDER)


def conversion_rates(report: "OrderedDict[str, int]") -> dict[str, float]:
    """Cumulative reach per stage: share of all leads that got at least this far."""
    total = sum(report.values())
    if total == 0:
        return {stage: 0.0 for stage in report}
    rates: dict[str, float] = {}
    remaining = total
    for stage in report:
        rates[stage] = round(remaining / total, 3)
        remaining -= report[stage]
    return rates


def export_csv(store: LeadStore, path: str | Path, min_score: int = 0) -> int:
    """Write the pipeline to CSV for a spreadsheet or a real CRM import."""
    import csv

    leads = store.list(min_score=min_score, limit=100_000)
    columns = ["company", "website", "category", "segment", "contact_name", "contact_title",
               "email", "linkedin_url", "score", "stage", "score_reasons", "notes"]
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for lead in leads:
            row = lead.model_dump(mode="json")
            row["score_reasons"] = "; ".join(lead.score_reasons)
            writer.writerow({c: row.get(c, "") for c in columns})
    return len(leads)
