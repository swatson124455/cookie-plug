"""Core data models shared by every module in the engine.

Leads flow through the pipeline as :class:`Lead` objects. Enrichment fills
:class:`LeadSignals`, scoring fills ``score`` and ``score_reasons``, and the
CRM persists the whole thing. Keeping one model avoids the "sometimes a dict,
sometimes an object" problem.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Category(str, Enum):
    """Product category of the lead, mapped to facility production lines."""

    COOKIE = "cookie"
    BAKERY = "bakery"
    PET_TREAT = "pet_treat"
    PET_FOOD = "pet_food"
    SNACK = "snack"
    OTHER = "other"


class Segment(str, Enum):
    """Who the lead is, which drives messaging and expected deal size."""

    EMERGING_BRAND = "emerging_brand"
    ESTABLISHED_BRAND = "established_brand"
    RETAILER_PRIVATE_LABEL = "retailer_private_label"
    NON_FOOD_BRAND_EXTENSION = "non_food_brand_extension"
    SUBSCRIPTION_BOX = "subscription_box"
    DISTRIBUTOR_OR_BROKER = "distributor_or_broker"
    UNKNOWN = "unknown"


class Stage(str, Enum):
    """Pipeline stage. Order matters: it is the funnel."""

    NEW = "new"
    ENRICHED = "enriched"
    QUALIFIED = "qualified"
    CONTACTED = "contacted"
    REPLIED = "replied"
    DISCOVERY_CALL = "discovery_call"
    SAMPLE_SENT = "sample_sent"
    HANDOFF = "handoff"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


STAGE_ORDER: tuple[Stage, ...] = tuple(Stage)


class LeadSignals(BaseModel):
    """Observable facts about a lead gathered from public sources.

    Every field defaults to "not observed" so a partially enriched lead is
    still valid. Booleans mean "we saw evidence", not "we confirmed absence".
    """

    is_shopify: bool = False
    sells_wholesale: bool = False
    in_national_retail: bool = False
    retailers_mentioned: list[str] = Field(default_factory=list)
    mentions_copacker: bool = False
    mentions_private_label: bool = False
    hiring_ops_or_production: bool = False
    out_of_stock: bool = False
    product_count: int | None = None
    recent_funding: bool = False
    recent_retail_launch: bool = False
    has_pet_and_human_lines: bool = False
    explicit_own_facility_only: bool = False
    detected_categories: list[Category] = Field(default_factory=list)
    site_title: str = ""
    site_description: str = ""

    def __repr__(self) -> str:
        active = [name for name, value in self.model_dump().items() if value]
        return f"LeadSignals(active={active})"


class Lead(BaseModel):
    """A single prospect company and its primary contact."""

    company: str
    website: str = ""
    category: Category = Category.OTHER
    segment: Segment = Segment.UNKNOWN
    contact_name: str = ""
    contact_title: str = ""
    email: str = ""
    linkedin_url: str = ""
    city: str = ""
    state: str = ""
    source: str = "manual"
    notes: str = ""
    signals: LeadSignals = Field(default_factory=LeadSignals)
    score: int = 0
    score_reasons: list[str] = Field(default_factory=list)
    stage: Stage = Stage.NEW
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("company")
    @classmethod
    def _company_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("company must not be blank")
        return cleaned

    @field_validator("website")
    @classmethod
    def _normalize_website(cls, value: str) -> str:
        """Ensure a scheme so httpx and dedupe logic behave consistently."""
        cleaned = value.strip().lower()
        if cleaned and not cleaned.startswith(("http://", "https://")):
            cleaned = f"https://{cleaned}"
        return cleaned.rstrip("/")

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned and ("@" not in cleaned or "." not in cleaned.split("@")[-1]):
            raise ValueError(f"invalid email: {value}")
        return cleaned

    @property
    def domain(self) -> str:
        """Bare domain used as the dedupe key (``example.com``)."""
        host = self.website.split("//")[-1].split("/")[0]
        return host.removeprefix("www.")

    @property
    def first_name(self) -> str:
        """First token of the contact name, or a neutral fallback."""
        return self.contact_name.split()[0] if self.contact_name.strip() else "there"

    def touch(self) -> None:
        """Bump ``updated_at``; call after any mutation before persisting."""
        self.updated_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return (
            f"Lead(company={self.company!r}, domain={self.domain!r}, "
            f"category={self.category.value}, score={self.score}, stage={self.stage.value})"
        )


class AiAssessment(BaseModel):
    """Structured output of the AI qualification step."""

    fit_score: int = Field(ge=0, le=100, description="0-100 fit with the facility ICP")
    reasoning: str = Field(description="Two or three sentences on why")
    likely_pain: str = Field(description="The most probable operational pain right now")
    best_angle: str = Field(description="The single strongest opening angle for outreach")
    disqualifiers: list[str] = Field(default_factory=list)
    personal_line: str = Field(description="One specific, non-flattering opening sentence")

    def __repr__(self) -> str:
        return f"AiAssessment(fit_score={self.fit_score}, angle={self.best_angle!r})"


class OutreachTouch(BaseModel):
    """One rendered message in a sequence."""

    day: int
    channel: str
    subject: str
    body: str

    def __repr__(self) -> str:
        return f"OutreachTouch(day={self.day}, channel={self.channel}, subject={self.subject!r})"
