"""Website capacity-check submissions into the lead pipeline.

The site's Netlify form ``capacity-check`` is the warmest source the engine
has: a brand saying what it makes, how much, and when. Submissions arrive as a
CSV export (:func:`load_csv`) or from the Netlify API
(:func:`fetch_netlify_submissions`), become :class:`FormSubmission` records,
and :func:`import_submissions` turns them into leads. A submission from a
company already in the pipeline is merged without touching researched facts,
and importing the same submission twice changes nothing.

Four sites (bakery, pet, formulation, pet-formulation) post the same form
name with a hidden ``site`` field and optional fit questions (storage,
allergens, certifications, ...). Every answer that is not a core field is kept
in :attr:`FormSubmission.extras`, written into the lead note, and the fit
answers the facility cares about become tags (:func:`inbound_tags`).
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping
from urllib.parse import quote

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator

from leadgen.crm import LeadStore
from leadgen.models import Category, Lead, LeadSignals, Segment, Stage
from leadgen.triggers import classify_category

FORM_NAME = "capacity-check"
SOURCE = "inbound_website"
ACTIVITY_KIND = "inbound"
TAGS: tuple[str, ...] = ("inbound", "website")

# Host and basePath from the official spec: github.com/netlify/open-api, swagger.yml.
NETLIFY_API = "https://api.netlify.com/api/v1"
NETLIFY_TIMEOUT_SECONDS = 20.0
NETLIFY_PER_PAGE = 100
NETLIFY_MAX_PAGES = 50  # 5,000 submissions per form; a guard, not a limit this site will reach
NETLIFY_USER_AGENT = "cookie-plug-leadgen/0.1"

FREE_MAIL_DOMAINS: frozenset[str] = frozenset({
    "gmail.com", "googlemail.com", "yahoo.com", "ymail.com", "outlook.com", "hotmail.com",
    "live.com", "msn.com", "icloud.com", "me.com", "mac.com", "aol.com", "proton.me",
    "protonmail.com", "pm.me", "gmx.com", "zoho.com", "mail.com", "yandex.com", "comcast.net",
    "att.net", "verizon.net", "sbcglobal.net",
})
# Platforms, not brands: a link to one of these is never the brand's own website.
NON_BRAND_HOSTS: frozenset[str] = frozenset({
    "facebook.com", "instagram.com", "linkedin.com", "twitter.com", "x.com", "tiktok.com",
    "youtube.com", "pinterest.com", "etsy.com", "amazon.com", "faire.com", "linktr.ee", "bit.ly",
})
_NOT_BRAND = FREE_MAIL_DOMAINS | NON_BRAND_HOSTS
# TLDs accepted even when typed in capitals; any other TLD must be lowercase, so "St.Louis" stays a name.
COMMON_TLDS: frozenset[str] = frozenset({"com", "net", "org", "co", "io", "us", "biz", "info", "shop", "store", "ca", "uk"})

SEGMENT_BY_SETUP: dict[str, Segment] = {
    "home or shared kitchen": Segment.EMERGING_BRAND,
    "not in production yet": Segment.EMERGING_BRAND,
    "our own facility": Segment.ESTABLISHED_BRAND,
    "a co-packer": Segment.ESTABLISHED_BRAND,
}
TRANSITIONING_SETUPS: frozenset[str] = frozenset({"home or shared kitchen", "our own facility", "a co-packer"})
# The formulation sites ask "stage" instead of "current_setup".
SEGMENT_BY_STAGE: dict[str, Segment] = {
    "idea or concept": Segment.EMERGING_BRAND,
    "selling from a home or shared kitchen": Segment.EMERGING_BRAND,
    "selling with a co-packer": Segment.ESTABLISHED_BRAND,
    "established brand adding products": Segment.ESTABLISHED_BRAND,
}
TRANSITIONING_STAGES: frozenset[str] = frozenset({
    "selling from a home or shared kitchen", "selling with a co-packer", "established brand adding products",
})

# Sites whose leads are pet products whatever the product text says, and the answers that mean food, not treats.
PET_SITES: frozenset[str] = frozenset({"pet", "pet-formulation"})
PET_FOOD_PRODUCTS: frozenset[str] = frozenset({"complete and balanced food", "toppers or mixers"})
FORMULATION_SITES: frozenset[str] = frozenset({"formulation", "pet-formulation"})
FORMULATION_RECIPE_STATUSES: frozenset[str] = frozenset({
    "kitchen recipe", "concept only", "want a private-label recipe", "product to match",
})
STORAGE_TAGS: dict[str, str] = {"refrigerated": "fit:refrigerated", "frozen": "fit:frozen"}
ALLERGEN_TAGS: dict[str, str] = {
    "peanuts": "fit:peanut", "peanut": "fit:peanut", "tree nuts": "fit:tree-nut", "tree nut": "fit:tree-nut",
}
NO_CERTIFICATION: frozenset[str] = frozenset({"none yet", "none"})

# Export and API column names that mean a model field once keys are normalized.
FIELD_ALIASES: dict[str, str] = {
    "created_at": "submitted_at", "date": "submitted_at", "_date": "submitted_at",
    "submitted": "submitted_at", "id": "submission_id",
}
# Keys that are never answers, so never extras: Netlify's own metadata about the request.
METADATA_KEYS: frozenset[str] = frozenset({
    "ip", "user_agent", "referrer", "site_url", "number", "form_id", "site_id", "updated_at",
    "g_recaptcha_response",
})
# Fit questions in the order the note lists them; any other extra follows in arrival order.
FIT_FIELDS: tuple[str, ...] = (
    "storage", "allergens", "certifications", "claims", "recipe_status", "sku_count", "pack_format",
    "target_price", "channels", "species", "pet_product", "formulation_goal", "after_formulation",
)
EXTRA_KEY_PATTERN = re.compile(r"[a-z0-9][a-z0-9_]{0,39}")
EXTRA_MAX_CHARS = 500  # a guard on one answer; the longest real one is a pack format or target price
# (label in the note, FormSubmission field); the first two are the activity summary.
NOTE_FIELDS: tuple[tuple[str, str], ...] = (
    ("product", "product"), ("volume", "volume"), ("timing", "timing"),
    ("setup", "current_setup"), ("stage", "stage"), ("phone", "phone"), ("notes", "notes"),
)

EMAIL_PATTERN = re.compile(r"[a-z0-9._%+'-]+@(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}")
_HOST = r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
_HOST_ONLY = re.compile(_HOST + r"[a-z]{2,24}")
# A URL or bare domain that is not part of an email address or a longer word.
_DOMAIN_TOKEN = re.compile(
    r"(?<![\w@.-])(?:https?://)?(?P<host>" + _HOST + r"(?P<tld>[a-z]{2,24}))(?![\w-])"
    r"(?::\d{1,5})?(?:[/?#][^\s,;|()<>\"']*)?",
    re.IGNORECASE,
)
_EMAIL_TOKEN = re.compile(r"[^\s,;|()<>]+@[^\s,;|()<>]+")


class FormSubmission(BaseModel):
    """One capacity-check submission, from a CSV export or the Netlify API."""

    model_config = ConfigDict(str_strip_whitespace=True)

    product: str = ""
    volume: str = ""
    timing: str = ""
    current_setup: str = ""
    name: str = ""
    company: str = ""
    email: str = ""
    phone: str = ""
    notes: str = ""
    stage: str = ""  # the formulation sites' "where are you now" question, in place of current_setup
    source_page: str = ""
    site: str = ""  # hidden field naming which of the sites sent it: bakery, pet, formulation, pet-formulation
    website: str = ""
    bot_field: str = ""  # the honeypot: people never see it, so any value means a bot
    form_name: str = ""
    submitted_at: datetime | None = None
    submission_id: str = ""
    extras: dict[str, str] = Field(default_factory=dict)  # every other answer; checkbox lists comma-joined

    def __repr__(self) -> str:
        return (
            f"FormSubmission(id={self.submission_id!r}, email={self.email!r}, company={self.company!r}, "
            f"site={self.site!r}, extras={len(self.extras)})"
        )

    @field_validator("submitted_at", mode="before")
    @classmethod
    def _utc_timestamp(cls, value: object) -> datetime | None:
        """Parse ISO 8601 into an aware UTC datetime; blanks and junk become None."""
        return parse_timestamp(value)

    @classmethod
    def from_mapping(cls, row: Mapping[Any, Any]) -> FormSubmission:
        """Build from a dict whose keys vary in case, spacing, hyphens, underscores, and a ``[]`` suffix.

        Keys that name a field fill it; when two normalize to the same field,
        the first non-empty value wins. Every other answer goes to ``extras``
        under :func:`extra_key`, with repeated keys' values merged. List values
        (checkbox groups from the API) are joined with ", ". Netlify metadata,
        timestamps, ids, and non-string keys never become extras.
        """
        values: dict[str, str] = {}
        extras: dict[str, list[str]] = {}
        for raw_key, raw_value in row.items():
            items = value_items(raw_value)
            field = normalize_key(raw_key)
            if field:
                if items and not values.get(field):
                    values[field] = ", ".join(items)
                continue
            key = extra_key(raw_key)
            if key and items:
                bucket = extras.setdefault(key, [])
                bucket.extend(item for item in items if item not in bucket)
        joined = {key: ", ".join(items)[:EXTRA_MAX_CHARS] for key, items in extras.items()}
        return cls(**values, extras=joined)


class ImportedLead(BaseModel):
    """A submission that reached the pipeline, as a new lead or merged into a known one."""

    lead: Lead
    status: Literal["new", "merged"]
    email: str  # the submitter, who may not be the lead's main contact after a merge
    summary: str

    def __repr__(self) -> str:
        return f"ImportedLead(company={self.lead.company!r}, status={self.status})"


class InboundImport(BaseModel):
    """Outcome of an import: submissions that reached the pipeline, and the ones skipped with why."""

    imported: list[ImportedLead] = Field(default_factory=list)
    skipped: list[tuple[str, str]] = Field(default_factory=list)

    @property
    def new_count(self) -> int:
        """Submissions that created a lead."""
        return sum(1 for item in self.imported if item.status == "new")

    @property
    def merged_count(self) -> int:
        """Submissions folded into a lead already in the pipeline."""
        return sum(1 for item in self.imported if item.status == "merged")

    def __repr__(self) -> str:
        return f"InboundImport(new={self.new_count}, merged={self.merged_count}, skipped={len(self.skipped)})"


class NetlifyError(RuntimeError):
    """A Netlify API call failed. The message names the status and path, never the token."""

    def __repr__(self) -> str:
        return f"NetlifyError({str(self)!r})"


class SitePull(BaseModel):
    """What one Netlify site gave: its submissions, or the error that stopped the pull."""

    site_id: str
    submissions: list[FormSubmission] = Field(default_factory=list)
    error: str = ""

    @property
    def ok(self) -> bool:
        """True when the pull finished without an error."""
        return not self.error

    def __repr__(self) -> str:
        return f"SitePull(site_id={self.site_id!r}, submissions={len(self.submissions)}, ok={self.ok})"


def _base_key(key: object) -> str:
    """Lowercase, trimmed, without a checkbox ``[]`` suffix, with spaces and hyphens as underscores."""
    if not isinstance(key, str):
        return ""
    return re.sub(r"[\s-]+", "_", key.strip().lower().removesuffix("[]").strip())


def normalize_key(key: object) -> str:
    """The model field an export or API column name means, or empty when it is not one of ours."""
    normalized = _base_key(key)
    field = FIELD_ALIASES.get(normalized, normalized)
    return field if field in FormSubmission.model_fields and field != "extras" else ""


def extra_key(key: object) -> str:
    """The ``extras`` key for an answer that is not a core field; empty for metadata and odd keys.

    ``allergens[]`` gives ``allergens``. Timestamps, ids, Netlify's request
    metadata, and keys that are not short ``[a-z0-9_]`` names are dropped.
    """
    normalized = _base_key(key)
    if normalized in FIELD_ALIASES or normalized in METADATA_KEYS or normalize_key(normalized):
        return ""
    return normalized if EXTRA_KEY_PATTERN.fullmatch(normalized) else ""


def value_items(value: object) -> list[str]:
    """The non-empty, trimmed answers in a value: one for text, each element for a list."""
    if value is None:
        return []
    raw = value if isinstance(value, (list, tuple, set, frozenset)) else [value]
    items = (str(item).strip() for item in raw if item is not None)
    return [item for item in items if item]


def parse_timestamp(value: object) -> datetime | None:
    """ISO 8601 text, a date, or a datetime as an aware UTC datetime; None when blank or unreadable.

    Naive values, and text ending in ``UTC`` or ``GMT``, are taken as UTC.
    """
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time.min)
    else:
        text = re.sub(r"\s*(?:UTC|GMT)$", "", str(value or "").strip(), flags=re.IGNORECASE)
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def email_problem(email: str) -> str:
    """Why an address cannot be used ("missing email" or "invalid email"), or empty when it can."""
    cleaned = email.strip().lower()
    if not cleaned:
        return "missing email"
    return "" if EMAIL_PATTERN.fullmatch(cleaned) else "invalid email"


def parse_company_field(text: str, email: str = "", website: str = "") -> tuple[str, str]:
    """Split the form's "Brand name, brand.com" answer into (company, website).

    The website is the first URL or bare domain in ``website`` (a separate
    column, when an export has one) or in ``text``, else the domain of
    ``email`` unless it is a free-mail provider. Social and marketplace links
    never count. It is normalized to ``https://<host>`` with the host lowercased
    and ``www.`` dropped, which is the same key :attr:`Lead.domain` derives.
    The company is ``text`` with every domain token and stray separator
    removed, falling back to the domain's first label, title-cased. Both are
    empty when nothing identifies the company.
    """
    name, text_host = _split_company_text(text)
    host = _split_company_text(website)[1] or text_host or _email_host(email)
    return (name or _company_from_host(host), f"https://{host}" if host else "")


def _split_company_text(text: str) -> tuple[str, str]:
    """Cut URL and domain tokens out of ``text``; return (the name left over, the first brand host)."""
    hosts: list[str] = []

    def _cut(match: re.Match[str]) -> str:
        """Replace a real domain token with a space and remember its host."""
        tld = match.group("tld")
        if not (tld.islower() or tld.lower() in COMMON_TLDS):
            return match.group(0)  # "St.Louis" is part of a name, not a domain
        hosts.append(match.group("host").lower().removeprefix("www."))
        return " "

    remainder = _DOMAIN_TOKEN.sub(_cut, _EMAIL_TOKEN.sub(" ", text))  # an address is never part of a name
    brand_hosts = [host for host in hosts if not _is_non_brand(host)]
    return _clean_name(remainder), (brand_hosts[0] if brand_hosts else "")


def _clean_name(text: str) -> str:
    """Tidy what is left once domains are cut: empty brackets, doubled separators, stray ends."""
    cleaned = re.sub(r"\(\s*\)|\[\s*\]", " ", text)
    cleaned = re.sub(r"\s*([,;|/])(?:\s*[,;|/])+", r"\1", cleaned)
    return " ".join(cleaned.split()).strip(" ,;|/:-–—·.")


def _is_non_brand(host: str) -> bool:
    """True for free-mail and platform hosts, which never identify the brand's own site."""
    return any(host == domain or host.endswith(f".{domain}") for domain in _NOT_BRAND)


