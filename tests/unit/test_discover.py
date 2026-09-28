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


def test_dedupe_merges_by_normalized_name_and_unions_signals():
    from leadgen.models import LeadSignals

    first = Lead(company="Fields Good", category=Category.COOKIE, notes="funding", source="funding_news",
                 signals=LeadSignals(recent_funding=True))
    second = Lead(company="Fields Good, LLC", website="fieldsgood.co", contact_name="Ashley Fields",
                  notes="launch", source="brand_extension", signals=LeadSignals(recent_retail_launch=True))
    merged = dedupe([first, second])
    assert len(merged) == 1
    lead = merged[0]
    assert lead.website == "https://fieldsgood.co"
    assert lead.contact_name == "Ashley Fields"
    assert lead.signals.recent_funding and lead.signals.recent_retail_launch
    assert "funding" in lead.notes and "launch" in lead.notes
    assert lead.source == "funding_news+brand_extension"


def test_dedupe_domain_row_first_then_name_only_row():
    first = Lead(company="Elavi", website="elavi.co", notes="a")
    second = Lead(company="Elavi Inc", notes="b")
    merged = dedupe([first, second])
    assert len(merged) == 1 and "b" in merged[0].notes


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


def test_dedupe_merges_name_containment_but_not_short_names():
    leads = [
        Lead(company="Mightylicious Gluten Free", notes="a"),
        Lead(company="Mightylicious", website="mightylicious.com", notes="b"),
        Lead(company="Rogue"),
        Lead(company="Rogue Bakery Co"),
    ]
    merged = dedupe(leads)
    names = [lead.company for lead in merged]
    assert names == ["Mightylicious Gluten Free", "Rogue", "Rogue Bakery Co"]
    assert merged[0].website == "https://mightylicious.com"
