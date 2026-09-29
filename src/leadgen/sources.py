"""Public trigger feeds: FDA recalls, SEC EDGAR Reg CF filings, trade-press RSS.

Each source turns a public feed into :class:`RawItem` records. Nothing here
decides whether an item is a lead; that is :mod:`leadgen.triggers`. All
sources take an injected ``httpx.Client`` so tests never touch the network.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from typing import Any, Protocol

import httpx
import yaml
from pydantic import BaseModel, Field

DEFAULT_TIMEOUT_SECONDS = 20.0
OPENFDA_URL = "https://api.fda.gov/food/enforcement.json"
EDGAR_URL = "https://efts.sec.gov/LATEST/search-index"
# The SEC asks automated clients to identify themselves with a contact.
DEFAULT_SEC_USER_AGENT = "cookie-plug-leadgen/0.1 (set LEADGEN_SEC_USER_AGENT to your name and email)"


class RawItem(BaseModel):
    """One headline-sized fact from a feed, before any interpretation."""

    source: str
    title: str
    summary: str = ""
    url: str = ""
    published: date | None = None
    company_hint: str = ""  # set when the feed itself names the company (FDA, EDGAR)
    extra: dict[str, Any] = Field(default_factory=dict)

    def __repr__(self) -> str:
        return f"RawItem(source={self.source!r}, title={self.title[:50]!r})"


class Source(Protocol):
    """Anything that can be polled for items newer than a date."""

    name: str

    def fetch(self, since: date) -> list[RawItem]: ...


class FeedConfig(BaseModel):
    """Parsed ``config/feeds.yaml``."""

    rss: list[dict[str, str]] = Field(default_factory=list)
    fda_terms: list[str] = Field(default_factory=list)
    edgar_queries: list[str] = Field(default_factory=list)
    edgar_forms: list[str] = Field(default_factory=list)

    def __repr__(self) -> str:
        return f"FeedConfig(rss={len(self.rss)}, fda_terms={len(self.fda_terms)}, edgar_queries={len(self.edgar_queries)})"


def load_feeds(path: str = "config/feeds.yaml") -> FeedConfig:
    with open(path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return FeedConfig(
        rss=list(raw.get("rss") or []),
        fda_terms=list((raw.get("fda") or {}).get("terms") or []),
        edgar_queries=list((raw.get("edgar") or {}).get("queries") or []),
        edgar_forms=list((raw.get("edgar") or {}).get("forms") or []),
    )


def default_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": os.environ.get("LEADGEN_SEC_USER_AGENT", DEFAULT_SEC_USER_AGENT)},
        timeout=DEFAULT_TIMEOUT_SECONDS,
        follow_redirects=True,
    )


class FdaRecallSource:
    """Food and pet-food recalls from the openFDA enforcement endpoint."""

    name = "fda_recall"

    def __init__(self, terms: list[str], client: httpx.Client, limit: int = 100) -> None:
        self._terms = terms
        self._client = client
        self._limit = limit

    def __repr__(self) -> str:
        return f"FdaRecallSource(terms={len(self._terms)})"

    def fetch(self, since: date) -> list[RawItem]:
        if not self._terms:
            return []
        terms = "+OR+".join(f'"{t.replace(" ", "+")}"' for t in self._terms)
        window = f"[{since.strftime('%Y%m%d')}+TO+{date.today().strftime('%Y%m%d')}]"
        query = f"product_description:({terms})+AND+report_date:{window}"
        try:
            response = self._client.get(f"{OPENFDA_URL}?search={query}&limit={self._limit}")
            response.raise_for_status()
            results = response.json().get("results", [])
        except (httpx.HTTPError, ValueError):
            return []
        return [self._to_item(r) for r in results if isinstance(r, dict)]

    def _to_item(self, record: dict[str, Any]) -> RawItem:
        firm = str(record.get("recalling_firm", "")).strip()
        published = _parse_date(str(record.get("report_date", "")), "%Y%m%d")
        return RawItem(
            source=self.name,
            title=f"{firm} recalls {str(record.get('product_description', ''))[:120]}",
            summary=str(record.get("reason_for_recall", ""))[:400],
            url=f"https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts?search={firm.replace(' ', '+')}",
            published=published,
            company_hint=firm,
            extra={"classification": record.get("classification", ""), "state": record.get("state", "")},
        )


class EdgarFormCSource:
    """Reg CF and Reg D filings that mention our categories, via EDGAR full-text search."""

    name = "edgar_filing"

    def __init__(self, queries: list[str], forms: list[str], client: httpx.Client) -> None:
        self._queries = queries
        self._forms = forms or ["C"]
        self._client = client

    def __repr__(self) -> str:
        return f"EdgarFormCSource(queries={len(self._queries)})"

    def fetch(self, since: date) -> list[RawItem]:
        items: list[RawItem] = []
        seen: set[str] = set()
        for query in self._queries:
            for hit in self._search(query, since):
                source = hit.get("_source", {})
                names = source.get("display_names") or []
                entity = str(names[0]).split(" (CIK")[0].strip() if names else ""
                key = f"{entity}|{source.get('file_date', '')}"
                if not entity or key in seen:
                    continue
                seen.add(key)
                items.append(
                    RawItem(
                        source=self.name,
                        title=f"{entity} filed Form {source.get('form', '?')} mentioning {query}",
                        summary=f"Filing date {source.get('file_date', '')}; matched {query}",
                        url=f"https://efts.sec.gov/LATEST/search-index?q={query}&forms={source.get('form', 'C')}",
                        published=_parse_date(str(source.get("file_date", "")), "%Y-%m-%d"),
                        company_hint=entity,
                        extra={"form": source.get("form", ""), "hit_id": hit.get("_id", "")},
                    )
                )
        return items

    def _search(self, query: str, since: date) -> list[dict[str, Any]]:
        params = {
            "q": query,
            "forms": ",".join(self._forms),
            "dateRange": "custom",
            "startdt": since.isoformat(),
            "enddt": date.today().isoformat(),
        }
        try:
            response = self._client.get(EDGAR_URL, params=params)
            response.raise_for_status()
            return list(response.json().get("hits", {}).get("hits", []))
        except (httpx.HTTPError, ValueError):
            return []


class RssSource:
    """Trade-press headlines from an RSS 2.0 or Atom feed."""

    name = "rss"

    def __init__(self, name: str, url: str, client: httpx.Client) -> None:
        self.name = f"rss_{name}"
        self._url = url
        self._client = client

    def __repr__(self) -> str:
        return f"RssSource(name={self.name!r})"

    def fetch(self, since: date) -> list[RawItem]:
        try:
            response = self._client.get(self._url)
            response.raise_for_status()
            root = ET.fromstring(response.content)
        except (httpx.HTTPError, ET.ParseError):
            return []
        items = [self._entry(node) for node in root.iter() if _local(node.tag) in ("item", "entry")]
        return [i for i in items if i.title and (i.published is None or i.published >= since)]

    def _entry(self, node: ET.Element) -> RawItem:
        fields = {_local(child.tag): child for child in node}
        title = _text(fields.get("title"))
        link_node = fields.get("link")
        url = (link_node.get("href") if link_node is not None and link_node.get("href") else _text(link_node))
        summary = _text(fields.get("description")) or _text(fields.get("summary")) or _text(fields.get("content"))
        published_raw = _text(fields.get("pubDate")) or _text(fields.get("published")) or _text(fields.get("updated"))
        return RawItem(source=self.name, title=title, summary=summary[:400], url=url, published=_parse_any_date(published_raw))


def build_sources(config: FeedConfig, client: httpx.Client) -> list[Source]:
    """Every configured source, in polling order."""
    sources: list[Source] = [
        FdaRecallSource(config.fda_terms, client),
        EdgarFormCSource(config.edgar_queries, config.edgar_forms, client),
    ]
    sources.extend(RssSource(feed["name"], feed["url"], client) for feed in config.rss if feed.get("url"))
    return sources


def since_date(days: int) -> date:
    return (datetime.now(timezone.utc) - timedelta(days=days)).date()


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(node: ET.Element | None) -> str:
    return (node.text or "").strip() if node is not None else ""


def _parse_date(value: str, fmt: str) -> date | None:
    try:
        return datetime.strptime(value, fmt).date()
    except ValueError:
        return None


def _parse_any_date(value: str) -> date | None:
    """RSS uses RFC 822, Atom uses ISO 8601; accept both, fail quietly."""
    if not value:
        return None
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.replace("Z", "+0000")[:31], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None