def _email_host(email: str) -> str:
    """The business domain of an address; empty for free-mail providers and malformed input."""
    local, _, host = email.strip().lower().rpartition("@")
    host = host.removeprefix("www.")
    if not local or not _HOST_ONLY.fullmatch(host) or _is_non_brand(host):
        return ""
    return host


def _company_from_host(host: str) -> str:
    """The first label of a domain, title-cased: ``crumbco.com`` gives ``Crumbco``."""
    return host.split(".")[0].title() if host else ""


def _one_line(text: str) -> str:
    """Collapse newlines and runs of whitespace so free text fits on one line."""
    return " ".join(text.split())


def _joined(sub: FormSubmission, fields: tuple[tuple[str, str], ...]) -> str:
    """``label=value`` pairs joined with "; ", leaving out empty values."""
    return "; ".join(
        f"{label}={_one_line(getattr(sub, attr))}" for label, attr in fields if getattr(sub, attr)
    )


def inbound_note(sub: FormSubmission) -> str:
    """The one-line entry for ``lead.notes``; empty parts are left out and the honeypot never appears."""
    head = "Inbound capacity check"
    if sub.submitted_at is not None:
        head += f" {sub.submitted_at.date().isoformat()}"
    if sub.source_page:
        head += f" from {_one_line(sub.source_page)}"
    details = "; ".join(part for part in (_joined(sub, NOTE_FIELDS), _extras_note(sub)) if part)
    return f"{head}: {details}" if details else head


