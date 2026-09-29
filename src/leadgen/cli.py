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
from datetime import date
from pathlib import Path
from typing import Callable

from leadgen import __version__
from leadgen.ai import QualifierError, build_qualifier, lead_facts
from leadgen.contacts import email_candidates
from leadgen.crm import LeadStore, conversion_rates, export_csv
from leadgen.discover import import_csv, search_queries
from leadgen.discovery import brand_to_lead, discover
from leadgen.dossier import build_dossier, find_website, save_dossier
from leadgen.htmlimport import import_html_file
from leadgen.inbound import FormSubmission, NetlifyError, fetch_netlify_submissions, filter_since, import_submissions, load_csv
from leadgen.economics import FunnelAssumptions, ReferralTerms, account_value, funnel_plan
from leadgen.enrich import WebsiteEnricher
from leadgen.facility import load_facility
from leadgen.models import Category, Lead, Stage
from leadgen.outreach import SenderIdentity, load_sequence, render_sequence
from leadgen.report import REPORT_DIR, build_report, email_report, render_report, save_report
from leadgen.schedule import due_touches, log_touch
from leadgen.sources import build_sources, default_client, load_feeds, since_date
from leadgen.triggers import ClaudeExtractor, RuleBasedExtractor, extraction_to_lead
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


def cmd_import_form(args: argparse.Namespace) -> int:
    """Import website capacity-check submissions from a CSV export and/or the Netlify API."""
    if not args.csv and not args.netlify:
        print("import-form needs a CSV export path or --netlify", file=sys.stderr)
        return 1
    try:
        since = date.fromisoformat(args.since) if args.since else None
    except ValueError:
        print(f"--since must be YYYY-MM-DD, got {args.since!r}", file=sys.stderr)
        return 1
    submissions = _collect_form_submissions(args, since)
    if submissions is None:
        return 1
    with _store(args) as store:
        result = import_submissions(store, submissions)
    for item in result.imported:
        lead = item.lead
        print(f"{lead.company} {item.email} {lead.category.value} {lead.segment.value} ({item.status})")
    for label, reason in result.skipped:
        print(f"  skipped {label}: {reason}")
    print(
        f"import-form: {result.new_count} new, {result.merged_count} merged, {len(result.skipped)} skipped. "
        "Run `leadgen enrich` then `leadgen score`."
    )
    return 0


def _collect_form_submissions(args: argparse.Namespace, since: date | None) -> list[FormSubmission] | None:
    """Read the CSV and/or pull from Netlify; print why and return None when either fails."""
    token = os.environ.get("NETLIFY_AUTH_TOKEN", "").strip()
    site_id = os.environ.get("NETLIFY_SITE_ID", "").strip()
    if args.netlify and not (token and site_id):
        print("import-form --netlify needs NETLIFY_AUTH_TOKEN and NETLIFY_SITE_ID set in the environment (see .env.example)", file=sys.stderr)
        return None
    submissions: list[FormSubmission] = []
    if args.csv:
        try:
            submissions.extend(filter_since(load_csv(args.csv), since))
        except (OSError, UnicodeDecodeError) as exc:
            reason = "not UTF-8; save the export as a UTF-8 CSV" if isinstance(exc, UnicodeDecodeError) else exc.strerror or str(exc)
            print(f"cannot read {args.csv}: {reason}", file=sys.stderr)
            return None
    if args.netlify:
        try:
            submissions.extend(fetch_netlify_submissions(site_id, token, since=since))
        except NetlifyError as exc:
            print(f"Netlify import failed: {exc}", file=sys.stderr)
            return None
    return submissions


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
            if args.thread and touch.thread != args.thread:
                continue
            print(f"--- day {touch.day} [{touch.channel}] ({touch.thread}) {touch.subject}\n{touch.body}\n")
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


