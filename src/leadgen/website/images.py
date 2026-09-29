"""Share images and icons, drawn with Pillow from the site's own fonts.

Run ``python site/build.py --images`` after adding a guide or changing the
brand. Output is committed under ``site/static/``, so the site build itself
never needs Pillow. Every image is drawn from confirmed facts only.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image, ImageDraw, ImageFont

    from leadgen.website.render import SiteContext

SIZE = (1200, 630)
INK = (12, 14, 15)
BG = (236, 239, 240)
WHITE = (255, 255, 255)
GREEN = (10, 122, 60)
BRIGHT = (43, 212, 111)
MUTED = (163, 173, 178)
KICKER = "CONTRACT MANUFACTURING  ·  PRIVATE LABEL  ·  FORMULATION"


class Fonts:
    """The three faces used on the site, at any size and weight."""

    def __init__(self, font_dir: Path) -> None:
        self.font_dir = font_dir

    def __repr__(self) -> str:
        return f"Fonts(font_dir={str(self.font_dir)!r})"

    def display(self, size: int, weight: int = 860, width: int = 72) -> "ImageFont.FreeTypeFont":
        """Archivo at a weight (500 to 900) and width (62 to 100)."""
        from PIL import ImageFont

        font = ImageFont.truetype(str(self.font_dir / "archivo-var.woff2"), size)
        font.set_variation_by_axes([weight, width])
        return font

    def mono(self, size: int) -> "ImageFont.FreeTypeFont":
        """IBM Plex Mono Medium."""
        from PIL import ImageFont

        return ImageFont.truetype(str(self.font_dir / "ibm-plex-mono-500.woff2"), size)


def wrap(text: str, font: "ImageFont.FreeTypeFont", width: int) -> list[str]:
    """Greedy word wrap by measured pixel width."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if font.getlength(trial) <= width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    return lines + ([current] if current else [])


def balanced(text: str, font: "ImageFont.FreeTypeFont", width: int) -> list[str]:
    """Wrap, then narrow the box a little if that avoids a one-word last line."""
    lines = wrap(text, font, width)
    for narrower in range(width, int(width * 0.78), -10):
        if len(lines) < 2 or len(lines[-1].split()) > 1:
            break
        trial = wrap(text, font, narrower)
        if len(trial) == len(lines):
            lines = trial
    return lines


def fit_title(fonts: Fonts, text: str, width: int, max_lines: int = 4) -> tuple["ImageFont.FreeTypeFont", list[str]]:
    """The largest title size (from 84px down) that fits in the box."""
    for size in range(84, 38, -4):
        font = fonts.display(size)
        lines = balanced(text, font, width)
        if len(lines) <= max_lines:
            return font, lines
    font = fonts.display(40)
    return font, wrap(text, font, width)[:max_lines]


def draw_mark(draw: "ImageDraw.ImageDraw", x: int, y: int, size: int, inverted: bool = False) -> None:
    """The brand mark: a square, an open line, and a green status light."""
    unit = size / 34
    draw.rounded_rectangle([x, y, x + size, y + size], radius=max(2, int(3 * unit)), fill=WHITE if inverted else INK)
    draw.rectangle([x + 6 * unit, y + 15 * unit, x + 21 * unit, y + 19 * unit], fill=INK if inverted else WHITE)
    draw.ellipse([x + 22 * unit, y + 13.5 * unit, x + 29 * unit, y + 20.5 * unit], fill=BRIGHT)


def draw_lockup(draw: "ImageDraw.ImageDraw", fonts: Fonts, site: "SiteContext", origin: tuple[int, int]) -> None:
    """Mark plus the two-line brand name."""
    x, y = origin
    draw_mark(draw, x, y, 58)
    draw.text((x + 76, y - 4), site.cfg.short_name.upper(), font=fonts.display(44, 880, 70), fill=INK)
    if site.brand_rest:
        draw.text((x + 78, y + 40), site.brand_rest.upper(), font=fonts.mono(17), fill=INK)


FACT_ROWS = 3


def facts_height(site: "SiteContext") -> int:
    """Pixel height of the facts panel for the confirmed lines."""
    return 102 + 40 * len(site.facts.lines) + 16 + 40 * FACT_ROWS + 14


