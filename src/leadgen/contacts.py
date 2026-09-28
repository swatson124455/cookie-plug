"""Email address candidates for a named contact.

Small brands almost always use one of a handful of address patterns. Given a
name and a domain this module lists the likely addresses in order of how
often each pattern appears at companies under fifty people, so the manual
lookup starts with the best guess. Every candidate is UNVERIFIED until a
lookup tool or a non-bounce confirms it; the playbook says so and so does
the CLI output.
"""

from __future__ import annotations

import re
import unicodedata

from pydantic import BaseModel

from leadgen.models import Lead

GENERIC_INBOXES: tuple[str, ...] = ("hello", "info", "wholesale", "sales", "partnerships")

# Most common first, based on small-company conventions. A known pattern for
# the company (seen on a real address) overrides this order.
PATTERNS: tuple[str, ...] = ("first", "first.last", "firstlast", "flast", "first_last", "f.last", "last")


class EmailCandidate(BaseModel):
    """One possible address and why it was proposed."""

    address: str
    pattern: str
    verified: bool = False

    def __repr__(self) -> str:
        return f"EmailCandidate({self.address!r}, pattern={self.pattern})"


def _ascii_token(text: str) -> str:
    """Lowercase, strip accents and anything that is not a letter or digit."""
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", normalized.lower())


def name_parts(contact_name: str) -> tuple[str, str]:
    """Split a contact name into (first, last), dropping titles and suffixes."""
    stop = {"dr", "dr.", "mr", "mrs", "ms", "jd", "phd", "cpa", "rdn", "jr", "sr", "ii", "iii"}
    words = [w for w in re.split(r"[\s,]+", contact_name.strip()) if w and w.lower().strip(".") not in stop]
    if not words:
        return "", ""
    first = _ascii_token(words[0])
    last = _ascii_token(words[-1]) if len(words) > 1 else ""
    return first, last


def render_pattern(pattern: str, first: str, last: str) -> str | None:
    """Turn a pattern name into a local part, or None if the name lacks a piece."""
    initial = first[:1]
    forms = {
        "first": first,
        "first.last": f"{first}.{last}" if last else None,
        "firstlast": f"{first}{last}" if last else None,
        "flast": f"{initial}{last}" if last and initial else None,
        "first_last": f"{first}_{last}" if last else None,
        "f.last": f"{initial}.{last}" if last and initial else None,
        "last": last or None,
    }
    return forms.get(pattern)


def email_candidates(lead: Lead, known_pattern: str | None = None) -> list[EmailCandidate]:
    """Ranked address candidates for the lead's contact plus generic inboxes.

    ``known_pattern`` (for example "first.last") moves that pattern to the
    front when a real address at the company was seen.
    """
    if lead.email:
        return [EmailCandidate(address=lead.email, pattern="verified", verified=True)]
    domain = lead.domain
    if not domain:
        return []
    candidates: list[EmailCandidate] = []
    first, last = name_parts(lead.contact_name)
    order = ([known_pattern] if known_pattern else []) + [p for p in PATTERNS if p != known_pattern]
    if first:
        for pattern in order:
            local = render_pattern(pattern, first, last)
            if local:
                candidates.append(EmailCandidate(address=f"{local}@{domain}", pattern=pattern))
    candidates.extend(EmailCandidate(address=f"{inbox}@{domain}", pattern="generic") for inbox in GENERIC_INBOXES)
    return candidates
