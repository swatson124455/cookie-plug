"""Continuous discovery of emerging brands with Claude web search.

This is the research-agent pass turned into a command. For a category it
runs a fixed set of discovery searches through Claude's web search tool,
asks for a JSON list of companies with evidence, validates each entry, and
returns leads ready for the pipeline. It complements ``leadgen watch``,
which only sees brands that reach a press feed.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import anthropic
from pydantic import BaseModel, Field, ValidationError

from leadgen.ai import QualifierError
from leadgen.models import Category, Lead, LeadSignals, Segment
from leadgen.triggers import TRIGGER_SIGNALS

DEFAULT_MODEL = "claude-opus-5"
PROMPT_PATH = Path("prompts/discover.md")
MAX_SEARCHES = 15
MAX_CONTINUATIONS = 4
MAX_TOKENS = 8000
SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": MAX_SEARCHES}

DISCOVERY_QUERIES: dict[Category, tuple[str, ...]] = {
    Category.COOKIE: (
        'new cookie brand launches {year}',
        'cookie startup "co-packer" OR "co-manufacturer" {year}',
        'cookie brand "outgrown" kitchen OR commissary {year}',
        'gluten-free OR vegan cookie brand launches at Sprouts OR "Whole Foods" regional {year}',
        'cookie brand Kickstarter OR StartEngine OR Wefunder {year}',
        'protein cookie brand TikTok Shop launch {year}',
    ),
    Category.BAKERY: (
        'new brownie OR granola OR cracker brand launches {year}',
        'baked goods startup raises pre-seed OR seed {year}',
        'bakery brand "shelf-stable" launch first retail {year}',
        'baked snack brand Faire wholesale new {year}',
    ),
    Category.SNACK: (
        'new snack bar brand launches {year} founder',
        'snack startup "looking for a co-packer" {year}',
    ),
    Category.PET_TREAT: (
        'new dog treat brand launches {year}',
        'dog treat startup founded 2025 OR {year} human-grade baked',
        'dog treat brand "co-packer" OR "commissary" OR "cottage" {year}',
        'pet treat brand launches on Chewy first time {year}',
        'dog treat brand Kickstarter OR StartEngine {year}',
    ),
    Category.PET_FOOD: (
        'new pet food brand launches {year} startup',
        'pet food startup raises seed {year} treats',
    ),
    Category.OTHER: (),
}


class DiscoveredBrand(BaseModel):
    """One entry from the discovery JSON, validated."""

    company: str = Field(min_length=2, max_length=80)
    website: str = ""
    category: Category = Category.OTHER
    trigger: str = ""
    evidence: str = ""
    url: str = ""
    founder: str = ""

    def __repr__(self) -> str:
        return f"DiscoveredBrand({self.company!r}, trigger={self.trigger!r})"


def queries_for(category: Category, year: int | None = None) -> list[str]:
    """The discovery searches for a category, with the year filled in."""
    year = year or date.today().year
    return [q.format(year=year) for q in DISCOVERY_QUERIES.get(category, ())]


def parse_discovery(text: str) -> list[DiscoveredBrand]:
    """Pull the JSON array out of the model's reply and validate each entry."""
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return []
    try:
        raw = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    brands: list[DiscoveredBrand] = []
    for item in raw if isinstance(raw, list) else []:
        try:
            brands.append(DiscoveredBrand(**item))
        except (ValidationError, TypeError):
            continue
    return brands


def discover(category: Category, client: anthropic.Anthropic, model: str = DEFAULT_MODEL, year: int | None = None) -> list[DiscoveredBrand]:
    """Run the discovery searches for a category and return validated brands."""
    searches = queries_for(category, year)
    if not searches:
        return []
    system = PROMPT_PATH.read_text(encoding="utf-8")
    user = f"Category: {category.value}\nTime window: the last 12 months\nSearches to run:\n" + "\n".join(f"- {q}" for q in searches)
    messages: list[dict[str, object]] = [{"role": "user", "content": user}]
    response = _create(client, model, system, messages)
    continuations = 0
    while response.stop_reason == "pause_turn" and continuations < MAX_CONTINUATIONS:
        messages = messages[:1] + [{"role": "assistant", "content": response.content}]
        response = _create(client, model, system, messages)
        continuations += 1
    if response.stop_reason == "refusal":
        raise QualifierError("model declined the discovery request")
    text = "\n".join(block.text for block in response.content if getattr(block, "type", "") == "text")
    return parse_discovery(text)


def _create(client: anthropic.Anthropic, model: str, system: str, messages: list[dict[str, object]]):  # type: ignore[no-untyped-def]
    try:
        return client.messages.create(model=model, max_tokens=MAX_TOKENS, system=system, messages=messages, tools=[SEARCH_TOOL])
    except anthropic.AuthenticationError as exc:
        raise QualifierError("Anthropic API key is missing or invalid") from exc
    except anthropic.RateLimitError as exc:
        raise QualifierError("Anthropic rate limit hit; retry shortly") from exc
    except anthropic.APIStatusError as exc:
        raise QualifierError(f"Anthropic API error {exc.status_code}: {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise QualifierError("could not reach the Anthropic API") from exc


def brand_to_lead(brand: DiscoveredBrand, category: Category) -> Lead:
    """Turn a discovered brand into a pipeline lead with the trigger as a signal."""
    flags = {TRIGGER_SIGNALS[brand.trigger]: True} if brand.trigger in TRIGGER_SIGNALS else {}
    founder_name, founder_title = _split_founder(brand.founder)
    return Lead(
        company=brand.company,
        website=brand.website,
        category=brand.category if brand.category != Category.OTHER else category,
        segment=Segment.EMERGING_BRAND,
        contact_name=founder_name,
        contact_title=founder_title,
        source=f"discover_{category.value}",
        notes=f"{brand.trigger or 'discovered'} ({date.today().isoformat()}): {brand.evidence} {brand.url}".strip(),
        signals=LeadSignals(**flags),
    )


def _split_founder(text: str) -> tuple[str, str]:
    """'Jane Doe, Founder' -> ('Jane Doe', 'Founder'); plain names keep an empty title."""
    if not text.strip():
        return "", ""
    parts = [p.strip() for p in re.split(r"[,(]", text, maxsplit=1)]
    name = parts[0]
    title = parts[1].rstrip(")") if len(parts) > 1 else ""
    return name[:80], title[:80]
