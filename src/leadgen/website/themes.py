"""Site skins: each site in the family picks a theme in its ``site.yaml`` (``theme: open-book``).

A theme is a folder ``site/themes/<id>/`` with:

* ``theme.yaml``: its name, the Google Fonts URL the one-file preview uses,
  the font files to preload, and the share-image palette and fonts;
* ``fonts.css`` and ``fonts/``: self-hosted WOFF2 faces for the live site
  (``scripts/fetch_theme_fonts.py`` writes both);
* ``theme.css``: overrides appended after ``site/static/styles.css``.

Templates stay shared; a theme changes only fonts, colors, and component styling,
so every site keeps the same pages, links, forms, and structured data.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from leadgen.website.content import ContentError

HEX = re.compile(r"#[0-9a-fA-F]{6}")
THEME_ID = re.compile(r"[a-z0-9-]+")


def rgb(value: str) -> tuple[int, int, int]:
    """``#0c0e0f`` as an RGB tuple for Pillow."""
    return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)


class ShareStyle(BaseModel):
    """How a theme's share images look: fonts from its ``fonts/`` folder and six colors."""

    display: str
    label: str
    display_weight: int = 800
    display_width: int = 72
    bg: str = "#eceff0"
    ink: str = "#0c0e0f"
    panel: str = "#ffffff"
    signal: str = "#0a7a3c"
    bright: str = "#2bd46f"
    muted: str = "#a3adb2"
    radius: int = 0
    heavy_bars: bool = False

    @field_validator("bg", "ink", "panel", "signal", "bright", "muted")
    @classmethod
    def _hex(cls, value: str) -> str:
        """Colors are six-digit hex, so Pillow and CSS read them the same way."""
        if not HEX.fullmatch(value):
            raise ValueError(f"{value!r} is not a #rrggbb color")
        return value

    def color(self, name: str) -> tuple[int, int, int]:
        """A palette color as RGB."""
        return rgb(getattr(self, name))

    def __repr__(self) -> str:
        return f"ShareStyle(display={self.display!r}, bg={self.bg!r})"


class Theme(BaseModel):
    """A loaded theme and where its files live."""

    id: str
    name: str
    google_fonts: str
    preload: list[str] = Field(default_factory=list)
    share: ShareStyle
    folder: Path

    @property
    def font_dir(self) -> Path:
        """The theme's WOFF2 files."""
        return self.folder / "fonts"

    def css(self, with_fonts: bool) -> tuple[str, str]:
        """``(font-face rules, overrides)``; the font rules are empty for the preview, which uses Google Fonts."""
        fonts = (self.folder / "fonts.css").read_text(encoding="utf-8") if with_fonts else ""
        overrides = self.folder / "theme.css"
        return fonts, overrides.read_text(encoding="utf-8") if overrides.exists() else ""

    def __repr__(self) -> str:
        return f"Theme(id={self.id!r}, name={self.name!r})"


def load_theme(site_dir: Path, theme_id: str) -> Theme:
    """A theme by id, with every file it names checked, so a typo fails the build and not the page."""
    folder = site_dir / "themes" / theme_id
    if not THEME_ID.fullmatch(theme_id) or not (folder / "theme.yaml").exists():
        known = sorted(path.name for path in (site_dir / "themes").iterdir() if (path / "theme.yaml").exists())
        raise ContentError(f"unknown theme {theme_id!r}: choose one of {', '.join(known)}")
    raw: dict[str, Any] = yaml.safe_load((folder / "theme.yaml").read_text(encoding="utf-8")) or {}
    try:
        theme = Theme.model_validate(raw | {"id": theme_id, "folder": folder})
    except ValueError as exc:
        raise ContentError(f"{folder / 'theme.yaml'}: {exc}") from exc
    needed = [folder / "fonts.css"] + [theme.font_dir / name for name in
                                       theme.preload + [theme.share.display, theme.share.label]]
    missing = [str(path.relative_to(site_dir)) for path in needed if not path.exists()]
    if missing:
        raise ContentError(f"theme {theme_id}: missing {', '.join(missing)}")
    return theme