def _extras_note(sub: FormSubmission) -> str:
    """``site=...`` then every non-empty extra as ``label=value``, fit questions first in form order."""
    parts = [f"site={_one_line(sub.site)}"] if sub.site else []
    rank = {key: index for index, key in enumerate(FIT_FIELDS)}
    ordered = sorted(sub.extras.items(), key=lambda item: rank.get(item[0], len(rank)))  # stable: others keep arrival order
    parts.extend(f"{key}={_one_line(value)}" for key, value in ordered if value.strip())
    return "; ".join(parts)


def inbound_summary(sub: FormSubmission) -> str:
    """Product and volume, the two answers that size the opportunity."""
    return _joined(sub, NOTE_FIELDS[:2]) or "no product or volume given"


def submission_key(sub: FormSubmission) -> str:
    """Content identity for re-import checks: email, product, and submitted_at to the second."""
    when = sub.submitted_at.replace(microsecond=0).isoformat() if sub.submitted_at else ""
    raw = "|".join((sub.email.lower(), _one_line(sub.product).lower(), when))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def submission_markers(sub: FormSubmission) -> set[str]:
    """What makes a later import of this submission a repeat: its id and its content key."""
    markers = {f"key:{submission_key(sub)}"}
    if sub.submission_id:
        markers.add(f"id:{sub.submission_id}")
    return markers


