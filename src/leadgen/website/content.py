"""Load site content: Markdown guides with front matter, the FAQ, and category copy.

Content files are data, not templates: guides are Markdown with a YAML front
matter block, the FAQ and category pages are YAML. FAQ answers can carry a
``when_confirmed`` variant that is used only once the named facility field is
confirmed, so a specific number never appears before the facility commits to it.
"""

from __future__ import annotations

import html as html_lib
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable

import yaml

from leadgen.website.facts import FacilityFacts

FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)
GUIDE_REQUIRED = ("title", "description", "date", "summary")
CATEGORY_KEYS = ("cookie-co-packer", "bakery-co-packer", "dog-treat-co-packer", "pet-food-co-packer", "general")


class ContentError(ValueError):
    """A content file is missing required fields or cannot be parsed."""


@dataclass(frozen=True)
class TocEntry:
    """One H2 in a guide, for the on-page contents list."""

    anchor: str
    text: str


@dataclass
class Guide:
    """A pillar guide rendered from Markdown."""

    slug: str
    title: str
    description: str
    published: date
    updated: date
    summary: str
    markdown: str
    html: str = ""
    seo_title: str = ""
    category: str = "general"
    related: list[str] = field(default_factory=list)
    sources: list[dict[str, str]] = field(default_factory=list)
    toc: list[TocEntry] = field(default_factory=list)

    @property
    def short_title(self) -> str:
        """Title for tight spaces: the part before a colon or parenthesis."""
        return self.title.split(":")[0].split(" (")[0].strip()

    @property
    def word_count(self) -> int:
        """Words in the Markdown body plus the summary."""
        return len(re.findall(r"[A-Za-z0-9']+", self.summary + " " + self.markdown))

    @property
    def reading_minutes(self) -> int:
        """Reading time at about 230 words a minute, at least one."""
        return max(1, round(self.word_count / 230))

    def __repr__(self) -> str:
        return f"Guide(slug={self.slug!r}, words={self.word_count})"


@dataclass(frozen=True)
class FaqItem:
    """A question with the answer resolved against confirmed facts."""

    question: str
    answer: str
    group: str = "General"
    featured: bool = False


def split_front_matter(text: str, source: str = "content") -> tuple[dict[str, Any], str]:
    """Separate the YAML front matter block from the Markdown body."""
    match = FRONT_MATTER.match(text.lstrip("﻿"))
    if not match:
        raise ContentError(f"{source}: missing '---' front matter block")
    meta = yaml.safe_load(match.group(1)) or {}
    if not isinstance(meta, dict):
        raise ContentError(f"{source}: front matter must be a mapping")
    return meta, match.group(2).strip() + "\n"


def _as_date(value: Any, source: str, key: str) -> date:
    """Accept a YAML date or an ISO string."""
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ContentError(f"{source}: {key} must be YYYY-MM-DD") from exc


def render_markdown(text: str, id_prefix: str = "") -> tuple[str, list[TocEntry]]:
    """Markdown to HTML with heading ids (prefixed, for the one-file preview) and an H2 list."""
    import markdown
    from markdown.extensions.toc import slugify

    def prefixed(value: str, separator: str) -> str:
        return id_prefix + slugify(value, separator)

    converter = markdown.Markdown(
        extensions=["tables", "sane_lists", "smarty", "toc"],
        extension_configs={"toc": {"slugify": prefixed, "toc_depth": "2-2"}},
        output_format="html",
    )
    html = converter.convert(text)
    toc = [TocEntry(token["id"], html_lib.unescape(token["name"])) for token in getattr(converter, "toc_tokens", [])]
    return html, toc


def load_guide(path: Path, id_prefix: Callable[[str], str] = lambda slug: "") -> Guide:
    """Parse one guide file; raise ContentError when required front matter is missing."""
    meta, body = split_front_matter(path.read_text(encoding="utf-8"), str(path))
    missing = [key for key in GUIDE_REQUIRED if not meta.get(key)]
    if missing:
        raise ContentError(f"{path}: missing {', '.join(missing)}")
    category = str(meta.get("category") or "general")
    if category not in CATEGORY_KEYS:
        raise ContentError(f"{path}: category must be one of {', '.join(CATEGORY_KEYS)}")
    published = _as_date(meta["date"], str(path), "date")
    guide = Guide(
        slug=path.stem, title=str(meta["title"]).strip(), description=str(meta["description"]).strip(),
        published=published, updated=_as_date(meta.get("updated") or published, str(path), "updated"),
        summary=str(meta["summary"]).strip(), markdown=body, seo_title=str(meta.get("seo_title") or "").strip(),
        category=category, related=[str(slug) for slug in meta.get("related") or []],
        sources=[{"title": str(s.get("title", "")), "url": str(s.get("url", ""))} for s in meta.get("sources") or []],
    )
    guide.html, guide.toc = render_markdown(body, id_prefix(guide.slug))
    return guide


