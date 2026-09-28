"""Unit tests for leadgen.crm using a temporary SQLite file."""

import pytest

from leadgen.crm import LeadStore, conversion_rates, export_csv
from leadgen.models import Category, Lead, Stage


@pytest.fixture
def store(tmp_path):
    with LeadStore(tmp_path / "leads.sqlite3") as store:
        yield store


def test_upsert_and_get_roundtrip(store, strong_lead):
    store.upsert(strong_lead)
    loaded = store.get("crumbco.com")
    assert loaded is not None
    assert loaded.company == "Crumb Co"
    assert loaded.signals.in_national_retail
    assert store.count() == 1
    assert "leads=1" in repr(store)


def test_upsert_replaces_existing_by_domain(store):
    store.upsert(Lead(company="Old Name", website="a.com", score=10))
    store.upsert(Lead(company="New Name", website="www.a.com", score=90))
    assert store.count() == 1
    assert store.get("a.com").company == "New Name"


def test_list_filters_and_orders(store):
    store.upsert(Lead(company="Low", website="low.com", score=10))
    store.upsert(Lead(company="High", website="high.com", score=80, stage=Stage.QUALIFIED))
    store.upsert(Lead(company="Mid", website="mid.com", score=50))
    assert [l.company for l in store.list()] == ["High", "Mid", "Low"]
    assert [l.company for l in store.list(min_score=40)] == ["High", "Mid"]
    assert [l.company for l in store.list(stage=Stage.QUALIFIED)] == ["High"]
    assert len(store.list(limit=1)) == 1


def test_advance_logs_activity(store, strong_lead):
    store.upsert(strong_lead)
    lead = store.advance("crumbco.com", Stage.CONTACTED, note="sent day 0")
    assert lead.stage == Stage.CONTACTED
    history = store.activities("crumbco.com")
    assert history[0]["kind"] == "stage_change"
    assert "new -> contacted" in history[0]["detail"]


def test_advance_unknown_lead_raises(store):
    with pytest.raises(KeyError):
        store.advance("nobody.com", Stage.REPLIED)


def test_get_missing_returns_none(store):
    assert store.get("missing.com") is None


def test_pipeline_report_includes_every_stage(store):
    store.upsert(Lead(company="A", website="a.com"))
    store.upsert(Lead(company="B", website="b.com", stage=Stage.REPLIED))
    report = store.pipeline_report()
    assert list(report.keys())[0] == "new"
    assert report["new"] == 1 and report["replied"] == 1 and report["closed_won"] == 0


def test_conversion_rates_are_cumulative(store):
    store.upsert(Lead(company="A", website="a.com"))
    store.upsert(Lead(company="B", website="b.com", stage=Stage.CONTACTED))
    store.upsert(Lead(company="C", website="c.com", stage=Stage.REPLIED))
    rates = conversion_rates(store.pipeline_report())
    assert rates["new"] == 1.0
    assert rates["contacted"] == pytest.approx(2 / 3, abs=0.001)
    assert rates["replied"] == pytest.approx(1 / 3, abs=0.001)
    assert rates["closed_won"] == 0.0


def test_conversion_rates_empty():
    assert all(v == 0.0 for v in conversion_rates(LeadStore(":memory:").pipeline_report()).values())


def test_export_csv_writes_rows(store, strong_lead, tmp_path):
    strong_lead.score = 77
    strong_lead.score_reasons = ["a", "b"]
    store.upsert(strong_lead)
    store.upsert(Lead(company="Low", website="low.com", category=Category.BAKERY, score=5))
    out = tmp_path / "out.csv"
    assert export_csv(store, out, min_score=50) == 1
    content = out.read_text(encoding="utf-8")
    assert "Crumb Co" in content and "a; b" in content and "Low" not in content
