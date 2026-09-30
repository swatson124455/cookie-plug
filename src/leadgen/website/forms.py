"""Per-site questionnaires: ``site/sites/<id>/form.yaml`` validated into what the form macro renders.

Each site asks its own audience its own questions, but every form posts to the
same Netlify form name with the same contact fields, so ``leadgen import-form``
reads all four sites. The template adds the contact fields, the notes box, the
honeypot, and the hidden ``source_page`` and ``site`` fields; ``form.yaml``
lists only the audience questions: the required core and an optional fit
section that opens on request.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from leadgen.website.content import ContentError, fill_tokens

FIELD_TYPES = ("text", "select", "radio", "checkboxes")
CHOICE_TYPES = ("select", "radio", "checkboxes")
RESERVED = ("name", "company", "email", "phone", "notes", "source_page", "site", "bot-field", "form-name")
FIELD_NAME = re.compile(r"[a-z][a-z_]*")
FORM_REQUIRED = ("title", "intro", "summary", "kicker", "submit", "steps", "fields")


def _field(raw: dict[str, Any], required_default: bool, source: str) -> dict[str, Any]:
    """One question, checked and filled with defaults."""
    name = str(raw.get("name", ""))
    kind = str(raw.get("type", "text"))
    if not FIELD_NAME.fullmatch(name) or name in RESERVED:
        raise ContentError(f"{source}: field name {name!r} must be lowercase letters and underscores, not {', '.join(RESERVED)}")
    if kind not in FIELD_TYPES:
        raise ContentError(f"{source}: field {name} type must be one of {', '.join(FIELD_TYPES)}")
    if not raw.get("label"):
        raise ContentError(f"{source}: field {name} needs a label")
    options = [str(option) for option in raw.get("options") or []]
    if kind in CHOICE_TYPES and len(options) < 2:
        raise ContentError(f"{source}: field {name} needs at least two options")
    return {"name": name, "type": kind, "label": str(raw["label"]), "options": options,
            "placeholder": str(raw.get("placeholder") or ""), "hint": str(raw.get("hint") or ""),
            "required": bool(raw.get("required", required_default)) and kind != "checkboxes",
            "wide": bool(raw.get("wide", kind in ("radio", "checkboxes")))}


def _fields(raw: list[dict[str, Any]], required_default: bool, source: str) -> list[dict[str, Any]]:
    """A list of questions with unique names."""
    fields = [_field(item, required_default, source) for item in raw or []]
    names = [item["name"] for item in fields]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ContentError(f"{source}: duplicate field names: {', '.join(duplicates)}")
    return fields


def load_form(path: Path, tokens: dict[str, str] | None = None) -> dict[str, Any]:
    """The site's questionnaire; the core must ask what the product is, and names are unique across sections."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    missing = [key for key in FORM_REQUIRED if not raw.get(key)]
    if missing:
        raise ContentError(f"{path}: missing {', '.join(missing)}")
    fields = _fields(raw["fields"], True, str(path))
    if "product" not in {item["name"] for item in fields}:
        raise ContentError(f"{path}: the core questions must include a field named product")
    fit = dict(raw.get("fit") or {})
    fit_fields = _fields(fit.get("fields") or [], False, str(path))
    clash = {item["name"] for item in fields} & {item["name"] for item in fit_fields}
    if clash:
        raise ContentError(f"{path}: fields asked twice: {', '.join(sorted(clash))}")
    steps = [fill_tokens(str(step), tokens) for step in raw["steps"]]
    return {key: fill_tokens(str(raw[key]), tokens) for key in ("title", "intro", "summary", "kicker", "submit")} | {
        "steps": steps, "fields": fields, "notes_placeholder": str(raw.get("notes_placeholder") or ""),
        "fit": {"title": str(fit.get("title") or "Help us check fit"), "intro": str(fit.get("intro") or ""),
                "fields": fit_fields}}


def field_names(form: dict[str, Any]) -> list[str]:
    """Every name the form posts, in order: questions, fit questions, then the template's own fields."""
    asked = [item["name"] for item in form["fields"] + form["fit"]["fields"]]
    return asked + ["name", "company", "email", "phone", "notes", "source_page", "site"]


def load_home(path: Path, tokens: dict[str, str] | None = None) -> dict[str, Any]:
    """The home page copy for a site: hero, who it is for, steps, and section headings."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    required = ("kicker", "h1", "lead", "trust", "who_title", "who_text", "who", "steps_title", "steps", "lines_title")
    missing = [key for key in required if not raw.get(key)]
    if missing:
        raise ContentError(f"{path}: missing {', '.join(missing)}")
    for key in ("who", "steps"):
        bad = [index + 1 for index, item in enumerate(raw[key]) if not item.get("title") or not item.get("text")]
        if bad:
            raise ContentError(f"{path}: {key} items {bad} need title and text")
    home = {key: fill_tokens(value, tokens) if isinstance(value, str) else value for key, value in raw.items()}
    home["steps"] = [{"title": str(step["title"]), "text": fill_tokens(str(step["text"]), tokens)} for step in raw["steps"]]
    return home
