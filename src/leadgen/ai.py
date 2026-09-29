"""Optional Claude layer: AI qualification and first-email drafting.

Every call goes through :class:`Qualifier`, which accepts an injected
``anthropic.Anthropic`` client so tests use a fake. When no API key is
configured, :func:`build_qualifier` returns :class:`RuleBasedQualifier`,
which produces the same output shape from enrichment signals alone, so the
rest of the pipeline never has to care which one it got.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

import anthropic
from pydantic import BaseModel, Field

from leadgen.prompting import UNTRUSTED_NOTICE, fenced
from leadgen.facility import FacilityProfile
from leadgen.models import AiAssessment, Lead
from leadgen.outreach import SenderIdentity, personal_line_from_signals

DEFAULT_MODEL = "claude-opus-5"
PROMPT_DIR = Path("prompts")
MAX_TOKENS_ASSESSMENT = 2048
MAX_TOKENS_EMAIL = 1024


class OutreachDraft(BaseModel):
    """AI-written first email."""

    subject: str
    body: str

    def __repr__(self) -> str:
        return f"OutreachDraft(subject={self.subject!r})"


class Qualifier(Protocol):
    """Anything that can assess a lead and draft its first email."""

    def assess(self, lead: Lead, facility: FacilityProfile) -> AiAssessment: ...

    def draft_email(self, lead: Lead, facility: FacilityProfile, sender: SenderIdentity) -> OutreachDraft: ...


class QualifierError(RuntimeError):
    """Raised when the AI call fails in a way the caller should see."""


def lead_facts(lead: Lead, facility: FacilityProfile) -> str:
    """Render the facts the model is allowed to reason from. Nothing else."""
    signals = lead.signals
    active = [name for name, value in signals.model_dump().items() if value is True]
    return "\n".join(
        [
            f"Company: {fenced(lead.company, 200)}",
            f"Website: {fenced(lead.website or 'unknown', 200)}",
            f"Category: {lead.category.value}",
            f"Segment: {lead.segment.value}",
            f"Contact: {fenced(lead.contact_name or 'unknown', 120)} ({fenced(lead.contact_title or 'unknown title', 120)})",
            f"Site title: {fenced(signals.site_title or 'n/a', 300)}",
            f"Site description: {fenced(signals.site_description or 'n/a', 600)}",
            f"Observed signals: {', '.join(active) or 'none'}",
            f"Retailers mentioned: {fenced(', '.join(signals.retailers_mentioned) or 'none', 300)}",
            f"Product count (Shopify): {signals.product_count if signals.product_count is not None else 'unknown'}",
            f"Rule-based score: {lead.score} ({'; '.join(lead.score_reasons) or 'no reasons'})",
            f"Notes: {fenced(lead.notes or 'none')}",
            f"Facility lines: {', '.join(c.value for c in facility.categories)}",
            f"Facility confirmed certifications: {', '.join(facility.confirmed_certifications()) or 'none confirmed'}",
            f"Facility spare capacity: {facility.spare_capacity_pct()}%",
        ]
    )


def _read_prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


class ClaudeQualifier:
    """Qualification and drafting backed by the Claude API."""

    def __init__(self, client: anthropic.Anthropic | None = None, model: str = DEFAULT_MODEL) -> None:
        self._client = client or anthropic.Anthropic()
        self._model = model

    def __repr__(self) -> str:
        return f"ClaudeQualifier(model={self._model!r})"

    def assess(self, lead: Lead, facility: FacilityProfile) -> AiAssessment:
        """Ask Claude for a structured fit assessment."""
        return self._parse(
            system=_read_prompt("qualify.md") + "\n\n" + UNTRUSTED_NOTICE,
            user=f"Assess this company.\n\n{lead_facts(lead, facility)}",
            schema=AiAssessment,
            max_tokens=MAX_TOKENS_ASSESSMENT,
        )

    def draft_email(self, lead: Lead, facility: FacilityProfile, sender: SenderIdentity) -> OutreachDraft:
        """Ask Claude for a first-touch email."""
        user = (
            f"Sender name: {sender.name}\nSender title: {sender.title}\n\n"
            f"Company facts:\n{lead_facts(lead, facility)}"
        )
        return self._parse(
            system=_read_prompt("draft_email.md") + "\n\n" + UNTRUSTED_NOTICE,
            user=user,
            schema=OutreachDraft,
            max_tokens=MAX_TOKENS_EMAIL,
        )

    def _parse(self, system: str, user: str, schema: type[BaseModel], max_tokens: int):  # type: ignore[no-untyped-def]
        """One structured-output call with a specific-first error chain."""
        try:
            response = self._client.messages.parse(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_format=schema,
            )
        except anthropic.AuthenticationError as exc:
            raise QualifierError("Anthropic API key is missing or invalid") from exc
        except anthropic.RateLimitError as exc:
            raise QualifierError("Anthropic rate limit hit; retry shortly") from exc
        except anthropic.APIStatusError as exc:
            raise QualifierError(f"Anthropic API error {exc.status_code}: {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise QualifierError("could not reach the Anthropic API") from exc
        if response.stop_reason == "refusal":
            raise QualifierError("model declined the request")
        if response.parsed_output is None:
            raise QualifierError("model returned no structured output")
        return response.parsed_output


class RuleBasedQualifier:
    """Zero-cost fallback that mirrors the AI output shape from signals."""

    def __repr__(self) -> str:
        return "RuleBasedQualifier()"

    def assess(self, lead: Lead, facility: FacilityProfile) -> AiAssessment:
        signals = lead.signals
        disqualifiers = []
        if not facility.supports(lead.category):
            disqualifiers.append(f"facility does not run a {lead.category.value} line")
        if signals.explicit_own_facility_only:
            disqualifiers.append("states it manufactures in its own facility")
        pain = "production capacity and lead time" if signals.in_national_retail or signals.out_of_stock else "scaling beyond the current setup"
        return AiAssessment(
            fit_score=lead.score,
            reasoning=f"Rule-based score {lead.score} from: {'; '.join(lead.score_reasons) or 'no signals'}.",
            likely_pain=pain,
            best_angle=f"Open capacity and fast sampling for a {lead.category.value.replace('_', ' ')} brand facing {pain}.",
            disqualifiers=disqualifiers,
            personal_line=personal_line_from_signals(lead),
        )

    def draft_email(self, lead: Lead, facility: FacilityProfile, sender: SenderIdentity) -> OutreachDraft:
        from leadgen.outreach import load_sequence, render_sequence

        first = render_sequence(lead, facility, sender, load_sequence())[0]
        return OutreachDraft(subject=first.subject, body=first.body)


def build_qualifier(model: str | None = None) -> Qualifier:
    """Pick the Claude qualifier when a key is configured, else the rule-based one."""
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return ClaudeQualifier(model=model or os.environ.get("LEADGEN_MODEL", DEFAULT_MODEL))
    return RuleBasedQualifier()
