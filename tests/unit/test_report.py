"""Unit tests for leadgen.report."""

from datetime import date, datetime, timedelta, timezone

import pytest

from leadgen.crm import LeadStore
from leadgen.models import Lead, Stage
from leadgen.report import WeeklyReport, build_report, email_report, render_report, save_report


@pytest.fixture
def store(tmp_path):
    with LeadStore(tmp_path / "r.sqlite3") as store:
        yield store


def test_build_report_collects_new_retriggered_due_and_spear(store, sequence_template):
    old = Lead(company="Old Co", website="old.com", score=40, created_at=datetime.now(timezone.utc) - timedelta(days=30))
    store.upsert(old)
    store.log_activity("old.com", "trigger", "funding: raised")
    new = Lead(company="New Co", website="new.com", score=60, notes="transition: outgrew kitchen https://e")
    store.upsert(new)
    spear = Lead(company="Spear Co", website="spear.com", score=70)
    spear.add_tag("spear")
    store.upsert(spear)
    store.advance("spear.com", Stage.CONTACTED)
    report = build_report(store, sequence_template, days=7, today=date.today() + timedelta(days=6))
    assert [l.company for l in report.new_leads] == ["Spear Co", "New Co"]
    assert [l.company for l in report.retriggered] == ["Old Co"]
    assert report.due_count == 2
    assert report.funnel["contacted"] == 1
    assert report.spear_activity and report.spear_activity[0].startswith("Spear Co")
    assert "WeeklyReport" in repr(report)


def test_render_and_save(tmp_path):
    report = WeeklyReport(generated_on=date(2026, 9, 29), days=7, new_leads=[Lead(company="A", score=50, notes="n")], funnel={"new": 1, "closed_won": 0}, due_count=3)
    text = render_report(report)
    assert "New leads found: 1" in text and "Follow-ups due now: 3" in text and "Funnel: new 1" in text
    path = save_report(text, today=date(2026, 9, 29), directory=tmp_path)
    assert path.name == "2026-09-29.txt" and path.read_text(encoding="utf-8") == text


def test_render_truncates_long_lists():
    leads = [Lead(company=f"C{i}", score=i) for i in range(15)]
    text = render_report(WeeklyReport(generated_on=date.today(), days=7, new_leads=leads))
    assert "and 5 more" in text


def test_email_report_requires_config_and_sends(monkeypatch):
    assert email_report("body", "subj", env={}) is False
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port):
            sent["host"], sent["port"] = host, port

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self):
            sent["tls"] = True

        def login(self, user, password):
            sent["login"] = (user, password)

        def send_message(self, message):
            sent["to"] = message["To"]
            sent["subject"] = message["Subject"]

    monkeypatch.setattr("leadgen.report.smtplib.SMTP", FakeSMTP)
    env = {"LEADGEN_SMTP_HOST": "smtp.example.com", "LEADGEN_SMTP_USER": "me@example.com", "LEADGEN_SMTP_PASSWORD": "pw", "LEADGEN_REPORT_TO": "you@example.com"}
    assert email_report("body", "subj", env=env) is True
    assert sent == {"host": "smtp.example.com", "port": 587, "tls": True, "login": ("me@example.com", "pw"), "to": "you@example.com", "subject": "subj"}
