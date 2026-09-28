"""Unit tests for leadgen.schedule."""

from datetime import date, timedelta

import pytest

from leadgen.crm import LeadStore
from leadgen.models import Lead, Stage
from leadgen.schedule import contact_start, due_touches, log_touch, logged_touch_days


@pytest.fixture
def store(tmp_path):
    with LeadStore(tmp_path / "s.sqlite3") as store:
        yield store


def _contacted(store: LeadStore, company: str, domain: str) -> Lead:
    lead = Lead(company=company, website=domain)
    store.upsert(lead)
    store.advance(domain, Stage.CONTACTED)
    return lead


def test_contact_start_from_stage_change(store):
    lead = _contacted(store, "A", "a.com")
    assert contact_start(store, lead) == date.today()


def test_contact_start_none_when_never_contacted(store):
    lead = Lead(company="B", website="b.com")
    store.upsert(lead)
    assert contact_start(store, lead) is None


def test_log_touch_and_logged_days(store):
    lead = _contacted(store, "A", "a.com")
    log_touch(store, lead, 3, "linkedin")
    log_touch(store, lead, 5, "email")
    store.log_activity("a.com", "touch", "garbage")
    assert logged_touch_days(store, lead) == {3, 5}


def test_due_touches_respects_dates_and_logged(store, sequence_template):
    lead = _contacted(store, "A", "a.com")
    today = date.today()
    assert due_touches(store, sequence_template, today) == []
    later = today + timedelta(days=6)
    due = due_touches(store, sequence_template, later)
    assert [t.day for t in due] == [3, 5]
    assert due[0].days_overdue == 3 and due[0].channel == "linkedin"
    assert "DueTouch" in repr(due[0])
    log_touch(store, lead, 3, "linkedin")
    assert [t.day for t in due_touches(store, sequence_template, later)] == [5]


def test_due_touches_skips_replied_leads(store, sequence_template):
    _contacted(store, "A", "a.com")
    store.advance("a.com", Stage.REPLIED)
    assert due_touches(store, sequence_template, date.today() + timedelta(days=30)) == []


def test_due_touches_ordered_most_overdue_first(store, sequence_template):
    _contacted(store, "Zed", "z.com")
    _contacted(store, "Amy", "amy.com")
    due = due_touches(store, sequence_template, date.today() + timedelta(days=20))
    assert due[0].day == 3 and due[0].company == "Amy"
    assert due[-1].day == 18
