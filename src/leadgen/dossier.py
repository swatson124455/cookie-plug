"""Automated account dossiers using Claude with the web search server tool.

This is the productized version of the research pass that built the spear
list: one call per lead, Claude searches the public web, and the result is
saved as Markdown under ``leads/dossiers/``. The pause_turn loop follows
the API's server-tool contract: when the server-side search loop pauses,
the same conversation is resent and it resumes.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import anthropic

from leadgen.ai import QualifierError
from leadgen.facility import FacilityProfile
from leadgen.models import Lead

DEFAULT_MODEL = "claude-opus-5"
DOSSIER_DIR = Path("leads/dossiers")
PROMPT_PATH = Path("prompts/dossier.md")
MAX_SEARCHES = 12
MAX_CONTINUATIONS = 4
MAX_TOKENS = 6000

WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": MAX_SEARCHES}


def dossier_path(lead: Lead, directory: Path = DOSSIER_DIR) -> Path:
    key = (lead.domain or lead.company.lower()).replace(".", "_").replace(" ", "_")
    return directory / f"{key}.md"


def _lead_brief(lead: Lead, facility: FacilityProfile) -> str:
    lines = [
        f"Company: {lead.company}",
        f"Website: {lead.website or 'unknown'}",
        f"Category: {lead.category.value}",
        f"Known contact: {lead.contact_name or 'unknown'} ({lead.contact_title or 'unknown'})",
        f"What we already know: {lead.notes or 'nothing'}",
        f"Facility lines: {', '.join(c.value for c in facility.categories)}",
        f"Today's date: {date.today().isoformat()}",
    ]
    return "\n".join(lines)


def build_dossier(lead: Lead, facility: FacilityProfile, client: anthropic.Anthropic, model: str = DEFAULT_MODEL) -> str:
    """Research one lead and return the dossier Markdown."""
    system = PROMPT_PATH.read_text(encoding="utf-8")
    messages: list[dict[str, object]] = [{"role": "user", "content": f"Research this company.\n\n{_lead_brief(lead, facility)}"}]
    response = _create(client, model, system, messages)
    continuations = 0
    while response.stop_reason == "pause_turn" and continuations < MAX_CONTINUATIONS:
        messages = messages[:1] + [{"role": "assistant", "content": response.content}]
        response = _create(client, model, system, messages)
        continuations += 1
    if response.stop_reason == "refusal":
        raise QualifierError("model declined to research this company")
    text = "\n".join(block.text for block in response.content if getattr(block, "type", "") == "text").strip()
    if not text:
        raise QualifierError("model returned no dossier text")
    return text


def _create(client: anthropic.Anthropic, model: str, system: str, messages: list[dict[str, object]]):  # type: ignore[no-untyped-def]
    try:
        return client.messages.create(
            model=model, max_tokens=MAX_TOKENS, system=system, messages=messages, tools=[WEB_SEARCH_TOOL],
        )
    except anthropic.AuthenticationError as exc:
        raise QualifierError("Anthropic API key is missing or invalid") from exc
    except anthropic.RateLimitError as exc:
        raise QualifierError("Anthropic rate limit hit; retry shortly") from exc
    except anthropic.APIStatusError as exc:
        raise QualifierError(f"Anthropic API error {exc.status_code}: {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise QualifierError("could not reach the Anthropic API") from exc


WEBSITE_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 2}
WEBSITE_PROMPT = (
    "Find the official website domain of the company below. Use web search. "
    "Reply with only the bare domain (for example brand.com) or the single word UNKNOWN. "
    "Never reply with a retailer, marketplace, social network, or news site."
)
_DOMAIN_RE = re.compile(r"^(?:https?://)?(?:www\.)?([a-z0-9-]+(?:\.[a-z0-9-]+)+)/?$", re.IGNORECASE)


def find_website(lead: Lead, client: anthropic.Anthropic, model: str = DEFAULT_MODEL) -> str:
    """Ask Claude, with two web searches, for the company's own domain; empty if unknown."""
    user = f"Company: {lead.company}\nCategory: {lead.category.value}\nContext: {lead.notes[:300] or 'none'}"
    messages: list[dict[str, object]] = [{"role": "user", "content": user}]
    try:
        response = client.messages.create(model=model, max_tokens=200, system=WEBSITE_PROMPT, messages=messages, tools=[WEBSITE_TOOL])
        if response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            response = client.messages.create(model=model, max_tokens=200, system=WEBSITE_PROMPT, messages=messages, tools=[WEBSITE_TOOL])
    except anthropic.APIStatusError as exc:
        raise QualifierError(f"Anthropic API error {exc.status_code}: {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise QualifierError("could not reach the Anthropic API") from exc
    text = " ".join(block.text for block in response.content if getattr(block, "type", "") == "text").strip()
    last_token = text.split()[-1].strip(".,;") if text else ""
    match = _DOMAIN_RE.match(last_token)
    return match.group(1).lower() if match and last_token.upper() != "UNKNOWN" else ""


def save_dossier(lead: Lead, text: str, directory: Path = DOSSIER_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = dossier_path(lead, directory)
    header = f"# {lead.company}\n\nGenerated {date.today().isoformat()} by `leadgen dossier`. Verify any fact before it goes into an email.\n\n"
    path.write_text(header + text + "\n", encoding="utf-8")
    return path
