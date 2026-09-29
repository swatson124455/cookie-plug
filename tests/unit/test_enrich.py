"""Unit tests for leadgen.enrich using an httpx mock transport."""

import json

import httpx

from leadgen.enrich import WebsiteEnricher, extract_signals
from leadgen.models import Category, Lead, Stage


def test_extract_signals_from_shopify_homepage(shopify_html):
    signals = extract_signals(shopify_html)
    assert signals.is_shopify
    assert signals.sells_wholesale
    assert signals.in_national_retail
    assert "whole foods" in signals.retailers_mentioned
    assert signals.out_of_stock
    assert signals.hiring_ops_or_production
    assert signals.has_pet_and_human_lines
    assert Category.COOKIE in signals.detected_categories
    assert signals.site_title.startswith("Crumb Co")
    assert "Whole Foods" in signals.site_description


def test_extract_signals_transition_language():
    html = "<html><body><p>We have outgrown our shared kitchen and are looking for a co-packer.</p></body></html>"
    signals = extract_signals(html)
    assert signals.transitioning and signals.seeking_copacker


def test_extract_signals_plain_page_has_nothing():
    signals = extract_signals("<html><body><p>Hello world</p></body></html>")
    assert not signals.is_shopify
    assert signals.detected_categories == []
    assert signals.site_title == ""


def _transport(shopify_html: str, products: dict | None = None, fail: bool = False) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if fail:
            raise httpx.ConnectError("boom", request=request)
        if request.url.path == "/products.json":
            return httpx.Response(200, json=products or {"products": []})
        return httpx.Response(200, text=shopify_html)

    return httpx.MockTransport(handler)


def test_enricher_fetches_products_json_for_shopify(shopify_html):
    products = {"products": [
        {"variants": [{"available": False}]},
        {"variants": [{"available": True}]},
    ]}
    enricher = WebsiteEnricher(client=httpx.Client(transport=_transport(shopify_html, products)))
    lead = Lead(company="Crumb Co", website="crumbco.com")
    enricher.enrich(lead)
    assert lead.signals.product_count == 2
    assert lead.signals.out_of_stock
    assert lead.category == Category.COOKIE
    assert lead.stage == Stage.ENRICHED
    assert "WebsiteEnricher" in repr(enricher)


def test_enricher_handles_network_failure(shopify_html):
    enricher = WebsiteEnricher(client=httpx.Client(transport=_transport(shopify_html, fail=True)))
    lead = Lead(company="Crumb Co", website="crumbco.com")
    enricher.enrich(lead)
    assert not lead.signals.is_shopify
    assert lead.stage == Stage.ENRICHED


def test_enricher_handles_bad_products_json(shopify_html):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/products.json":
            return httpx.Response(200, text="not json")
        return httpx.Response(200, text=shopify_html)

    enricher = WebsiteEnricher(client=httpx.Client(transport=httpx.MockTransport(handler)))
    lead = Lead(company="Crumb Co", website="crumbco.com")
    enricher.enrich(lead)
    assert lead.signals.product_count is None
    assert lead.signals.is_shopify


def test_enricher_skips_lead_without_website():
    enricher = WebsiteEnricher(client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))))
    lead = Lead(company="No Site")
    enricher.enrich(lead)
    assert "no website" in lead.notes
    assert lead.stage == Stage.NEW


def test_enricher_keeps_explicit_category(shopify_html):
    enricher = WebsiteEnricher(client=httpx.Client(transport=_transport(shopify_html)))
    lead = Lead(company="Crumb Co", website="crumbco.com", category=Category.PET_TREAT)
    enricher.enrich(lead)
    assert lead.category == Category.PET_TREAT
    assert json.loads(lead.model_dump_json())["signals"]["is_shopify"] is True
