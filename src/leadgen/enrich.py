"""Website enrichment using only public pages.

For each lead we fetch the homepage and, when the site is a Shopify store,
the public ``/products.json`` endpoint that every Shopify storefront serves.
No logins, no scraping of protected platforms. The enricher is injectable
with an ``httpx.Client`` so tests never hit the network.
"""

from __future__ import annotations

import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

from leadgen.models import Category, Lead, LeadSignals, Stage

USER_AGENT = "Mozilla/5.0 (compatible; cookie-plug-leadgen/0.1; +https://github.com/swatson124455/cookie-plug)"
DEFAULT_TIMEOUT_SECONDS = 15.0
MAX_PRODUCTS_PAGE = 250

NATIONAL_RETAILERS: tuple[str, ...] = (
    "whole foods", "target", "walmart", "costco", "kroger", "sprouts", "wegmans",
    "trader joe", "publix", "h-e-b", "heb", "albertsons", "safeway", "petco",
    "petsmart", "chewy", "pet supplies plus", "tractor supply", "cvs", "walgreens",
)

KEYWORDS: dict[str, tuple[str, ...]] = {
    "wholesale": ("wholesale", "faire.com", "bulk orders", "stockists", "become a retailer"),
    "copacker": ("co-packer", "copacker", "co-packing", "contract manufactur", "co-manufactur"),
    "private_label": ("private label", "white label"),
    "hiring": ("production manager", "operations manager", "plant manager", "production associate", "we're hiring", "we are hiring", "join our team"),
    "own_facility": ("our own facility", "made in our own", "our own bakery", "we own our factory"),
    "seeking": ("looking for a co-packer", "seeking a co-packer", "looking for a manufacturer", "seeking a manufacturer", "co-packer wanted"),
    "transition": ("outgrown", "outgrowing", "shared kitchen", "commissary", "cottage food", "moving production", "now shelf-stable", "now shelf stable", "coming soon to stores", "first retail", "new format", "we're growing", "we are growing", "expanding production"),
}

CATEGORY_TERMS: dict[Category, tuple[str, ...]] = {
    Category.COOKIE: ("cookie", "cookies", "biscotti", "macaron"),
    Category.BAKERY: ("bakery", "baked goods", "brownie", "muffin", "granola", "bread", "cake", "cracker"),
    Category.PET_TREAT: ("dog treat", "cat treat", "pet treat", "dog biscuit", "chews"),
    Category.PET_FOOD: ("dog food", "cat food", "pet food", "kibble"),
    Category.SNACK: ("snack", "protein bar", "granola bar", "chips"),
}


class WebsiteEnricher:
    """Fetch public signals for a lead's website."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=DEFAULT_TIMEOUT_SECONDS,
            follow_redirects=True,
        )

    def __repr__(self) -> str:
        return f"WebsiteEnricher(client={type(self._client).__name__})"

    def enrich(self, lead: Lead) -> Lead:
        """Populate ``lead.signals`` from the homepage and Shopify catalog."""
        if not lead.website:
            lead.notes = (lead.notes + " | no website to enrich").strip(" |")
            return lead
        html = self._get_text(lead.website)
        signals = extract_signals(html) if html else LeadSignals()
        if signals.is_shopify:
            products = self._get_json(f"{lead.website}/products.json?limit={MAX_PRODUCTS_PAGE}")
            _apply_products(signals, products)
        lead.signals = signals
        if lead.category == Category.OTHER and signals.detected_categories:
            lead.category = signals.detected_categories[0]
        if lead.stage == Stage.NEW:
            lead.stage = Stage.ENRICHED
        lead.touch()
        return lead

    def _get_text(self, url: str) -> str:
        try:
            response = self._client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPError:
            return ""

    def _get_json(self, url: str) -> dict[str, Any]:
        try:
            response = self._client.get(url)
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, dict) else {}
        except (httpx.HTTPError, ValueError):
            return {}


def extract_signals(html: str) -> LeadSignals:
    """Parse a homepage into :class:`LeadSignals`. Pure function, easy to test."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True).lower()
    lowered_html = html.lower()
    title = soup.title.get_text(strip=True) if soup.title else ""
    description_tag = soup.find("meta", attrs={"name": "description"})
    description = str(description_tag.get("content", "")) if description_tag else ""

    retailers = [name for name in NATIONAL_RETAILERS if name in text]
    detected = [cat for cat, terms in CATEGORY_TERMS.items() if any(t in text for t in terms)]
    has_pet = any(c in (Category.PET_TREAT, Category.PET_FOOD) for c in detected)
    has_human = any(c in (Category.COOKIE, Category.BAKERY, Category.SNACK) for c in detected)

    return LeadSignals(
        is_shopify="cdn.shopify.com" in lowered_html or "shopify" in lowered_html,
        sells_wholesale=_has_any(text, KEYWORDS["wholesale"]),
        in_national_retail=bool(retailers),
        retailers_mentioned=retailers,
        mentions_copacker=_has_any(text, KEYWORDS["copacker"]),
        mentions_private_label=_has_any(text, KEYWORDS["private_label"]),
        hiring_ops_or_production=_has_any(text, KEYWORDS["hiring"]),
        out_of_stock=bool(re.search(r"sold out|out of stock|back in stock", text)),
        explicit_own_facility_only=_has_any(text, KEYWORDS["own_facility"]),
        seeking_copacker=_has_any(text, KEYWORDS["seeking"]),
        transitioning=_has_any(text, KEYWORDS["transition"]),
        has_pet_and_human_lines=has_pet and has_human,
        detected_categories=detected,
        site_title=title[:200],
        site_description=description[:300],
    )


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _apply_products(signals: LeadSignals, payload: dict[str, Any]) -> None:
    """Read product count and stock state from a Shopify products.json payload."""
    products = payload.get("products")
    if not isinstance(products, list):
        return
    signals.product_count = len(products)
    for product in products:
        variants = product.get("variants") or []
        if variants and all(v.get("available") is False for v in variants):
            signals.out_of_stock = True
            break
