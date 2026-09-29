"""Turn feed items into leads with a trigger attached.

Two extractors share one output shape. The rule-based one is free and
runs offline: keyword lists decide category and trigger type, and the
company name is cut from the headline. The Claude one reads the same item
and returns the same structure with better judgment; ``watch --ai`` uses it
and falls back to the rules on any API error.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

import anthropic
from pydantic import BaseModel, Field

from leadgen.models import Category, Lead, LeadSignals, Segment
from leadgen.sources import RawItem

CATEGORY_KEYWORDS: dict[Category, tuple[str, ...]] = {
    Category.PET_TREAT: ("dog treat", "dog treats", "cat treat", "cat treats", "pet treat", "pet treats", "dog biscuit", "dog chews", "dental chew"),
    Category.PET_FOOD: ("dog food", "cat food", "pet food", "kibble", "pet nutrition"),
    Category.COOKIE: ("cookie", "cookies", "biscotti", "shortbread", "macaron"),
    Category.BAKERY: ("bakery", "baked goods", "brownie", "brownies", "muffin", "muffins", "granola", "cracker", "crackers", "donut", "donuts", "bread", "cake"),
    Category.SNACK: ("snack", "snacks", "protein bar", "granola bar", "chips", "puffs"),
}

TRIGGER_KEYWORDS: dict[str, tuple[str, ...]] = {
    "seeking_copacker": ("looking for a co-packer", "seeking a co-packer", "seeking co-manufacturer", "looking for a manufacturer", "co-packer wanted", "rfp for co-manufacturing"),
    "transition": ("outgrown", "outgrowing", "moves production", "moving production", "transitions to", "shelf-stable version", "now shelf-stable", "first packaged", "from food truck", "from the food truck", "from farmers market", "commissary", "shared kitchen", "cottage", "expand production capacity", "production expansion", "scale production", "new facility", "pivots to", "pivot to", "enters retail", "first retail"),
    "recall": ("recall", "recalls", "recalled"),
    "closure": ("closing", "closes plant", "to close", "shuts down", "shutting down", "bankruptcy", "chapter 11", "layoffs", "ceases production"),
    "funding": ("raises", "raised", "funding", "seed round", "series a", "series b", "investment", "closes round", "secures $", "crowdfunding", "reg cf", "form c"),
    "retail_launch": ("launches at", "launches in", "now available at", "now at", "expands to", "expands into", "rolls out", "lands at", "lands in", "debuts at", "in stores", "nationwide", "target", "walmart", "costco", "whole foods", "kroger", "sprouts", "chewy", "petco", "petsmart", "wegmans", "h-e-b"),
    "hiring": ("is hiring", "hiring", "job opening", "production manager", "plant manager", "co-packer manager", "co-manufacturing manager"),
    "new_product": ("launches", "introduces", "debuts", "unveils", "new product", "new line", "new flavor"),
}

# Headline verbs after which the company name ends. Longest first.
_HEADLINE_VERBS = (
    "to launch", "to open", "to close", "rolls out", "now available", "closes round",
    "launches", "raises", "expands", "debuts", "introduces", "announces", "secures", "lands",
    "unveils", "recalls", "closes", "files", "opens", "partners", "adds", "brings", "hires",
    "names", "appoints", "wins", "enters", "signs", "acquires", "moves", "selected", "taps",
)
_VERB_PATTERN = re.compile(r"^(?P<company>.+?)\s+(?:" + "|".join(re.escape(v) for v in _HEADLINE_VERBS) + r")\b", re.IGNORECASE)


class TriggerExtraction(BaseModel):
    """What an extractor concluded about one feed item."""

    is_relevant: bool = Field(description="True only for a brand or buyer in cookies, bakery, snacks, pet treats, or pet food")
    company: str = Field(default="", description="The company the item is about, cleanly named")
    website: str = Field(default="", description="Company domain if it appears in the item, else empty")
    category: Category = Category.OTHER
    trigger: str = Field(default="", description="One of recall, closure, funding, retail_launch, hiring, new_product, or empty")
    evidence: str = Field(default="", description="One sentence quoting the item")

    def __repr__(self) -> str:
        return f"TriggerExtraction(company={self.company!r}, trigger={self.trigger!r}, relevant={self.is_relevant})"


class Extractor(Protocol):
    def extract(self, item: RawItem) -> TriggerExtraction: ...


def classify_category(text: str) -> Category:
    """First category whose keywords appear; pet before human so 'dog cookie' is pet."""
    lowered = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(k in lowered for k in keywords):
            return category
    return Category.OTHER


def classify_trigger(text: str) -> str:
    """First trigger whose keywords appear, in priority order."""
    lowered = text.lower()
    for trigger, keywords in TRIGGER_KEYWORDS.items():
        if any(k in lowered for k in keywords):
            return trigger
    return ""


def company_from_headline(title: str) -> str:
    """Cut the subject off the front of a press headline; empty if no verb found."""
    cleaned = re.split(r"\s+[|:]\s+", title, maxsplit=1)[0].strip()
    match = _VERB_PATTERN.match(cleaned)
    if not match:
        return ""
    company = match.group("company").strip(" ,'\"")
    return "" if len(company) > 60 or len(company) < 2 else company


class RuleBasedExtractor:
    """Keyword classification; free and deterministic."""

    def __repr__(self) -> str:
        return "RuleBasedExtractor()"

    def extract(self, item: RawItem) -> TriggerExtraction:
        text = f"{item.title} {item.summary}"
        category = classify_category(text)
        trigger = classify_trigger(text)
        company = item.company_hint or company_from_headline(item.title)
        relevant = category != Category.OTHER and bool(company) and bool(trigger)
        return TriggerExtraction(
            is_relevant=relevant, company=company, category=category, trigger=trigger,
            evidence=item.title[:200],
        )


class ClaudeExtractor:
    """Same output, produced by Claude with structured outputs; rules as fallback."""

    def __init__(self, client: anthropic.Anthropic, model: str = "claude-opus-5", prompt_path: str = "prompts/extract_trigger.md") -> None:
        self._client = client
        self._model = model
        self._system = Path(prompt_path).read_text(encoding="utf-8")
        self._fallback = RuleBasedExtractor()

    def __repr__(self) -> str:
        return f"ClaudeExtractor(model={self._model!r})"

    def extract(self, item: RawItem) -> TriggerExtraction:
        user = f"Source: {item.source}\nTitle: {item.title}\nSummary: {item.summary}\nURL: {item.url}\nCompany named by the feed: {item.company_hint or 'none'}"
        try:
            response = self._client.messages.parse(
                model=self._model, max_tokens=512, system=self._system,
                messages=[{"role": "user", "content": user}], output_format=TriggerExtraction,
            )
        except (anthropic.APIStatusError, anthropic.APIConnectionError):
            return self._fallback.extract(item)
        if response.stop_reason == "refusal" or response.parsed_output is None:
            return self._fallback.extract(item)
        return response.parsed_output


TRIGGER_SIGNALS: dict[str, str] = {
    "seeking_copacker": "seeking_copacker",
    "transition": "transitioning",
    "retail_launch": "recent_retail_launch",
    "funding": "recent_funding",
    "hiring": "hiring_ops_or_production",
    "recall": "recent_recall",
    "closure": "recent_recall",  # a closure is a supply disruption; same weight class
    "new_product": "new_product_launch",
}


def extraction_to_lead(item: RawItem, extraction: TriggerExtraction) -> Lead | None:
    """A new lead carrying the trigger as a signal and the evidence in notes."""
    if not extraction.is_relevant or not extraction.company:
        return None
    flags = {TRIGGER_SIGNALS[extraction.trigger]: True} if extraction.trigger in TRIGGER_SIGNALS else {}
    when = item.published.isoformat() if item.published else "undated"
    return Lead(
        company=extraction.company,
        website=extraction.website,
        category=extraction.category,
        segment=Segment.UNKNOWN,
        source=f"watch_{item.source}",
        notes=f"{extraction.trigger or 'signal'} ({when}): {extraction.evidence or item.title} {item.url}".strip(),
        signals=LeadSignals(**flags),
    )