def site_slug(site: str) -> str:
    """The site answer as a tag-safe id: lowercase letters, digits, and dashes (``pet-formulation``)."""
    return re.sub(r"[^a-z0-9]+", "-", site.lower()).strip("-")[:40]


def inbound_source(sub: FormSubmission) -> str:
    """``inbound_<site>`` with dashes as underscores (``inbound_pet_formulation``); ``inbound_website`` without a site."""
    site = site_slug(sub.site)
    return f"inbound_{site.replace('-', '_')}" if site else SOURCE


def _answers(text: str) -> list[str]:
    """A comma-joined checkbox answer as its trimmed, non-empty choices."""
    return [part.strip() for part in text.split(",") if part.strip()]


def needs_formulation(sub: FormSubmission) -> bool:
    """True when the brand has no production-ready formula yet, or asked through a formulation site."""
    status = _one_line(sub.extras.get("recipe_status", "")).lower()
    return status in FORMULATION_RECIPE_STATUSES or site_slug(sub.site) in FORMULATION_SITES


def inbound_tags(sub: FormSubmission) -> list[str]:
    """``inbound`` and ``website``, then the site and the fit answers the facility has to plan for.

    ``site:<id>``; ``fit:refrigerated`` / ``fit:frozen`` from storage;
    ``fit:peanut`` / ``fit:tree-nut`` from allergens; ``need-cert:<slug>`` per
    certification wanted; ``need:formulation``; ``formulation-only`` when the
    brand does not want production after formulation.
    """
    extras = sub.extras
    site = site_slug(sub.site)
    tags = list(TAGS) + ([f"site:{site}"] if site else [])
    storage = _one_line(extras.get("storage", "")).lower()
    if storage in STORAGE_TAGS:
        tags.append(STORAGE_TAGS[storage])
    allergens = {answer.lower() for answer in _answers(extras.get("allergens", ""))}
    tags.extend(tag for name, tag in ALLERGEN_TAGS.items() if name in allergens)
    for cert in _answers(extras.get("certifications", "")):
        slug = site_slug(cert)
        if slug and cert.lower() not in NO_CERTIFICATION:
            tags.append(f"need-cert:{slug}")
    if needs_formulation(sub):
        tags.append("need:formulation")
    if re.match(r"no\b", extras.get("after_formulation", "").strip().lower()):
        tags.append("formulation-only")
    return list(dict.fromkeys(tags))


