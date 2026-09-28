"""Unit tests for leadgen.discover."""

import pytest

from leadgen.discover import dedupe, import_csv, search_queries
from leadgen.models import Category, Lead, Segment


def test_import_csv_loads_valid_rows_and_reports_bad_ones(sample_csv):
    report = import_csv(sample_csv, default_source="expo")
    companies = [lead.company for lead in report.leads]
    assert companies == ["Crumb Co", "Barkery Lane"]
    assert len(report.skipped) == 2
    reasons = dict(report.skipped)
    assert set(reasons) == {5, 6}
    assert "blank" in reasons[5]
    assert "email" in reasons[6]
    assert "ImportReport(loaded=2, skipped=2)" == repr(report)


def test_import_csv_coerces_enums_and_source(sample_csv):
    report = import_csv(sample_csv, default_source="expo")
    crumb, barkery = report.leads
    assert crumb.category == Category.COOKIE
    assert crumb.segment == Segment.ESTABLISHED_BRAND
    assert barkery.category == Category.PET_TREAT
    assert crumb.source == "expo"
    assert crumb.city == "Austin"


def test_import_csv_requires_company_column(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("name,website\nA,a.com\n", encoding="utf-8")
    with pytest.raises(ValueError, match="company"):
        import_csv(path)


def test_dedupe_by_domain_then_name():
    leads = [
        Lead(company="A", website="a.com"),
        Lead(company="A Again", website="www.a.com"),
        Lead(company="NoSite"),
        Lead(company="nosite"),
    ]
    assert [lead.company for lead in dedupe(leads)] == ["A", "NoSite"]


def test_search_queries_substitute_category_term():
    queries = search_queries(Category.PET_TREAT)
    assert "google" in queries and "trade_shows" in queries
    assert any("dog treats" in q for q in queries["google"])
    assert all("{category}" not in q for channel in queries.values() for q in channel)


def test_import_csv_reads_signal_columns(tmp_path):
    path = tmp_path / "signals.csv"
    path.write_text(
        "company,website,category,in_national_retail,recent_funding,hiring_ops_or_production\n"
        "Trig Co,trig.com,cookie,true,YES,\n"
        "Plain Co,plain.com,cookie,,no,0\n",
        encoding="utf-8",
    )
    report = import_csv(path)
    trig, plain = report.leads
    assert trig.signals.in_national_retail and trig.signals.recent_funding
    assert not trig.signals.hiring_ops_or_production
    assert not any(v for v in plain.signals.model_dump().values() if isinstance(v, bool))
