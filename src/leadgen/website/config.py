"""Load ``site/config.yaml`` and decide whether it is ready to publish.

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


class SiteConfig(BaseModel):
    """Typed view of ``site/config.yaml``."""

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

    @property
    def base_url(self) -> str:
        """The domain without a trailing slash, for absolute URLs."""
        return self.domain.rstrip("/")

    @property
    def short_name(self) -> str:
        """Short brand for tight spaces; falls back to the full brand."""
        return self.brand_short or self.brand

    def __repr__(self) -> str:
        return f"SiteConfig(brand={self.brand!r}, domain={self.domain!r})"


def load_site_config(path: str | Path) -> SiteConfig:
    """Parse and validate the site config file."""
    with open(path, "r", encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle) or {}
    try:
        return SiteConfig.model_validate(raw)
    except ValueError as exc:
        raise SiteConfigError(f"{path}: {exc}") from exc


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
    problems = [f"{path} is a placeholder" for path, leaf in _walk(cfg.model_dump(), "") if is_placeholder(leaf)]
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
    """Capacity lines that the facility does not run (a config mistake)."""
    return [line for line in cfg.capacity.lines if line not in facility_lines]
