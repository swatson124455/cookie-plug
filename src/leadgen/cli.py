"""Command-line interface for the lead engine.

Each subcommand is one pipeline step so the weekly routine is scriptable:
``import`` a list, ``enrich`` it, ``score`` it, ``qualify`` the top of it,
``draft`` outreach, ``advance`` stages as replies come in, and ``report``
the funnel.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Callable

from leadgen import __version__
from leadgen.ai import QualifierError, build_qualifier
from leadgen.crm import LeadStore, conversion_rates, export_csv
from leadgen.discover import import_csv, search_queries
from leadgen.economics import FunnelAssumptions, ReferralTerms, account_value, funnel_plan
from leadgen.enrich import WebsiteEnricher
from leadgen.facility import load_facility
from leadgen.models import Category, Stage
from leadgen.outreach import SenderIdentity, load_sequence, render_sequence
from leadgen.scoring import apply_score, load_weights


def _store(args: argparse.Namespace) -> LeadStore:
    return LeadStore(args.db)


def _sender() -> SenderIdentity:
    return SenderIdentity(
        name=os.environ.get("LEADGEN_SENDER_NAME") or "Your Name",
        title=os.environ.get("LEADGEN_SENDER_TITLE") or "Partnerships",
    )


def cmd_import(args: argparse.Namespace) -> int:
    report = import_csv(args.csv, default_source=args.source)
    with _store(args) as store:
        store.upsert_many(report.leads)
    print(f"imported {len(report.leads)} leads, skipped {len(report.skipped)}")
    for row_number, reason in report.skipped:
        print(f"  row {row_number}: {reason}")
    return 0


def cmd_enrich(args: argparse.Namespace) -> int:
    enricher = WebsiteEnricher()
    with _store(args) as store:
        leads = store.list(stage=Stage.NEW if not args.all else None, limit=args.limit)
        for lead in leads:
            enricher.enrich(lead)
            store.upsert(lead)
            print(f"{lead.company}: {lead.signals!r}")
    print(f"enriched {len(leads)} leads")
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    weights = load_weights(args.icp)
    facility = load_facility(args.facility)
    with _store(args) as store:
        leads = store.list(limit=100_000)
        for lead in leads:
            apply_score(lead, weights, facility)
            store.upsert(lead)
        print(f"scored {len(leads)} leads")
        for lead in store.list(min_score=args.min_score, limit=args.top):
            print(f"{lead.score:3d}  {lead.company:<32} {lead.category.value:<10} {'; '.join(lead.score_reasons)}")
    return 0


def cmd_qualify(args: argparse.Namespace) -> int:
    facility = load_facility(args.facility)
    qualifier = build_qualifier()
    print(f"using {qualifier!r}")
    with _store(args) as store:
        leads = store.list(min_score=args.min_score, limit=args.limit)
        for lead in leads:
            try:
                assessment = qualifier.assess(lead, facility)
            except QualifierError as exc:
                print(f"{lead.company}: qualification failed: {exc}")
                continue
            lead.notes = (lead.notes + f" | AI fit {assessment.fit_score}: {assessment.best_angle}").strip(" |")
            if assessment.fit_score >= args.threshold and not assessment.disqualifiers:
                lead.stage = Stage.QUALIFIED
            store.upsert(lead)
            store.log_activity(lead.domain or lead.company.lower(), "qualified", assessment.model_dump_json())
            print(f"{assessment.fit_score:3d}  {lead.company:<32} {assessment.best_angle}")
    return 0


def cmd_draft(args: argparse.Namespace) -> int:
    facility = load_facility(args.facility)
    template = load_sequence(args.template)
    sender = _sender()
    with _store(args) as store:
        lead = store.get(args.lead)
        if lead is None:
            print(f"no lead found for {args.lead!r}", file=sys.stderr)
            return 1
        personal_line = None
        if args.ai:
            try:
                personal_line = build_qualifier().assess(lead, facility).personal_line
            except QualifierError as exc:
                print(f"AI personal line unavailable ({exc}); using signal-based line", file=sys.stderr)
        for touch in render_sequence(lead, facility, sender, template, personal_line=personal_line):
            print(f"--- day {touch.day} [{touch.channel}] {touch.subject}\n{touch.body}\n")
    return 0


def cmd_queries(args: argparse.Namespace) -> int:
    for channel, queries in search_queries(Category(args.category)).items():
        print(f"## {channel}")
        for query in queries:
            print(f"  {query}")
    return 0


def cmd_advance(args: argparse.Namespace) -> int:
    with _store(args) as store:
        try:
            lead = store.advance(args.lead, Stage(args.stage), note=args.note)
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    print(f"{lead.company} -> {lead.stage.value}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    with _store(args) as store:
        report = store.pipeline_report()
    rates = conversion_rates(report)
    print(f"{'stage':<16}{'leads':>6}{'reached':>9}")
    for stage, count in report.items():
        print(f"{stage:<16}{count:>6}{rates[stage]:>9.0%}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    with _store(args) as store:
        count = export_csv(store, args.out, min_score=args.min_score)
    print(f"exported {count} leads to {args.out}")
    return 0


def cmd_facility_check(args: argparse.Namespace) -> int:
    facility = load_facility(args.facility)
    pending = facility.unconfirmed_fields()
    print(f"{facility!r}")
    print(f"confirmed certifications: {facility.confirmed_certifications() or 'none'}")
    if pending:
        print("fields still TO_CONFIRM before outreach:")
        for field in pending:
            print(f"  - {field}")
        return 1
    print("facility profile complete")
    return 0


def cmd_economics(args: argparse.Namespace) -> int:
    terms = ReferralTerms(referral_pct=args.pct, years_paid=args.years, annual_retention=args.retention)
    value = account_value(args.annual_purchases, terms)
    plan = funnel_plan(args.target_closes, FunnelAssumptions())
    print(json.dumps({"account": value.model_dump(), "funnel": plan.model_dump()}, indent=2))
    return 0


def _add_pipeline_commands(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    """Subcommands that move leads through the funnel."""
    p = sub.add_parser("import", help="import leads from a CSV")
    p.add_argument("csv")
    p.add_argument("--source", default="csv")
    p.set_defaults(func=cmd_import)

    p = sub.add_parser("enrich", help="fetch public website signals")
    p.add_argument("--all", action="store_true", help="re-enrich every lead, not only new ones")
    p.add_argument("--limit", type=int, default=200)
    p.set_defaults(func=cmd_enrich)

    p = sub.add_parser("score", help="apply ICP scoring")
    p.add_argument("--min-score", type=int, default=40)
    p.add_argument("--top", type=int, default=25)
    p.set_defaults(func=cmd_score)

    p = sub.add_parser("qualify", help="AI (or rule-based) qualification")
    p.add_argument("--min-score", type=int, default=40)
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--threshold", type=int, default=55)
    p.set_defaults(func=cmd_qualify)

    p = sub.add_parser("draft", help="render the outreach sequence for one lead")
    p.add_argument("lead", help="domain or lowercase company name")
    p.add_argument("--ai", action="store_true", help="use Claude for the personal line")
    p.set_defaults(func=cmd_draft)

    p = sub.add_parser("advance", help="move a lead to a new stage")
    p.add_argument("lead")
    p.add_argument("stage", choices=[s.value for s in Stage])
    p.add_argument("--note", default="")
    p.set_defaults(func=cmd_advance)


def _add_ops_commands(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    """Subcommands for research, reporting, and planning."""
    p = sub.add_parser("queries", help="print search queries for a category")
    p.add_argument("category", choices=[c.value for c in Category])
    p.set_defaults(func=cmd_queries)

    p = sub.add_parser("report", help="print the pipeline funnel")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("export", help="export leads to CSV")
    p.add_argument("out")
    p.add_argument("--min-score", type=int, default=0)
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("facility-check", help="list unconfirmed facility fields")
    p.set_defaults(func=cmd_facility_check)

    p = sub.add_parser("economics", help="account value and funnel math")
    p.add_argument("--pct", type=float, required=True, help="referral percent of purchases")
    p.add_argument("--years", type=float, default=2)
    p.add_argument("--retention", type=float, default=0.85)
    p.add_argument("--annual-purchases", type=float, required=True)
    p.add_argument("--target-closes", type=int, default=3)
    p.set_defaults(func=cmd_economics)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="leadgen", description="Co-packing referral lead engine")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--db", default=os.environ.get("LEADGEN_DB_PATH", "data/leads.sqlite3"))
    parser.add_argument("--facility", default="config/facility.yaml")
    parser.add_argument("--icp", default="config/icp.yaml")
    parser.add_argument("--template", default="config/templates/sequence.yaml")
    sub = parser.add_subparsers(dest="command", required=True)
    _add_pipeline_commands(sub)
    _add_ops_commands(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handler: Callable[[argparse.Namespace], int] = args.func
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
