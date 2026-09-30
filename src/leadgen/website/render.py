"""What templates see (``site``) and the Jinja environment that renders them.

URLs depend on the build mode: real paths (``/faq/``) for production and
draft builds, hash tokens (``#faq``) for the one-file preview. Templates call
``site.url(...)`` and never hard-code either form.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

from leadgen.website.config import FamilyMember, SiteConfig, display_value, is_placeholder
from leadgen.website.content import FaqItem, Guide
from leadgen.website.facts import FacilityFacts, Line

if TYPE_CHECKING:
    from jinja2 import Environment
    from markupsafe import Markup

    from leadgen.website.pages import Page

MODES = ("production", "draft", "preview")
HYPHENATED = re.compile(r"(\w+(?:-\w+)+)")
INTERNAL_LINK = re.compile(r'<a href="/([a-z0-9/_-]*)(#[^"]*)?">(.*?)</a>', re.DOTALL)


class SiteContext:
    """Everything a template can reach through ``site``."""

    def __init__(self, cfg: SiteConfig, facts: FacilityFacts, mode: str, today: date, static_dir: Path) -> None:
        if mode not in MODES:
            raise ValueError(f"mode must be one of {', '.join(MODES)}")
        self.cfg = cfg
        self.facts = facts
        self.mode = mode
        self.today = today
        self.static_dir = static_dir
        self.guides: list[Guide] = []
        self.faq: list[FaqItem] = []
        self.categories: dict[str, dict[str, Any]] = {}
        self.landings: dict[str, dict[str, Any]] = {}
        self.home: dict[str, Any] = {}
        self.form: dict[str, Any] = {}
        self.css_version = ""

    def __repr__(self) -> str:
        return f"SiteContext(brand={self.cfg.brand!r}, mode={self.mode!r}, guides={len(self.guides)})"

    @property
    def preview(self) -> bool:
        """True for the one-file preview."""
        return self.mode == "preview"

    @property
    def draft(self) -> bool:
        """True for builds that must not be indexed (draft and preview)."""
        return self.mode != "production"

    @staticmethod
    def token(key: str) -> str:
        """Preview route id for a page key: ``home``, ``faq``, ``guide-<slug>``."""
        if not key:
            return "home"
        return key.replace("guides/", "guide-", 1).replace("/", "-")

    @staticmethod
    def path(key: str) -> str:
        """Site-relative path for a page key: ``/``, ``/faq/``."""
        return f"/{key}/" if key else "/"

    def url(self, key: str, anchor: str = "") -> str:
        """Link target for templates: a path in multi-page builds, a hash token in the preview."""
        if self.preview:
            return f"#{self.anchor_id(key, anchor)}" if anchor else f"#{self.token(key)}"
        return self.path(key) + (f"#{anchor}" if anchor else "")

    def anchor_id(self, key: str, name: str) -> str:
        """Element id for a named anchor; unique across the whole preview document."""
        if not self.preview or not key:
            return name
        return f"{self.token(key)}--{name}"

    def abs_url(self, key: str) -> str:
        """Absolute URL for canonical links, sitemaps, and structured data."""
        return self.cfg.base_url + self.path(key)

    def abs_asset(self, path: str) -> str:
        """Absolute URL for a static file such as an Open Graph image."""
        return f"{self.cfg.base_url}/{path}"

    def og_image(self, path: str) -> str:
        """The page's share image when it exists, else the site default."""
        return path if (self.static_dir / path).exists() else "og/default.png"

    @property
    def brand_rest(self) -> str:
        """The part of the brand after the short name (``Co-Packing``), for the two-line lockup."""
        rest = self.cfg.brand.replace(self.cfg.short_name, "", 1).strip()
        return rest if rest != self.cfg.brand else ""

    def tel(self, value: str) -> str:
        """``tel:`` target from a displayed US phone number, or empty for placeholders."""
        digits = "".join(ch for ch in self.real(value) if ch.isdigit())
        if len(digits) == 10:
            digits = "1" + digits
        return f"tel:+{digits}" if len(digits) >= 11 else ""

    def real(self, value: str) -> str:
        """The value, or empty when it is still a placeholder."""
        return "" if is_placeholder(value) else value

    def field(self, value: str) -> "Markup":
        """Render a config value; placeholders show highlighted (drafts and preview only)."""
        from markupsafe import Markup, escape

        if is_placeholder(value):
            hint = "Placeholder: fill in site/shared.yaml or site/sites/<id>/site.yaml"
            return Markup(f'<mark class="todo" title="{hint}">{escape(display_value(value))}</mark>')
        return Markup(escape(value))

    def line(self, key: str) -> Line | None:
        """A production line by key (``cookie``), if the facility runs it."""
        return next((line for line in self.facts.lines if line.key == key), None)

    def guide(self, slug: str) -> Guide | None:
        """A guide by slug."""
        return next((guide for guide in self.guides if guide.slug == slug), None)

    def faq_groups(self) -> list[tuple[str, list[FaqItem]]]:
        """FAQ items grouped, in the order groups first appear in the file."""
        groups: dict[str, list[FaqItem]] = {}
        for item in self.faq:
            groups.setdefault(item.group, []).append(item)
        return list(groups.items())

    def category_for(self, line_key: str) -> tuple[str, dict[str, Any]] | None:
        """This site's page for a production line, as ``(slug, spec)``, if it has one."""
        return next(((slug, spec) for slug, spec in self.categories.items() if spec["line"] == line_key), None)

    def line_url(self, line_key: str) -> str:
        """The line's page on this site, or the capabilities page when the site has none."""
        found = self.category_for(line_key)
        return self.url(found[0]) if found else self.url("capabilities")

    def page_keys(self) -> set[str]:
        """Keys of the indexable content pages this site carries, for resolving Markdown links."""
        keys = {"", "capabilities", "guides", "faq", "about", "contact", "privacy"}
        return keys | set(self.categories) | {f"guides/{guide.slug}" for guide in self.guides}

    def live_siblings(self) -> list[FamilyMember]:
        """Sibling sites with a real domain (placeholders are skipped until the domain is set)."""
        return [member for member in self.cfg.family if not is_placeholder(member.domain)]

    def guide_home(self, slug: str) -> str:
        """Absolute URL of the guide on the first live site in family order that carries it, else empty.

        Shared guides get one canonical home, so four domains never compete with copies of one page.
        """
        for member in self.cfg.family_order():
            if member.id == self.cfg.id:
                return ""
            if slug in member.guides and not is_placeholder(member.domain):
                return f"{member.base_url}/guides/{slug}/"
        return ""

    def sibling_guide(self, slug: str) -> str:
        """Absolute URL of a guide this site lacks but a live sibling carries, else empty."""
        return next((f"{m.base_url}/guides/{slug}/" for m in self.live_siblings() if slug in m.guides), "")

    def guides_for(self, category: str, limit: int = 3) -> list[Guide]:
        """Guides for a category page, category matches first, then general ones."""
        ranked = sorted(self.guides, key=lambda guide: guide.category != category)
        return ranked[:limit]


