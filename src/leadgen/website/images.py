"""Share images and icons, drawn with Pillow from each site's theme fonts and colors.

Run ``python site/build.py --images`` after adding a guide or changing a
brand or theme. Share images are committed under ``site/sites/<id>/static/og/``
and the shared icons under ``site/static/``, so the site build itself never
needs Pillow. Every image is drawn from confirmed facts only.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image, ImageDraw, ImageFont

    from leadgen.website.render import SiteContext
    from leadgen.website.themes import Theme

SIZE = (1200, 630)
ICON_INK = (12, 14, 15)
ICON_LINE = (255, 255, 255)
ICON_DOT = (43, 212, 111)
KICKER = "CONTRACT MANUFACTURING  ·  PRIVATE LABEL  ·  FORMULATION"
AXIS_NAMES = {"weight": (b"Weight", "Weight"), "width": (b"Width", "Width"), "size": (b"Optical size", "Optical size", b"Optical Size", "Optical Size")}


class Kit:
    """A theme's two faces (display and label) at any size and weight, and its share palette."""

    def __init__(self, theme: "Theme") -> None:
        self.font_dir = theme.font_dir
        self.style = theme.share

    def __repr__(self) -> str:
        return f"Kit(font_dir={str(self.font_dir)!r})"

    def color(self, name: str) -> tuple[int, int, int]:
        """A palette color as RGB."""
        return self.style.color(name)

    def display(self, size: int, weight: int | None = None, width: int | None = None) -> "ImageFont.FreeTypeFont":
        """The display face; weight and width apply when the font has those axes."""
        return self._face(self.style.display, size, weight or self.style.display_weight, width or self.style.display_width)

    def label(self, size: int, weight: int = 500) -> "ImageFont.FreeTypeFont":
        """The label face (mono or sans, per theme)."""
        return self._face(self.style.label, size, weight, 100)

    def _face(self, name: str, size: int, weight: int, width: int) -> "ImageFont.FreeTypeFont":
        """Load a face and set its variable axes by name, clamped to each axis's range."""
        from PIL import ImageFont

        font = ImageFont.truetype(str(self.font_dir / name), size)
        try:
            axes = font.get_variation_axes()
        except OSError:
            return font  # a static face: one weight, nothing to set
        wanted = {"weight": weight, "width": width, "size": size}
        values = []
        for axis in axes:
            value = axis["default"]
            for key, names in AXIS_NAMES.items():
                if axis["name"] in names:
                    value = max(axis["minimum"], min(axis["maximum"], wanted[key]))
            values.append(value)
        font.set_variation_by_axes(values)
        return font


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


def fit_title(kit: Kit, text: str, width: int, max_lines: int = 4) -> tuple["ImageFont.FreeTypeFont", list[str]]:
    """The largest title size (from 84px down) that fits in the box."""
    for size in range(84, 38, -4):
        font = kit.display(size)
        lines = balanced(text, font, width)
        if len(lines) <= max_lines:
            return font, lines
    font = kit.display(40)
    return font, wrap(text, font, width)[:max_lines]


def draw_mark(draw: "ImageDraw.ImageDraw", kit: Kit, origin: tuple[int, int], size: int) -> None:
    """The brand mark: a square, an open line, and a status light, in the theme's colors."""
    x, y = origin
    unit = size / 34
    draw.rounded_rectangle([x, y, x + size, y + size], radius=max(2, int(3 * unit)), fill=kit.color("ink"))
    draw.rectangle([x + 6 * unit, y + 15 * unit, x + 21 * unit, y + 19 * unit], fill=kit.color("panel"))
    draw.ellipse([x + 22 * unit, y + 13.5 * unit, x + 29 * unit, y + 20.5 * unit], fill=kit.color("bright"))


def draw_lockup(draw: "ImageDraw.ImageDraw", kit: Kit, site: "SiteContext", origin: tuple[int, int]) -> None:
    """Mark plus the two-line brand name."""
    x, y = origin
    draw_mark(draw, kit, (x, y), 58)
    draw.text((x + 76, y - 4), site.cfg.short_name.upper(), font=kit.display(44, 880, 70), fill=kit.color("ink"))
    if site.brand_rest:
        draw.text((x + 78, y + 40), site.brand_rest.upper(), font=kit.label(17), fill=kit.color("ink"))


FACT_ROWS = 3


def facts_height(site: "SiteContext") -> int:
    """Pixel height of the facts panel for the confirmed lines."""
    return 102 + 40 * len(site.facts.lines) + 16 + 40 * FACT_ROWS + 14