def cmd_due(args: argparse.Namespace) -> int:
    template = load_sequence(args.template)
    today = date.fromisoformat(args.date) if args.date else date.today()
    with _store(args) as store:
        due = due_touches(store, template, today)
    if not due:
        print(f"nothing due on {today.isoformat()}")
        return 0
    print(f"{'overdue':>7}  {'day':>3}  {'channel':<9} {'lead':<32} subject")
    for touch in due:
        print(f"{touch.days_overdue:>7}  {touch.day:>3}  {touch.channel:<9} {touch.company[:32]:<32} {touch.subject}")
    print(f"{len(due)} touches due. Log each with: leadgen touch <lead> <day> [--channel email]")
    return 0


def cmd_touch(args: argparse.Namespace) -> int:
    with _store(args) as store:
        lead = store.get(args.lead)
        if lead is None:
            print(f"no lead found for {args.lead!r}", file=sys.stderr)
            return 1
        log_touch(store, lead, args.day, args.channel)
        if args.day == 0 and lead.stage in (Stage.NEW, Stage.ENRICHED, Stage.QUALIFIED):
            store.advance(args.lead, Stage.CONTACTED, note="day 0 sent")
    print(f"{lead.company}: logged day {args.day} {args.channel}")
    return 0


def cmd_brief(args: argparse.Namespace) -> int:
    facility = load_facility(args.facility)
    with _store(args) as store:
        lead = store.get(args.lead)
        if lead is None:
            print(f"no lead found for {args.lead!r}", file=sys.stderr)
            return 1
        history = store.activities(lead.domain or lead.company.lower())
    qualifier = build_qualifier()
    print(f"# Call brief: {lead.company}\n")
    print(lead_facts(lead, facility))
    try:
        assessment = qualifier.assess(lead, facility)
        print(f"\nFit {assessment.fit_score}/100 ({qualifier!r})")
        print(f"Likely pain: {assessment.likely_pain}")
        print(f"Best angle: {assessment.best_angle}")
        if assessment.disqualifiers:
            print(f"Disqualifiers: {'; '.join(assessment.disqualifiers)}")
    except QualifierError as exc:
        print(f"\nAI assessment unavailable: {exc}", file=sys.stderr)
    print("\nHistory:")
    for activity in history or [{"created_at": "", "kind": "none", "detail": "no activity logged"}]:
        print(f"  {activity['created_at'][:10]} {activity['kind']}: {activity['detail'][:120]}")
    return 0


def cmd_emails(args: argparse.Namespace) -> int:
    with _store(args) as store:
        lead = store.get(args.lead)
    if lead is None:
        print(f"no lead found for {args.lead!r}", file=sys.stderr)
        return 1
    candidates = email_candidates(lead, known_pattern=args.pattern or None)
    if not candidates:
        print(f"{lead.company}: no website on file, cannot propose addresses")
        return 1
    for candidate in candidates:
        flag = "verified" if candidate.verified else "UNVERIFIED"
        print(f"{candidate.address:<45} {candidate.pattern:<12} {flag}")
    if not candidates[0].verified:
        print("Verify with a free lookup or a single test send before adding to the sequence.")
    return 0