def rewrite_internal_links(html: str, site: SiteContext) -> str:
    """Point ``/path/`` links written in Markdown at the right target for this build mode and site.

    A link to a page this site does not carry goes to the sibling site that does, or becomes plain text.
    """
    keys = site.page_keys()

    def replace(match: "re.Match[str]") -> str:
        key, anchor, text = match.group(1).strip("/"), match.group(2) or "", match.group(3)
        if key in keys:
            return f'<a href="{site.url(key, anchor.lstrip("#"))}">{text}</a>'
        elsewhere = site.sibling_guide(key.removeprefix("guides/")) if key.startswith("guides/") else ""
        return f'<a href="{elsewhere}">{text}</a>' if elsewhere else text

    return INTERNAL_LINK.sub(replace, html)


def keep_hyphenated(text: str) -> "Markup":
    """Escape text and keep hyphenated words (``Co-Packer``) from breaking at the hyphen."""
    from markupsafe import Markup, escape

    return Markup(HYPHENATED.sub(r'<span class="nw">\1</span>', str(escape(text))))


def environment(templates: Path) -> "Environment":
    """A strict, autoescaping Jinja environment over ``site/templates``."""
    from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

    env = Environment(loader=FileSystemLoader(str(templates)), autoescape=select_autoescape(["html"]),
                      undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)
    env.filters["month"] = lambda value: f"{value:%B} {value.day}, {value.year}"
    env.filters["nobreak"] = keep_hyphenated
    return env


def render_page(env: "Environment", site: SiteContext, page: "Page", layout: str) -> str:
    """Render one page inside a layout (``base.html`` or the preview's ``_route.html``)."""
    from leadgen.website.pages import structured_data

    template = env.get_template(page.template)
    jsonld = structured_data(site, page) if layout == "base.html" else {}
    return template.render(site=site, page=page, layout=layout, jsonld=jsonld, **page.context)
