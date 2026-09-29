"""Import leads from a saved HTML page, such as a trade-show exhibitor directory.

Most exhibitor directories cannot be fetched by a script, but every browser
can save the page. This module reads that saved file and pulls out company
names with their external websites: each outbound link whose text looks
like a company name becomes a candidate. Social networks, the show's own
site, and obvious navigation are filtered out.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from pydantic import BaseModel

from leadgen.models import Category, Lead, Segment

SKIP_DOMAINS: tuple[str, ...] = (
    "facebook.com", "instagram.com", "linkedin.com", "twitter.com", "x.com", "tiktok.com",
    "youtube.com", "pinterest.com", "google.com", "apple.com", "amazon.com", "mailto",
    "expowest.com", "superzoo.org", "globalpetexpo.org", "sweetsandsnacks.com",
    "specialtyfood.com", "smallworldlabs.com", "plma.com", "a2zinc.net", "mapyourshow.com",
)
SKIP_TEXT = re.compile(r"^(website|visit|learn more|view|more|details|booth|home|contact|register|login|www\.|http)", re.IGNORECASE)
MAX_NAME_LENGTH = 60


class HtmlCandidate(BaseModel):
    """A company name and website found on the page."""

    company: str
    website: str

    def __repr__(self) -> str:
        return f"HtmlCandidate({self.company!r}, {self.website!r})"


def _domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host.removeprefix("www.")


def _looks_like_company(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned or len(cleaned) > MAX_NAME_LENGTH or SKIP_TEXT.match(cleaned):
        return False
    return bool(re.search(r"[A-Za-z]", cleaned)) and cleaned.count(" ") <= 7


def extract_candidates(html: str, extra_skip: tuple[str, ...] = ()) -> list[HtmlCandidate]:
    """Company and website pairs from every qualifying outbound link, deduped by domain."""
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    found: list[HtmlCandidate] = []
    skip = SKIP_DOMAINS + tuple(d.lower() for d in extra_skip)
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"]).strip()
        if not href.startswith(("http://", "https://")):
            continue
        domain = _domain(href)
        if not domain or any(domain == s or domain.endswith("." + s) for s in skip) or domain in seen:
            continue
        text = anchor.get_text(" ", strip=True)
        if not _looks_like_company(text):
            text = _name_from_context(anchor)  # link text was "Website" or similar
        if not _looks_like_company(text):
            continue
        seen.add(domain)
        found.append(HtmlCandidate(company=text.strip(), website=f"https://{domain}"))
    return found


def _name_from_context(anchor) -> str:  # type: ignore[no-untyped-def]
    """When the link text is 'Website', use the nearest heading or row text."""
    for parent in anchor.parents:
        heading = parent.find(["h1", "h2", "h3", "h4", "strong", "b"]) if parent else None
        if heading is not None and heading.get_text(strip=True):
            return heading.get_text(" ", strip=True)
        if parent.name in ("tr", "li", "article", "section"):
            return parent.get_text(" ", strip=True).split("\n")[0][:MAX_NAME_LENGTH]
    return ""


def candidates_to_leads(candidates: list[HtmlCandidate], source: str, category: Category = Category.OTHER) -> list[Lead]:
    return [
        Lead(company=c.company, website=c.website, category=category, segment=Segment.UNKNOWN, source=source,
             notes=f"from saved page import ({source})")
        for c in candidates
    ]


def import_html_file(path: str | Path, source: str, category: Category = Category.OTHER, extra_skip: tuple[str, ...] = ()) -> list[Lead]:
    html = Path(path).read_text(encoding="utf-8", errors="replace")
    return candidates_to_leads(extract_candidates(html, extra_skip), source, category)