def inbound_category(sub: FormSubmission) -> Category:
    """On the pet sites, food or treat from the pet_product answer; elsewhere read product and notes."""
    if site_slug(sub.site) in PET_SITES:
        product = _one_line(sub.extras.get("pet_product", "")).lower()
        return Category.PET_FOOD if product in PET_FOOD_PRODUCTS else Category.PET_TREAT
    return classify_category(f"{sub.product} {sub.notes}")


def inbound_segment(sub: FormSubmission) -> tuple[Segment, bool]:
    """(segment, transitioning) from the current_setup answer, else from the formulation sites' stage."""
    setup = _one_line(sub.current_setup).lower()
    stage = _one_line(sub.stage).lower()
    segment = SEGMENT_BY_SETUP.get(setup) or SEGMENT_BY_STAGE.get(stage, Segment.UNKNOWN)
    return segment, setup in TRANSITIONING_SETUPS or stage in TRANSITIONING_STAGES


def submission_to_lead(sub: FormSubmission) -> Lead:
    """A new pipeline lead from one submission.

    Raises ValueError("missing company") when neither the company answer, a
    website, nor a business email names the company.
    """
    company, website = parse_company_field(sub.company, sub.email, sub.website)
    if not company:
        raise ValueError("missing company")
    category = inbound_category(sub)
    segment, transitioning = inbound_segment(sub)
    return Lead(
        company=company, website=website, category=category, segment=segment,
        contact_name=sub.name, email=sub.email, source=inbound_source(sub), stage=Stage.NEW,
        notes=inbound_note(sub), tags=inbound_tags(sub),
        signals=LeadSignals(
            seeking_copacker=True,
            transitioning=transitioning,
            detected_categories=[] if category == Category.OTHER else [category],
        ),
    )