def load_guides(directory: Path, id_prefix: Callable[[str], str] = lambda slug: "") -> list[Guide]:
    """All guides, newest first, with related slugs checked."""
    guides = [load_guide(path, id_prefix) for path in sorted(directory.glob("*.md"))]
    known = {guide.slug for guide in guides}
    for guide in guides:
        unknown = [slug for slug in guide.related if slug not in known]
        if unknown:
            raise ContentError(f"guide {guide.slug}: related guides not found: {', '.join(unknown)}")
    return sorted(guides, key=lambda guide: (guide.published, guide.title), reverse=True)


def select_guides(guides: list[Guide], only: list[str] | None, source: str = "site") -> list[Guide]:
    """The guides a site carries (None means all), newest first, with related links kept inside the set."""
    if only is None:
        return guides
    by_slug = {guide.slug: guide for guide in guides}
    chosen = pick(by_slug, only, f"{source}: guides")
    for guide in chosen.values():
        guide.related = [slug for slug in guide.related if slug in chosen]
    return [guide for guide in guides if guide.slug in chosen]


def resolve_answer(item: dict[str, Any], facts: FacilityFacts) -> str:
    """Pick the confirmed-fact answer when its field is confirmed, else the default answer."""
    variant = item.get("when_confirmed") or {}
    value = facts.value(str(variant.get("field", ""))) if variant else None
    if value is not None:
        shown = f"{value:,}" if isinstance(value, int) and not isinstance(value, bool) else value
        return str(variant["a"]).format(value=shown)
    return str(item["a"]).strip()


def fill_tokens(text: str, tokens: dict[str, str] | None) -> str:
    """Replace ``{name}`` tokens (such as ``{reply_within}``) with site settings."""
    for name, value in (tokens or {}).items():
        text = text.replace("{" + name + "}", value)
    return text


def load_faq(path: Path, facts: FacilityFacts, tokens: dict[str, str] | None = None, site_id: str = "") -> list[FaqItem]:
    """The FAQ with every answer resolved; items tagged ``sites: [...]`` appear only on those sites."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    items: list[FaqItem] = []
    for index, item in enumerate(raw):
        if not item.get("q") or not item.get("a"):
            raise ContentError(f"{path}: item {index + 1} needs q and a")
        if site_id and item.get("sites") and site_id not in item["sites"]:
            continue
        answer = fill_tokens(resolve_answer(item, facts), tokens)
        items.append(FaqItem(str(item["q"]).strip(), answer, str(item.get("group") or "General"), bool(item.get("featured"))))
    return items


def pick(available: dict[str, Any], only: list[str] | None, source: str) -> dict[str, Any]:
    """The entries a site lists, in its order; None means all. Unknown names are an error."""
    if only is None:
        return available
    missing = [name for name in only if name not in available]
    if missing:
        raise ContentError(f"{source}: not found: {', '.join(missing)}")
    return {name: available[name] for name in only}


def load_categories(path: Path, facts: FacilityFacts, only: list[str] | None = None) -> dict[str, dict[str, Any]]:
    """Category page copy keyed by slug (limited to ``only``), with each page's questions resolved."""
    raw = pick(yaml.safe_load(path.read_text(encoding="utf-8")) or {}, only, str(path))
    pages: dict[str, dict[str, Any]] = {}
    for slug, spec in raw.items():
        for key in ("line", "h1", "title", "description", "intro"):
            if not spec.get(key):
                raise ContentError(f"{path}: {slug} needs {key}")
        spec = dict(spec)
        spec["questions"] = [FaqItem(str(q["q"]).strip(), resolve_answer(q, facts)) for q in spec.get("questions") or []]
        pages[str(slug)] = spec
    return pages


def load_landings(path: Path, only: list[str] | None = None) -> dict[str, dict[str, Any]]:
    """Ad landing pages keyed by slug (limited to ``only``); an absent file means none."""
    if not path.exists():
        return {}
    raw = pick(yaml.safe_load(path.read_text(encoding="utf-8")) or {}, only, str(path))
    for slug, spec in raw.items():
        for key in ("title", "description", "h1", "intro", "points"):
            if not spec.get(key):
                raise ContentError(f"{path}: {slug} needs {key}")
        if not re.fullmatch(r"[a-z0-9-]+", str(slug)):
            raise ContentError(f"{path}: landing page slug {slug!r} must be lowercase letters, digits, and dashes")
    return {str(slug): dict(spec) for slug, spec in raw.items()}
