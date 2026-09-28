"""Follow-up scheduling for the manual sending routine.

The sequence template says which day each touch goes out. This module turns
that into a daily "what is owed" list by combining each contacted lead's
start date (the stage change to ``contacted``) with the touches already
logged. A lead that replies leaves the contacted stage and drops out.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from pydantic import BaseModel

from leadgen.crm import LeadStore
from leadgen.models import Lead, Stage
from leadgen.outreach import SequenceTemplate

TOUCH_KIND = "touch"
CONTACTED_MARKER = f"-> {Stage.CONTACTED.value}"


class DueTouch(BaseModel):
    """One follow-up that is due or overdue for a lead."""

    company: str
    domain_key: str
    day: int
    channel: str
    subject: str
    due_on: date
    days_overdue: int

    def __repr__(self) -> str:
        return f"DueTouch(company={self.company!r}, day={self.day}, overdue={self.days_overdue})"


def contact_start(store: LeadStore, lead: Lead) -> date | None:
    """Date the lead entered the contacted stage, or None if never logged."""
    key = lead.domain or lead.company.lower()
    for activity in store.activities(key):
        if activity["kind"] == "stage_change" and CONTACTED_MARKER in activity["detail"]:
            return datetime.fromisoformat(activity["created_at"]).date()
        if activity["kind"] == TOUCH_KIND and activity["detail"].startswith("day 0"):
            return datetime.fromisoformat(activity["created_at"]).date()
    return None


def logged_touch_days(store: LeadStore, lead: Lead) -> set[int]:
    """Sequence days already sent, from ``touch`` activities ("day 3 email")."""
    key = lead.domain or lead.company.lower()
    days: set[int] = set()
    for activity in store.activities(key):
        if activity["kind"] == TOUCH_KIND:
            try:
                days.add(int(activity["detail"].split()[1]))
            except (IndexError, ValueError):
                continue
    return days


def log_touch(store: LeadStore, lead: Lead, day: int, channel: str) -> None:
    """Record that a touch went out. Day 0 also starts the clock."""
    key = lead.domain or lead.company.lower()
    store.log_activity(key, TOUCH_KIND, f"day {day} {channel}")


def due_touches(store: LeadStore, template: SequenceTemplate, today: date) -> list[DueTouch]:
    """Every unsent touch whose date has arrived, for leads still in ``contacted``."""
    due: list[DueTouch] = []
    for lead in store.list(stage=Stage.CONTACTED, limit=100_000):
        start = contact_start(store, lead)
        if start is None:
            continue
        sent = logged_touch_days(store, lead)
        for touch in template.touches:
            day = int(touch.get("day", 0))
            if day == 0 or day in sent:
                continue
            due_on = start + timedelta(days=day)
            if due_on <= today:
                due.append(
                    DueTouch(
                        company=lead.company,
                        domain_key=lead.domain or lead.company.lower(),
                        day=day,
                        channel=str(touch.get("channel", "email")),
                        subject=str(touch.get("subject", "")).format(company=lead.company, category_noun="", first_name=lead.first_name),
                        due_on=due_on,
                        days_overdue=(today - due_on).days,
                    )
                )
    due.sort(key=lambda t: (-t.days_overdue, t.company.lower()))
    return due