def skip_reason(sub: FormSubmission, seen: set[str] | None = None) -> str:
    """Why a submission must not become a lead, or empty when it can.

    ``seen`` holds :func:`submission_markers` of submissions already imported.
    """
    if sub.bot_field:
        return "spam (honeypot)"
    if sub.form_name and sub.form_name.lower() != FORM_NAME:
        return f"different form ({sub.form_name})"
    problem = email_problem(sub.email)
    if problem:
        return problem
    if seen and submission_markers(sub) & seen:
        return "already imported"
    return ""


def import_submissions(store: LeadStore, submissions: Iterable[FormSubmission]) -> InboundImport:
    """Add submissions to the pipeline: new companies upserted, known ones merged, repeats skipped.

    Each imported submission logs an ``inbound`` activity whose JSON detail
    carries its id and content key, so importing it again changes nothing.
    """
    result = InboundImport()
    seen = _imported_markers(store)
    for sub in submissions:
        reason = skip_reason(sub, seen)
        lead: Lead | None = None
        if not reason:
            try:
                lead = submission_to_lead(sub)
            except ValueError as exc:
                reason = str(exc).split("\n")[0]
        if lead is None:
            result.skipped.append((_label(sub), reason))
            continue
        result.imported.append(_store_submission(store, sub, lead))
        seen.update(submission_markers(sub))
    return result


def _label(sub: FormSubmission) -> str:
    """How a skipped submission is named in output: its id, else its email, else a name."""
    return sub.submission_id or sub.email or sub.name or sub.company or "unnamed submission"


def _store_submission(store: LeadStore, sub: FormSubmission, incoming: Lead) -> ImportedLead:
    """Upsert a new lead or merge into the known one, then log the inbound activity."""
    existing = _find_existing(store, incoming)
    if existing is not None:
        _merge_inbound(existing, incoming)
    lead = incoming if existing is None else existing
    store.upsert(lead)
    store.log_activity(lead.domain or lead.company.lower(), ACTIVITY_KIND, _activity_detail(sub))
    return ImportedLead(
        lead=lead, status="new" if existing is None else "merged",
        email=sub.email.lower(), summary=inbound_summary(sub),
    )


