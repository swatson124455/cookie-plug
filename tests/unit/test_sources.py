"""Unit tests for leadgen.sources with mocked HTTP."""

from datetime import date
from pathlib import Path

import httpx

from leadgen.sources import (
    EdgarFormCSource,
    FdaRecallSource,
    FeedConfig,
    RssSource,
    build_sources,
    load_feeds,
    since_date,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_load_feeds_reads_config():
    config = load_feeds(Path(__file__).resolve().parents[2] / "config" / "feeds.yaml")
    assert config.rss and config.fda_terms and config.edgar_queries
    assert "FeedConfig" in repr(config)


def test_fda_source_maps_records():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "product_description" in str(request.url) and "report_date" in str(request.url)
        return httpx.Response(200, json={"results": [
            {"recalling_firm": "Gregory's Foods", "product_description": "Bag Full of Cookies dough", "reason_for_recall": "undeclared peanut", "report_date": "20260115", "classification": "Class I", "state": "MN"},
        ]})

    items = FdaRecallSource(["cookie"], _client(handler)).fetch(date(2026, 1, 1))
    assert len(items) == 1
    assert items[0].company_hint == "Gregory's Foods"
    assert items[0].published == date(2026, 1, 15)
    assert "recalls" in items[0].title and items[0].extra["classification"] == "Class I"
    assert "FdaRecallSource" in repr(FdaRecallSource(["x"], _client(handler)))


def test_fda_source_handles_errors_and_no_terms():
    assert FdaRecallSource([], _client(lambda r: httpx.Response(200))).fetch(date.today()) == []
    assert FdaRecallSource(["cookie"], _client(lambda r: httpx.Response(500))).fetch(date.today()) == []
    assert FdaRecallSource(["cookie"], _client(lambda r: httpx.Response(200, text="nope"))).fetch(date.today()) == []


def test_edgar_source_dedupes_and_names_entity():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"hits": {"hits": [
            {"_id": "1:a.pdf", "_source": {"display_names": ["Legally Addictive Foods, LLC (CIK 0002142533)"], "file_date": "2026-05-01", "form": "C"}},
            {"_id": "1:a.pdf", "_source": {"display_names": ["Legally Addictive Foods, LLC (CIK 0002142533)"], "file_date": "2026-05-01", "form": "C"}},
            {"_id": "2:b.pdf", "_source": {"display_names": [], "file_date": "2026-05-02", "form": "C"}},
        ]}})

    items = EdgarFormCSource(['"cookies"', '"dog treats"'], ["C"], _client(handler)).fetch(date(2026, 1, 1))
    assert len(items) == 1
    assert items[0].company_hint == "Legally Addictive Foods, LLC"
    assert items[0].published == date(2026, 5, 1) and items[0].extra["form"] == "C"


def test_edgar_source_error_returns_empty():
    assert EdgarFormCSource(['"x"'], ["C"], _client(lambda r: httpx.Response(403))).fetch(date.today()) == []


def test_rss_source_parses_rss_and_filters_by_date():
    xml = (FIXTURES / "feed_rss.xml").read_bytes()
    source = RssSource("trade", "https://example.com/rss", _client(lambda r: httpx.Response(200, content=xml)))
    items = source.fetch(date(2026, 9, 1))
    titles = [i.title for i in items]
    assert len(items) == 3 and "Old Bakery Co expands to Kroger" not in titles
    assert items[0].url == "https://example.com/crumb" and items[0].published == date(2026, 9, 21)
    assert source.name == "rss_trade" and "RssSource" in repr(source)


def test_rss_source_parses_atom():
    xml = (FIXTURES / "feed_atom.xml").read_bytes()
    items = RssSource("atom", "https://example.com/atom", _client(lambda r: httpx.Response(200, content=xml))).fetch(date(2026, 9, 1))
    assert len(items) == 1
    assert items[0].url == "https://example.com/muffin" and items[0].published == date(2026, 9, 20)


def test_rss_source_bad_xml_or_http_error():
    assert RssSource("a", "https://x", _client(lambda r: httpx.Response(200, text="<not xml"))).fetch(date.today()) == []
    assert RssSource("a", "https://x", _client(lambda r: httpx.Response(404))).fetch(date.today()) == []


def test_build_sources_and_since():
    config = FeedConfig(rss=[{"name": "a", "url": "https://a"}, {"name": "b", "url": ""}], fda_terms=["cookie"], edgar_queries=['"x"'], edgar_forms=["C"])
    sources = build_sources(config, _client(lambda r: httpx.Response(200)))
    assert [s.name for s in sources] == ["fda_recall", "edgar_filing", "rss_a"]
    assert (date.today() - since_date(7)).days == 7