def draw_facts(draw: "ImageDraw.ImageDraw", fonts: Fonts, site: "SiteContext", origin: tuple[int, int]) -> None:
    """A miniature Capacity Facts panel from the confirmed lines and services."""
    left, top = origin
    right = left + 380
    draw.rectangle([left, top, right, top + facts_height(site)], fill=WHITE, outline=INK, width=4)
    x, y, inner = left + 18, top + 12, right - 18
    draw.text((x, y), "Capacity Facts", font=fonts.display(50, 900, 64), fill=INK)
    y += 68
    draw.rectangle([x, y, inner, y + 12], fill=INK)
    y += 22
    row_font, bold = fonts.display(26, 600, 88), fonts.display(26, 800, 88)
    for line in site.facts.lines:
        draw.text((x, y), line.label, font=bold, fill=INK)
        status = "Open" if line.open else "Ask"
        width = row_font.getlength(status)
        draw.ellipse([inner - width - 22, y + 12, inner - width - 10, y + 24], fill=GREEN if line.open else MUTED)
        draw.text((inner - width, y), status, font=row_font, fill=GREEN if line.open else INK)
        y += 40
        draw.line([x, y - 5, inner, y - 5], fill=INK, width=2)
    draw.rectangle([x, y, inner, y + 6], fill=INK)
    y += 16
    rows = (("Waitlist", "None"), ("Turnkey services", str(len(site.facts.services))), ("Cost to ask", "$0"))
    for label, value in rows[:FACT_ROWS]:
        draw.text((x, y), label, font=bold, fill=INK)
        draw.text((inner - row_font.getlength(value), y), value, font=row_font, fill=INK)
        y += 40


def share_image(site: "SiteContext", fonts: Fonts, title: str, kicker: str) -> "Image.Image":
    """One 1200x630 Open Graph image."""
    from PIL import Image, ImageDraw

    image = Image.new("RGB", SIZE, BG)
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, SIZE[0], 56], fill=INK)
    draw.ellipse([60, 21, 74, 35], fill=BRIGHT)
    draw.text((88, 17), kicker, font=fonts.mono(19), fill=WHITE)
    font, lines = fit_title(fonts, title, 610)
    y = 104
    for line in lines:
        draw.text((60, y), line, font=font, fill=INK)
        y += int(font.size * 1.02)
    draw.line([60, 486, 690, 486], fill=INK, width=4)
    draw_lockup(draw, fonts, site, (60, 516))
    draw_facts(draw, fonts, site, (760, max(80, 343 - facts_height(site) // 2)))
    return image


def icon(size: int) -> "Image.Image":
    """Square app icon: the mark, full bleed."""
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (size, size), INK)
    draw = ImageDraw.Draw(image)
    unit = size / 34
    draw.rectangle([6 * unit, 15 * unit, 21 * unit, 19 * unit], fill=WHITE)
    draw.ellipse([22 * unit, 13.5 * unit, 29 * unit, 20.5 * unit], fill=BRIGHT)
    return image


def image_jobs(site: "SiteContext") -> list[tuple[str, str, str]]:
    """``(relative path, title, kicker)`` for every share image the site uses."""
    jobs = [("og/default.png", site.cfg.tagline, KICKER)]
    jobs += [(f"og/{slug}.png", spec["h1"], KICKER) for slug, spec in site.categories.items()]
    jobs += [(f"og/guides/{guide.slug}.png", guide.title, f"GUIDE  ·  {guide.reading_minutes} MIN READ") for guide in site.guides]
    return jobs


def generate_images(site: "SiteContext", static_dir: Path) -> list[Path]:
    """Write every share image plus the app icon and logo; return the paths written."""
    fonts = Fonts(static_dir / "fonts")
    written: list[Path] = []
    for relative, title, kicker in image_jobs(site):
        target = static_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        share_image(site, fonts, title, kicker).save(target, optimize=True)
        written.append(target)
    for name, size in (("apple-touch-icon.png", 180), ("logo.png", 512)):
        icon(size).save(static_dir / name, optimize=True)
        written.append(static_dir / name)
    return written