def _find_existing(store: LeadStore, lead: Lead) -> Lead | None:
    """The pipeline lead stored under the same domain, else under the same company name."""
    if lead.domain:
        found = store.get(lead.domain)
        if found is not None:
            return found
    return store.get(lead.company.lower())


def _merge_inbound(existing: Lead, incoming: Lead) -> None:
    """Fold an inbound lead into a known one without overwriting researched facts.

    Follows ``discover._merge_into``: an empty contact name or email, an OTHER
    category, and an UNKNOWN segment are filled; notes and source are
    appended; true signals are unioned. The website is never changed, so the
    lead keeps its store key.
    """
    for field in ("contact_name", "email"):
        if not getattr(existing, field):
            setattr(existing, field, getattr(incoming, field))
    if existing.category == Category.OTHER:
        existing.category = incoming.category
    if existing.segment == Segment.UNKNOWN:
        existing.segment = incoming.segment
    if incoming.notes not in existing.notes:
        existing.notes = f"{existing.notes} || {incoming.notes}".strip(" |")
    if incoming.source not in existing.source.split("+"):
        existing.source = f"{existing.source}+{incoming.source}".strip("+")
    for tag in incoming.tags:
        existing.add_tag(tag)
    existing.signals = existing.signals.model_copy(update={
        "seeking_copacker": True,
        "transitioning": existing.signals.transitioning or incoming.signals.transitioning,
    })


def _activity_detail(sub: FormSubmission) -> str:
    """JSON for the inbound activity: the summary first, then who asked and the dedupe keys."""
    return json.dumps(
        {
            "summary": inbound_summary(sub), "name": sub.name, "email": sub.email.lower(),
            "submission_id": sub.submission_id, "key": submission_key(sub), "site": site_slug(sub.site),
        },
        ensure_ascii=False,
    )


def parse_activity_detail(detail: str) -> dict[str, str]:
    """Fields of an inbound activity's JSON detail; empty when the detail is not JSON."""
    try:
        record = json.loads(detail)
    except ValueError:
        return {}
    return {str(k): str(v) for k, v in record.items()} if isinstance(record, dict) else {}


def _imported_markers(store: LeadStore) -> set[str]:
    """Markers of every submission already logged as an inbound activity, on any lead."""
    markers: set[str] = set()
    for activity in store.activities_by_kind(ACTIVITY_KIND):
        record = parse_activity_detail(activity["detail"])
        if record.get("key"):
            markers.add(f"key:{record['key']}")
        if record.get("submission_id"):
            markers.add(f"id:{record['submission_id']}")
    return markers


def load_csv(path: str | Path) -> list[FormSubmission]:
    """Read a CSV export of the form; a UTF-8 byte-order mark is tolerated."""
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return [FormSubmission.from_mapping(row) for row in csv.DictReader(handle)]


def filter_since(submissions: Iterable[FormSubmission], since: date | datetime | None) -> list[FormSubmission]:
    """Submissions made on or after ``since``; a date means from the start of that day, UTC.

    Undated submissions are kept: dropping one could lose a lead, and a repeat is skipped on import.
    """
    cutoff = parse_timestamp(since) if since is not None else None
    return [s for s in submissions if cutoff is None or s.submitted_at is None or s.submitted_at >= cutoff]


def fetch_netlify_submissions(
    site_id: str,
    token: str,
    form_name: str = FORM_NAME,
    since: date | datetime | None = None,
    client: httpx.Client | None = None,
) -> list[FormSubmission]:
    """Submissions of one form from the Netlify API, optionally only those made since a day.

    Uses only what the official OpenAPI spec (netlify/open-api, swagger.yml)
    documents: ``GET /sites/{site_id}/forms`` (listSiteForms) to find the form
    by ``name``, then ``GET /forms/{form_id}/submissions`` (listFormSubmissions)
    with its ``page`` and ``per_page`` query parameters, read until a page comes
    back empty or repeats. The spec documents no date filter and no sort order,
    so ``since`` is applied here to each submission's ``created_at``. The token
    is sent as an OAuth2 bearer token; a Netlify personal access token works.
    Raises :class:`NetlifyError` on any failed call.
    """
    http = client if client is not None else _netlify_client()
    try:
        forms = _netlify_get(http, token, f"/sites/{quote(site_id, safe='')}/forms")
        form_ids = [str(f["id"]) for f in forms if isinstance(f, dict) and f.get("name") == form_name and f.get("id")]
        if not form_ids:
            names = sorted(str(f.get("name")) for f in forms if isinstance(f, dict))
            raise _netlify_error(f"no form named {form_name!r} on this site (found: {', '.join(names) or 'none'})", token)
        found = [sub for form_id in form_ids for sub in _form_submissions(http, token, form_id)]
    finally:
        if client is None:
            http.close()
    return filter_since(found, since)