def _rule(draw: "ImageDraw.ImageDraw", kit: Kit, box: tuple[int, int, int], heavy: int) -> None:
    """A divider: a heavy bar in the spec-sheet look, a hairline otherwise."""
    x, y, right = box
    if kit.style.heavy_bars:
        draw.rectangle([x, y, right, y + heavy], fill=kit.color("ink"))
    else:
        draw.line([x, y + heavy // 2, right, y + heavy // 2], fill=kit.color("muted"), width=2)


def draw_facts(draw: "ImageDraw.ImageDraw", kit: Kit, site: "SiteContext", origin: tuple[int, int]) -> None:
    """A miniature Capacity Facts panel from the confirmed lines and services."""
    left, top = origin
    right, ink = left + 380, kit.color("ink")
    draw.rounded_rectangle([left, top, right, top + facts_height(site)], radius=kit.style.radius,
                           fill=kit.color("panel"), outline=ink, width=4 if kit.style.heavy_bars else 2)
    x, y, inner = left + 18, top + 12, right - 18
    draw.text((x, y), "Capacity Facts", font=kit.display(46, None, 64), fill=ink)
    y += 68
    _rule(draw, kit, (x, y, inner), 12)
    y += 22
    row_font, bold = kit.display(26, 500, 88), kit.display(26, 700, 88)
    for line in site.facts.lines:
        draw.text((x, y), line.label, font=bold, fill=ink)
        status, color = ("Open", kit.color("signal")) if line.open else ("Ask", ink)
        width = row_font.getlength(status)
        dot = kit.color("signal") if line.open else kit.color("muted")
        draw.ellipse([inner - width - 22, y + 12, inner - width - 10, y + 24], fill=dot)
        draw.text((inner - width, y), status, font=row_font, fill=color)
        y += 40
        draw.line([x, y - 5, inner, y - 5], fill=ink if kit.style.heavy_bars else kit.color("muted"), width=2)
    _rule(draw, kit, (x, y, inner), 6)
    y += 16
    rows = (("Waitlist", "None"), ("Turnkey services", str(len(site.facts.services))), ("Cost to ask", "$0"))
    for label, value in rows[:FACT_ROWS]:
        draw.text((x, y), label, font=bold, fill=ink)
        draw.text((inner - row_font.getlength(value), y), value, font=row_font, fill=ink)
        y += 40


def share_image(site: "SiteContext", kit: Kit, title: str, kicker: str) -> "Image.Image":
    """One 1200x630 Open Graph image."""
    from PIL import Image, ImageDraw

    image = Image.new("RGB", SIZE, kit.color("bg"))
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, SIZE[0], 56], fill=kit.color("ink"))
    draw.ellipse([60, 21, 74, 35], fill=kit.color("bright"))
    draw.text((88, 17), kicker, font=kit.label(19), fill=kit.color("panel"))
    font, lines = fit_title(kit, title, 610)
    y = 104
    for line in lines:
        draw.text((60, y), line, font=font, fill=kit.color("ink"))
        y += int(font.size * 1.06)
    draw.line([60, 486, 690, 486], fill=kit.color("ink"), width=4)
    draw_lockup(draw, kit, site, (60, 516))
    draw_facts(draw, kit, site, (760, max(80, 343 - facts_height(site) // 2)))
    return image


def icon(size: int) -> "Image.Image":
    """Square app icon: the mark, full bleed (shared by every site)."""
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (size, size), ICON_INK)
    draw = ImageDraw.Draw(image)
    unit = size / 34
    draw.rectangle([6 * unit, 15 * unit, 21 * unit, 19 * unit], fill=ICON_LINE)
    draw.ellipse([22 * unit, 13.5 * unit, 29 * unit, 20.5 * unit], fill=ICON_DOT)
    return image


def image_jobs(site: "SiteContext") -> list[tuple[str, str, str]]:
    """``(relative path, title, kicker)`` for every share image the site uses."""
    kicker = str(site.home.get("kicker") or KICKER).upper().replace(" · ", "  ·  ")
    jobs = [("og/default.png", site.cfg.tagline, kicker)]
    jobs += [(f"og/{slug}.png", spec["h1"], kicker) for slug, spec in site.categories.items()]
    jobs += [(f"og/guides/{guide.slug}.png", guide.title, f"GUIDE  ·  {guide.reading_minutes} MIN READ") for guide in site.guides]
    return jobs


def generate_images(site: "SiteContext", static_dir: Path) -> list[Path]:
    """Write every share image for one site, in its theme, into its static directory; return the paths written."""
    if site.theme is None:
        raise ValueError("the site context has no theme loaded")
    kit = Kit(site.theme)
    written: list[Path] = []
    for relative, title, kicker in image_jobs(site):
        target = static_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        share_image(site, kit, title, kicker).save(target, optimize=True)
        written.append(target)
    return written


def generate_icons(static_dir: Path) -> list[Path]:
    """The app icon and logo, shared by every site in the family."""
    written: list[Path] = []
    for name, size in (("apple-touch-icon.png", 180), ("logo.png", 512)):
        icon(size).save(static_dir / name, optimize=True)
        written.append(static_dir / name)
    return written