def _extractor(use_ai: bool):  # type: ignore[no-untyped-def]
    if use_ai and (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        import anthropic

        return ClaudeExtractor(anthropic.Anthropic(), model=os.environ.get("LEADGEN_MODEL", "claude-opus-5"))
    return RuleBasedExtractor()


def cmd_watch(args: argparse.Namespace) -> int:
    """Poll public feeds, extract triggers, and add new leads to the pipeline."""
    config = load_feeds(args.feeds)
    sources = build_sources(config, default_client())
    if args.source:
        sources = [s for s in sources if s.name == args.source or s.name.endswith(args.source)]
    extractor = _extractor(args.ai)
    since = since_date(args.days)
    added = updated = skipped = 0
    with _store(args) as store:
        for source in sources:
            items = source.fetch(since)
            print(f"{source.name}: {len(items)} items")
            for item in items:
                lead = extraction_to_lead(item, extractor.extract(item))
                if lead is None:
                    skipped += 1
                    continue
                existing = store.get(lead.domain or lead.company.lower())
                if existing is None:
                    store.upsert(lead)
                    added += 1
                else:
                    _merge_trigger(existing, lead)
                    store.upsert(existing)
                    updated += 1
                store.log_activity(lead.domain or lead.company.lower(), "trigger", lead.notes[:300])
    print(f"watch since {since.isoformat()} ({extractor!r}): added {added}, updated {updated}, skipped {skipped}. Run `leadgen score` next.")
    return 0


def _merge_trigger(existing, incoming) -> None:  # type: ignore[no-untyped-def]
    """Add a newly seen trigger to a lead already in the pipeline."""
    if incoming.notes and incoming.notes not in existing.notes:
        existing.notes = f"{existing.notes} || {incoming.notes}".strip(" |")
    merged = existing.signals.model_dump()
    for name, value in incoming.signals.model_dump().items():
        if value is True:
            merged[name] = True
    existing.signals = type(existing.signals)(**merged)
    if not existing.website and incoming.website:
        existing.website = incoming.website


def cmd_discover(args: argparse.Namespace) -> int:
    """Find emerging brands per category with Claude web search and add them to the pipeline."""
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print("discover needs ANTHROPIC_API_KEY (or ANTHROPIC_AUTH_TOKEN)", file=sys.stderr)
        return 1
    import anthropic

    client = anthropic.Anthropic()
    model = os.environ.get("LEADGEN_MODEL", "claude-opus-5")
    try:
        categories = [Category(c) for c in args.categories] or [Category.COOKIE, Category.BAKERY, Category.PET_TREAT]
    except ValueError as exc:
        print(f"unknown category: {exc}", file=sys.stderr)
        return 1
    added = updated = 0
    with _store(args) as store:
        for category in categories:
            try:
                brands = discover(category, client, model=model)
            except QualifierError as exc:
                print(f"{category.value}: discovery failed: {exc}", file=sys.stderr)
                continue
            for brand in brands:
                lead = brand_to_lead(brand, category)
                key = lead.domain or lead.company.lower()
                existing = store.get(key)
                if existing is None:
                    store.upsert(lead)
                    added += 1
                else:
                    _merge_trigger(existing, lead)
                    store.upsert(existing)
                    updated += 1
                store.log_activity(key, "discovered", lead.notes[:300])
            print(f"{category.value}: {len(brands)} brands found")
    print(f"discover: added {added}, updated {updated}. Run `leadgen websites`, `leadgen enrich`, then `leadgen score`.")
    return 0


def cmd_dossier(args: argparse.Namespace) -> int:
    """Research a lead with Claude and web search; save Markdown under leads/dossiers/."""
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print("dossier needs ANTHROPIC_API_KEY (or ANTHROPIC_AUTH_TOKEN); see docs/15_infrastructure.md", file=sys.stderr)
        return 1
    import anthropic

    facility = load_facility(args.facility)
    client = anthropic.Anthropic()
    model = os.environ.get("LEADGEN_MODEL", "claude-opus-5")
    with _store(args) as store:
        leads = [store.get(key) for key in args.leads] if args.leads else store.list(min_score=args.min_score, limit=args.limit)
        leads = [lead for lead in leads if lead is not None]
        if not leads:
            print("no matching leads", file=sys.stderr)
            return 1
        for lead in leads:
            try:
                text = build_dossier(lead, facility, client, model=model)
            except QualifierError as exc:
                print(f"{lead.company}: dossier failed: {exc}", file=sys.stderr)
                continue
            path = save_dossier(lead, text, directory=Path(args.out))
            store.log_activity(lead.domain or lead.company.lower(), "dossier", str(path))
            print(f"{lead.company}: {path}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    with _store(args) as store:
        leads = store.list(stage=Stage(args.stage) if args.stage else None, min_score=args.min_score, limit=args.limit, tag=args.tag or None)
    if not leads:
        print("no leads match")
        return 0
    print(f"{'score':>5}  {'stage':<14} {'company':<32} {'contact':<24} {'tags'}")
    for lead in leads:
        print(f"{lead.score:>5}  {lead.stage.value:<14} {lead.company[:32]:<32} {lead.contact_name[:24]:<24} {','.join(lead.tags)}")
    return 0


def cmd_tag(args: argparse.Namespace) -> int:
    with _store(args) as store:
        lead = store.get(args.lead)
        if lead is None:
            print(f"no lead found for {args.lead!r}", file=sys.stderr)
            return 1
        changed = lead.remove_tag(args.tag) if args.remove else lead.add_tag(args.tag)
        store.upsert(lead)
    print(f"{lead.company}: tags {lead.tags}" + ("" if changed else " (no change)"))
    return 0


def cmd_import_html(args: argparse.Namespace) -> int:
    """Import company links from a saved directory page (exhibitor list, retailer program)."""
    leads = import_html_file(args.html, source=args.source, category=Category(args.category), extra_skip=tuple(args.skip))
    if args.dry_run:
        for lead in leads:
            print(f"{lead.company:<40} {lead.website}")
        print(f"{len(leads)} candidates (dry run, nothing imported)")
        return 0
    with _store(args) as store:
        new = 0
        for lead in leads:
            if store.get(lead.domain) is None:
                store.upsert(lead)
                new += 1
    print(f"imported {new} new leads from {len(leads)} candidates ({args.source}). Run `leadgen enrich` then `leadgen score`.")
    return 0


def cmd_websites(args: argparse.Namespace) -> int:
    """Fill missing websites for scored leads using Claude web search (two searches each)."""
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print("websites needs ANTHROPIC_API_KEY (or ANTHROPIC_AUTH_TOKEN)", file=sys.stderr)
        return 1
    import anthropic

    client = anthropic.Anthropic()
    model = os.environ.get("LEADGEN_MODEL", "claude-opus-5")
    found = 0
    with _store(args) as store:
        missing = [lead for lead in store.list(min_score=args.min_score, limit=100_000) if not lead.website][: args.limit]
        for lead in missing:
            try:
                domain = find_website(lead, client, model=model)
            except QualifierError as exc:
                print(f"{lead.company}: lookup failed: {exc}", file=sys.stderr)
                continue
            if not domain:
                print(f"{lead.company}: unknown")
                continue
            store.upsert(Lead(**{**lead.model_dump(), "website": domain}))
            store.log_activity(domain, "website_found", f"was {lead.company.lower()}; found {domain}")
            found += 1
            print(f"{lead.company}: {domain}")
    print(f"found {found} of {len(missing)}. Leads with a new domain were re-keyed; run `leadgen enrich` next.")
    return 0


def cmd_weekly_report(args: argparse.Namespace) -> int:
    """Summarize the week's discoveries, retriggers, due touches, and funnel; optionally email it."""
    template = load_sequence(args.template)
    with _store(args) as store:
        report = build_report(store, template, days=args.days)
    text = render_report(report)
    path = save_report(text, directory=Path(args.reports_dir))
    print(text)
    print(f"saved {path}")
    if args.email:
        sent = email_report(text, subject=f"cookie-plug weekly report {report.generated_on.isoformat()}")
        print("emailed" if sent else "email not sent: set LEADGEN_SMTP_HOST, LEADGEN_SMTP_USER, LEADGEN_SMTP_PASSWORD, LEADGEN_REPORT_TO")
        return 0 if sent else 2
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
    _add_import_form_command(sub)

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
    p.add_argument("--threshold", type=int, default=50)
    p.set_defaults(func=cmd_qualify)

    p = sub.add_parser("draft", help="render the outreach sequence for one lead")
    p.add_argument("lead", help="domain or lowercase company name")
    p.add_argument("--ai", action="store_true", help="use Claude for the personal line")
    p.add_argument("--thread", default="", choices=["", "founder", "operator", "sales"], help="only this thread's touches")
    p.set_defaults(func=cmd_draft)

    p = sub.add_parser("touch", help="log a sent touch (day 0 also marks the lead contacted)")
    p.add_argument("lead")
    p.add_argument("day", type=int)
    p.add_argument("--channel", default="email")
    p.set_defaults(func=cmd_touch)

    p = sub.add_parser("due", help="follow-ups owed today for contacted leads")
    p.add_argument("--date", default="", help="YYYY-MM-DD, defaults to today")
    p.set_defaults(func=cmd_due)

    p = sub.add_parser("brief", help="one-page call prep for a lead")
    p.add_argument("lead")
    p.set_defaults(func=cmd_brief)

    p = sub.add_parser("list", help="list leads by score, stage, or tag")
    p.add_argument("--stage", default="", choices=["", *[s.value for s in Stage]])
    p.add_argument("--tag", default="")
    p.add_argument("--min-score", type=int, default=0)
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("tag", help="add or remove a tag on a lead (e.g. spear, bench, nurture)")
    p.add_argument("lead")
    p.add_argument("tag")
    p.add_argument("--remove", action="store_true")
    p.set_defaults(func=cmd_tag)

    p = sub.add_parser("import-html", help="import company links from a saved directory page")
    p.add_argument("html", help="path to the page saved from your browser")
    p.add_argument("--source", required=True, help="tag such as expo_west_2027")
    p.add_argument("--category", default="other", choices=[c.value for c in Category])
    p.add_argument("--skip", action="append", default=[], help="extra domain to ignore, repeatable")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_import_html)

    p = sub.add_parser("websites", help="fill missing websites with Claude web search (needs a key)")
    p.add_argument("--min-score", type=int, default=40)
    p.add_argument("--limit", type=int, default=25)
    p.set_defaults(func=cmd_websites)

    p = sub.add_parser("watch", help="poll public feeds (FDA recalls, EDGAR filings, trade press) for new triggers")
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--source", default="", help="only this source, e.g. fda_recall, edgar_filing, nosh_pr")
    p.add_argument("--feeds", default="config/feeds.yaml")
    p.add_argument("--ai", action="store_true", help="use Claude to classify items (needs an API key)")
    p.set_defaults(func=cmd_watch)

    p = sub.add_parser("discover", help="find emerging brands per category with Claude web search (needs a key)")
    p.add_argument("categories", nargs="*", help="any of cookie, bakery, snack, pet_treat, pet_food; default: cookie bakery pet_treat")
    p.set_defaults(func=cmd_discover)

    p = sub.add_parser("dossier", help="research leads with Claude web search and save Markdown dossiers")
    p.add_argument("leads", nargs="*", help="domains or lowercase company names; default: top leads by score")
    p.add_argument("--min-score", type=int, default=50)
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--out", default="leads/dossiers")
    p.set_defaults(func=cmd_dossier)

    p = sub.add_parser("emails", help="ranked, unverified address candidates for a lead's contact")
    p.add_argument("lead")
    p.add_argument("--pattern", default="", help="known company pattern, e.g. first.last")
    p.set_defaults(func=cmd_emails)

    p = sub.add_parser("advance", help="move a lead to a new stage")
    p.add_argument("lead")
    p.add_argument("stage", choices=[s.value for s in Stage])
    p.add_argument("--note", default="")
    p.set_defaults(func=cmd_advance)


def _add_import_form_command(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    """The ``import-form`` subcommand, registered next to ``import``."""
    p = sub.add_parser("import-form", help="import website capacity-check submissions (CSV export or --netlify)")
    p.add_argument("csv", nargs="?", default="", help="CSV export of the capacity-check form")
    p.add_argument("--netlify", action="store_true", help="pull from the Netlify API (needs NETLIFY_AUTH_TOKEN and NETLIFY_SITE_ID)")
    p.add_argument("--since", default="", help="YYYY-MM-DD: only submissions from the start of this day (UTC)")
    p.set_defaults(func=cmd_import_form)


def _add_ops_commands(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    """Subcommands for research, reporting, and planning."""
    p = sub.add_parser("queries", help="print search queries for a category")
    p.add_argument("category", choices=[c.value for c in Category])
    p.set_defaults(func=cmd_queries)

    p = sub.add_parser("weekly-report", help="the week's new leads, retriggers, due touches, funnel; --email sends it")
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--email", action="store_true")
    p.add_argument("--reports-dir", default=str(REPORT_DIR), help="where to save the report (default data/reports)")
    p.set_defaults(func=cmd_weekly_report)

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
