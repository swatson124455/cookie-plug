"""Weekly pipeline report: what the machine found, what is owed, and the funnel.

The report is plain text so it reads in any inbox. Email delivery uses
SMTP settings from the environment; without them the report is written
to disk and printed, which is what the cloud Routine relies on.
"""

from __future__ import annotations

import os
import smtplib
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path

from pydantic import BaseModel, Field

from leadgen.crm import LeadStore
from leadgen.models import Lead, Stage
from leadgen.outreach import SequenceTemplate
from leadgen.schedule import due_touches

REPORT_DIR = Path("data/reports")
TOP_N = 10


class WeeklyReport(BaseModel):
    """Everything the report prints, so it can be tested without parsing text."""

    generated_on: date
    days: int
    new_leads: list[Lead] = Field(default_factory=list)
    retriggered: list[Lead] = Field(default_factory=list)
    due_count: int = 0
    funnel: dict[str, int] = Field(default_factory=dict)
    spear_activity: list[str] = Field(default_factory=list)

    def __repr__(self) -> str:
        return f"WeeklyReport(new={len(self.new_leads)}, retriggered={len(self.retriggered)}, due={self.due_count})"


def build_report(store: LeadStore, template: SequenceTemplate, days: int = 7, today: date | None = None) -> WeeklyReport:
    """Collect the week's changes from the store."""
    today = today or date.today()
    cutoff = datetime.combine(today - timedelta(days=days), datetime.min.time(), tzinfo=timezone.utc)
    leads = store.list(limit=100_000)
    new = sorted([l for l in leads if l.created_at >= cutoff], key=lambda l: -l.score)
    new_keys = {l.domain or l.company.lower() for l in new}
    retriggered = [l for l in leads if (l.domain or l.company.lower()) not in new_keys and _has_recent(store, l, ("trigger", "discovered"), cutoff)]
    spear = [f"{l.company}: {_last_activity(store, l)}" for l in store.list(tag="spear", limit=100) if _has_recent(store, l, None, cutoff)]
    return WeeklyReport(
        generated_on=today, days=days, new_leads=new, retriggered=retriggered,
        due_count=len(due_touches(store, template, today)), funnel=dict(store.pipeline_report()),
        spear_activity=spear,
    )


def _has_recent(store: LeadStore, lead: Lead, kinds: tuple[str, ...] | None, cutoff: datetime) -> bool:
    for activity in store.activities(lead.domain or lead.company.lower()):
        when = datetime.fromisoformat(activity["created_at"])
        if when >= cutoff and (kinds is None or activity["kind"] in kinds):
            return True
    return False


def _last_activity(store: LeadStore, lead: Lead) -> str:
    history = store.activities(lead.domain or lead.company.lower())
    return f"{history[-1]['kind']} {history[-1]['detail'][:80]}" if history else "no activity"


def render_report(report: WeeklyReport) -> str:
    """Plain-text rendering."""
    lines = [f"cookie-plug weekly report, {report.generated_on.isoformat()} (last {report.days} days)", ""]
    lines.append(f"New leads found: {len(report.new_leads)}")
    for lead in report.new_leads[:TOP_N]:
        lines.append(f"  {lead.score:>3}  {lead.company} [{lead.category.value}] {lead.website or 'no site'}")
        lines.append(f"       {lead.notes[:140]}")
    if len(report.new_leads) > TOP_N:
        lines.append(f"  ... and {len(report.new_leads) - TOP_N} more, run: leadgen list --min-score 35")
    lines.append("")
    lines.append(f"Existing leads with a new trigger: {len(report.retriggered)}")
    for lead in report.retriggered[:TOP_N]:
        lines.append(f"  {lead.score:>3}  {lead.company}: {lead.notes.split('||')[-1].strip()[:120]}")
    lines.append("")
    lines.append(f"Follow-ups due now: {report.due_count} (run: leadgen due)")
    lines.append("")
    if report.spear_activity:
        lines.append("Spear accounts with activity this week:")
        lines.extend(f"  {line}" for line in report.spear_activity)
        lines.append("")
    lines.append("Funnel: " + ", ".join(f"{stage} {count}" for stage, count in report.funnel.items() if count))
    return "\n".join(lines) + "\n"


def save_report(text: str, today: date | None = None, directory: Path = REPORT_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{(today or date.today()).isoformat()}.txt"
    path.write_text(text, encoding="utf-8")
    return path


def email_report(text: str, subject: str, env: dict[str, str] | None = None) -> bool:
    """Send via SMTP using LEADGEN_SMTP_* and LEADGEN_REPORT_TO; False if not configured."""
    env = env if env is not None else dict(os.environ)
    host, user, password, to = (env.get(k, "") for k in ("LEADGEN_SMTP_HOST", "LEADGEN_SMTP_USER", "LEADGEN_SMTP_PASSWORD", "LEADGEN_REPORT_TO"))
    if not (host and user and password and to):
        return False
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = user
    message["To"] = to
    message.set_content(text)
    with smtplib.SMTP(host, int(env.get("LEADGEN_SMTP_PORT", "587"))) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(message)
    return True
