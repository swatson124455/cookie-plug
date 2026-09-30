"""Load a site's settings and decide whether it is ready to publish.

One engine builds a family of sites. ``site/shared.yaml`` holds what every
site shares (contact, capacity status, form provider, the family order) and
``site/sites/<id>/site.yaml`` holds what one site owns (brand, domain, which
lines, guides, and pages it carries, and its wording). A site's config is
the shared file with its own file merged over it.

Placeholders start with ``TO_FILL``. Draft and preview builds show them
highlighted; the production build refuses to run while any remain, so a
half-filled site can never reach a public URL.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator

PLACEHOLDER = "TO_FILL"
SITE_ID = re.compile(r"[a-z0-9-]+")
EXAMPLE_HOSTS = ("example.com", "example.org", "example.net", "yourdomain.com")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")


class SiteConfigError(ValueError):
    """The site config is malformed or not ready for the requested build."""


def is_placeholder(value: object) -> bool:
    """True when a config value is still a ``TO_FILL`` placeholder."""
    return isinstance(value, str) and PLACEHOLDER in value


def display_value(value: str) -> str:
    """The human-readable part of a placeholder (``TO_FILL Your Name`` -> ``Your Name``)."""
    return value.replace(PLACEHOLDER, "").strip() or "to fill"


class ContactInfo(BaseModel):
    """Who a visitor reaches. Phone, address, and LinkedIn are optional (empty to omit)."""

    name: str
    title: str = "Partnerships"
    email: str
    phone: str = ""
    address: str = ""
    linkedin: str = ""

    def __repr__(self) -> str:
        return f"ContactInfo(name={self.name!r}, email={self.email!r})"


class CapacityStatus(BaseModel):
    """The dated capacity line: which lines are open, confirmed as of which month."""

    as_of: str
    lines: list[str] = Field(default_factory=list)

    @field_validator("as_of")
    @classmethod
    def _month(cls, value: str) -> str:
        """Require ``YYYY-MM`` so the site can print and age-check the date."""
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", str(value)):
            raise ValueError("capacity.as_of must look like 2026-09")
        return str(value)

    def as_of_date(self) -> date:
        """First day of the confirmed month."""
        year, month = self.as_of.split("-")
        return date(int(year), int(month), 1)

    def label(self) -> str:
        """``September 2026``."""
        confirmed = self.as_of_date()
        return f"{MONTHS[confirmed.month - 1]} {confirmed.year}"

    def age_days(self, today: date) -> int:
        """Days since the start of the confirmed month."""
        return (today - self.as_of_date()).days

    def __repr__(self) -> str:
        return f"CapacityStatus(as_of={self.as_of!r}, lines={self.lines!r})"


class FormSettings(BaseModel):
    """Where the capacity-check form posts."""

    provider: Literal["netlify", "formspree"] = "netlify"
    action: str = ""

    def __repr__(self) -> str:
        return f"FormSettings(provider={self.provider!r})"


class SiteWording(BaseModel):
    """Audience wording that differs between sites; defaults are the co-packing site's."""

    home_title: str = "Co-Packer With Open Capacity"
    home_description: str = ("Open co-packing lines for cookies, baked goods, pet treats, and pet food. Turnkey from "
                             "formulation to shelf-ready case packs. Check capacity for your product.")
    service_name: str = "Co-packing for food and pet brands"
    guides_title: str = "Co-Packer Guides for Food and Pet Brands"
    guides_description: str = ("Plain answers for founders: how to find and qualify a co-packer, minimums and costs, "
                               "retailer requirements, shelf-stable reformulation, and second sourcing.")
    guides_h1: str = "Guides for brands choosing a co-packer"
    guides_lead: str = ("Plain answers to the questions founders ask before, during, and after the move to a co-packer. "
                        "Each one starts with the short answer.")
    faq_title: str = "Co-Packer FAQ: Minimums, Samples, Costs"
    faq_description: str = ("Straight answers on co-packer minimums, sampling, certifications, private label, "
                            "costs, and how working with us works.")
    faq_lead: str = "Straight answers about co-packing, the facility, and how we work."
    about_lead: str = ("We connect brands that need production capacity with a US manufacturer that has it, "
                       "and we run the process until you sign.")
    check_name: str = "capacity check"
    cta: str = "Check capacity"
    cta_long: str = "Check capacity for your product"
    guide_form_title: str = "Is capacity your constraint?"
    guide_form_intro: str = "If this guide describes where your brand is, send the capacity check. We confirm line fit with the facility first."

    def __repr__(self) -> str:
        return f"SiteWording(cta={self.cta!r})"


class FamilyMember(BaseModel):
    """A sibling site, for the footer's family links and cross-site canonical URLs."""

    id: str
    brand: str
    domain: str
    blurb: str = ""
    guides: list[str] = Field(default_factory=list)

    @property
    def base_url(self) -> str:
        """The sibling's domain without a trailing slash."""
        return self.domain.rstrip("/")

    def __repr__(self) -> str:
        return f"FamilyMember(id={self.id!r})"