def parse_site_ids(value: str) -> list[str]:
    """Netlify site IDs from ``NETLIFY_SITE_ID``: comma-separated, one per domain, blanks and repeats dropped."""
    return list(dict.fromkeys(part.strip() for part in value.split(",") if part.strip()))


def fetch_netlify_sites(
    site_ids: Iterable[str],
    token: str,
    form_name: str = FORM_NAME,
    since: date | datetime | None = None,
    client: httpx.Client | None = None,
) -> list[SitePull]:
    """Pull the form from each site in turn; a site that fails records its error and the rest still run."""
    pulls: list[SitePull] = []
    for site_id in site_ids:
        try:
            found = fetch_netlify_submissions(site_id, token, form_name=form_name, since=since, client=client)
        except NetlifyError as exc:
            pulls.append(SitePull(site_id=site_id, error=str(exc)))
            continue
        pulls.append(SitePull(site_id=site_id, submissions=found))
    return pulls


def _netlify_client() -> httpx.Client:
    """An HTTP client with a timeout; TLS verification stays on, as httpx does by default."""
    return httpx.Client(timeout=NETLIFY_TIMEOUT_SECONDS)


def _form_submissions(http: httpx.Client, token: str, form_id: str) -> list[FormSubmission]:
    """Every submission of one form, page by page, stopping at an empty or repeated page."""
    path = f"/forms/{quote(form_id, safe='')}/submissions"
    found: list[FormSubmission] = []
    seen: set[str] = set()
    for page in range(1, NETLIFY_MAX_PAGES + 1):
        records = _netlify_get(http, token, path, {"page": page, "per_page": NETLIFY_PER_PAGE})
        fresh = [r for r in records if isinstance(r, dict) and (not r.get("id") or str(r["id"]) not in seen)]
        if not fresh:
            break
        seen.update(str(r["id"]) for r in fresh if r.get("id"))
        found.extend(_submission_from_record(r) for r in fresh)
    return found


def _submission_from_record(record: dict[str, Any]) -> FormSubmission:
    """Map one API submission: its ``data`` fields plus the top-level ``id`` and ``created_at``."""
    data = record.get("data")
    values: dict[Any, Any] = dict(data) if isinstance(data, dict) else {}
    values.update(id=record.get("id"), created_at=record.get("created_at"))
    return FormSubmission.from_mapping(values)


def _netlify_get(http: httpx.Client, token: str, path: str, params: dict[str, int] | None = None) -> list[Any]:
    """GET one API path with bearer auth and return its JSON array; NetlifyError on any failure."""
    headers = {"Authorization": f"Bearer {token}", "User-Agent": NETLIFY_USER_AGENT, "Accept": "application/json"}
    try:
        response = http.get(f"{NETLIFY_API}{path}", params=params, headers=headers)
    except httpx.HTTPError as exc:
        raise _netlify_error(f"could not reach the Netlify API ({type(exc).__name__}) for GET {path}", token) from None
    if not response.is_success:
        raise _netlify_error(f"Netlify API returned {response.status_code} {response.reason_phrase} for GET {path}", token)
    try:
        data = response.json()
    except ValueError:
        data = None
    if not isinstance(data, list):
        raise _netlify_error(f"Netlify API returned an unexpected body for GET {path}", token)
    return data


def _netlify_error(message: str, token: str) -> NetlifyError:
    """A NetlifyError whose message can never carry the token, even if it leaked into a path."""
    return NetlifyError(message.replace(token, "***") if token else message)