class SiteConfig(BaseModel):
    """Typed view of one site's merged settings."""

    id: str = "site"
    brand: str
    brand_short: str = ""
    tagline: str
    domain: str
    capacity: CapacityStatus
    reply_within: str = "one business day"
    contact: ContactInfo
    author_bio: str = ""
    form: FormSettings = Field(default_factory=FormSettings)
    analytics_snippet: str = ""
    analytics_hosts: list[str] = Field(default_factory=list)
    indexnow_key: str = ""
    lines: list[str] = Field(default_factory=list)
    categories: list[str] | None = None
    guides: list[str] | None = None
    landings: list[str] | None = None
    family_blurb: str = ""
    wording: SiteWording = Field(default_factory=SiteWording)
    family: list[FamilyMember] = Field(default_factory=list)
    family_order_ids: list[str] = Field(default_factory=list)

    @property
    def base_url(self) -> str:
        """The domain without a trailing slash, for absolute URLs."""
        return self.domain.rstrip("/")

    def family_order(self) -> list[FamilyMember]:
        """All sites, this one included, in family order (siblings keep their order around it)."""
        me = _family_member(self)
        ids = [member.id for member in self.family]
        order = self.family_order_ids or ids + [self.id]
        members = {member.id: member for member in self.family} | {self.id: me}
        return [members[item] for item in order if item in members]

    @property
    def short_name(self) -> str:
        """Short brand for tight spaces; falls back to the full brand."""
        return self.brand_short or self.brand

    def __repr__(self) -> str:
        return f"SiteConfig(id={self.id!r}, brand={self.brand!r}, domain={self.domain!r})"


def _read_yaml(path: Path) -> dict[str, Any]:
    """A YAML mapping, or a SiteConfigError naming the file."""
    with open(path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise SiteConfigError(f"{path}: must be a mapping")
    return raw


def load_site_config(path: str | Path) -> SiteConfig:
    """Parse and validate one complete config file (used for single-file configs and tests)."""
    raw = _read_yaml(Path(path))
    try:
        return SiteConfig.model_validate(raw)
    except ValueError as exc:
        raise SiteConfigError(f"{path}: {exc}") from exc


def merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge two mappings; the override wins, nested mappings merge key by key."""
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def site_ids(site_dir: Path) -> list[str]:
    """The family's site ids, in the order ``site/shared.yaml`` lists them."""
    ids = [str(item) for item in _read_yaml(site_dir / "shared.yaml").get("sites") or []]
    bad = [item for item in ids if not SITE_ID.fullmatch(item) or not (site_dir / "sites" / item / "site.yaml").exists()]
    if bad or not ids:
        raise SiteConfigError(f"{site_dir / 'shared.yaml'}: sites must list folders in site/sites/ (bad: {', '.join(bad) or 'none listed'})")
    return ids


def _family_member(cfg: SiteConfig) -> FamilyMember:
    """The public face of a site, as its siblings see it."""
    return FamilyMember(id=cfg.id, brand=cfg.brand, domain=cfg.domain, blurb=cfg.family_blurb, guides=list(cfg.guides or []))


def load_family(site_dir: Path) -> list[SiteConfig]:
    """Every site's merged config, in family order, each knowing its siblings."""
    shared = _read_yaml(site_dir / "shared.yaml")
    shared.pop("sites", None)
    configs: list[SiteConfig] = []
    for site_id in site_ids(site_dir):
        path = site_dir / "sites" / site_id / "site.yaml"
        try:
            configs.append(SiteConfig.model_validate(merge(shared, _read_yaml(path)) | {"id": site_id}))
        except ValueError as exc:
            raise SiteConfigError(f"{path}: {exc}") from exc
    members = [_family_member(cfg) for cfg in configs]
    order = [member.id for member in members]
    return [cfg.model_copy(update={"family": [m for m in members if m.id != cfg.id], "family_order_ids": order})
            for cfg in configs]


def load_site(site_dir: Path, site_id: str) -> SiteConfig:
    """One site's merged config; the error lists the valid ids."""
    family = {cfg.id: cfg for cfg in load_family(site_dir)}
    if site_id not in family:
        raise SiteConfigError(f"unknown site {site_id!r}: choose one of {', '.join(family)}")
    return family[site_id]


def _walk(value: object, prefix: str) -> list[tuple[str, object]]:
    """Flatten nested dicts and lists into ``(dotted.path, leaf)`` pairs."""
    if isinstance(value, dict):
        pairs: list[tuple[str, object]] = []
        for key, item in value.items():
            pairs.extend(_walk(item, f"{prefix}.{key}" if prefix else str(key)))
        return pairs
    if isinstance(value, list):
        return [pair for index, item in enumerate(value) for pair in _walk(item, f"{prefix}[{index}]")]
    return [(prefix, value)]


def publish_problems(cfg: SiteConfig) -> list[str]:
    """Everything that must be fixed before a production build, one line each."""
    own = cfg.model_dump(exclude={"family", "family_order_ids"})
    problems = [f"{path} is a placeholder" for path, leaf in _walk(own, "") if is_placeholder(leaf)]
    if not is_placeholder(cfg.domain):
        if not cfg.domain.startswith("https://"):
            problems.append("domain must start with https://")
        if any(host in cfg.domain for host in EXAMPLE_HOSTS):
            problems.append("domain is an example domain")
    if not is_placeholder(cfg.contact.email) and not EMAIL_PATTERN.match(cfg.contact.email):
        problems.append("contact.email is not an email address")
    if not cfg.contact.name.strip():
        problems.append("contact.name is empty")
    if cfg.form.provider == "formspree" and not cfg.form.action.startswith("https://"):
        problems.append("form.action must be the https Formspree endpoint when provider is formspree")
    return problems


def unknown_lines(cfg: SiteConfig, facility_lines: list[str]) -> list[str]:
    """Capacity or site lines that the facility does not run (a config mistake)."""
    return [line for line in dict.fromkeys(cfg.capacity.lines + cfg.lines) if line not in facility_lines]
