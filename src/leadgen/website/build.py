"""Build one site of the family: ``python site/build.py --site ID [--draft | --preview FILE | --images]``.

The site comes from ``--site`` or the ``OPEN_LINE_SITE`` environment variable
(set per Netlify site). Production builds refuse to run while the site's
merged config has placeholders. Draft builds render the same pages with
placeholders highlighted and ``noindex`` everywhere. The preview is one HTML
fragment with hash routing, for review without a server.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from leadgen.facility import load_facility
from leadgen.website import indexnow, seo
from leadgen.website.config import SiteConfigError, is_placeholder, load_site, publish_problems, site_ids, unknown_lines
from leadgen.website.content import ContentError, load_categories, load_faq, load_guides, load_landings, select_guides
from leadgen.website.facts import build_facts
from leadgen.website.forms import load_form, load_home
from leadgen.website.pages import Page, all_pages
from leadgen.website.render import SiteContext, environment, render_page, rewrite_internal_links

STALE_AFTER_DAYS = 45
DRAFT_DOMAIN = "https://draft.invalid"
SITE_ENV = "OPEN_LINE_SITE"
STATIC_FILES = ("favicon.svg", "apple-touch-icon.png", "logo.png")
STATIC_DIRS = ("fonts", "og")
GOOGLE_FONTS = ("https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..100,500..900"
                "&family=IBM+Plex+Mono:wght@500&family=Libre+Franklin:ital,wght@0,400..700;1,400..600&display=swap")


@dataclass
class BuildOptions:
    """Where to read, where to write, and which mode to build."""

    root: Path
    site_id: str
    mode: str = "production"
    dist: Path | None = None
    preview_file: Path | None = None
    today: date = field(default_factory=lambda: datetime.now(timezone.utc).date())

    @property
    def site_dir(self) -> Path:
        """``site/`` inside the repo."""
        return self.root / "site"

    @property
    def own_dir(self) -> Path:
        """``site/sites/<id>/``: this site's settings, home copy, form, and share images."""
        return self.site_dir / "sites" / self.site_id

    @property
    def output_dir(self) -> Path:
        """Where multi-page builds go (``site/dist`` unless overridden)."""
        return self.dist or self.site_dir / "dist"

    def __repr__(self) -> str:
        return f"BuildOptions(site_id={self.site_id!r}, mode={self.mode!r}, root={str(self.root)!r})"


@dataclass
class BuildResult:
    """What a build produced."""

    pages: list[Page]
    warnings: list[str]
    output: Path
    message: str = ""

    def __repr__(self) -> str:
        return f"BuildResult(pages={len(self.pages)}, warnings={len(self.warnings)}, output={str(self.output)!r})"


def load_context(options: BuildOptions) -> tuple[SiteContext, list[str]]:
    """Load config, confirmed facts, and content; return the template context and warnings."""
    cfg = load_site(options.site_dir, options.site_id)
    facility = load_facility(options.root / "config" / "facility.yaml")
    wrong = unknown_lines(cfg, [category.value for category in facility.categories])
    if wrong:
        raise SiteConfigError(f"capacity.lines includes lines the facility does not run: {', '.join(wrong)}")
    if options.mode == "production":
        problems = publish_problems(cfg)
        if problems:
            raise SiteConfigError(f"site {cfg.id} is not ready to publish (site/shared.yaml, site/sites/{cfg.id}/site.yaml):"
                                  "\n  - " + "\n  - ".join(problems))
    elif is_placeholder(cfg.domain):
        cfg = cfg.model_copy(update={"domain": DRAFT_DOMAIN})
    facts = build_facts(facility, cfg)
    site = SiteContext(cfg, facts, options.mode, options.today, options.own_dir / "static")
    _load_content(site, options)
    return site, _warnings(site, options)


def _load_content(site: SiteContext, options: BuildOptions) -> None:
    """Shared content filtered to what this site lists, plus its own home copy and questionnaire."""
    cfg, content = site.cfg, options.site_dir / "content"
    tokens = {"reply_within": cfg.reply_within}
    prefix = (lambda slug: f"guide-{slug}--") if options.mode == "preview" else (lambda slug: "")
    site.guides = select_guides(load_guides(content / "guides", prefix), cfg.guides, f"site {cfg.id}")
    site.faq = load_faq(content / "faq.yaml", site.facts, tokens, cfg.id)
    site.categories = load_categories(content / "categories.yaml", site.facts, cfg.categories)
    site.landings = load_landings(content / "landing.yaml", cfg.landings)
    for guide in site.guides:
        guide.html = rewrite_internal_links(guide.html, site)
    site.home = load_home(options.own_dir / "home.yaml", tokens)
    site.form = load_form(options.own_dir / "form.yaml", tokens)


def _warnings(site: SiteContext, options: BuildOptions) -> list[str]:
    """Stale capacity status and missing share images."""
    warnings: list[str] = []
    age = site.cfg.capacity.age_days(options.today)
    if age > STALE_AFTER_DAYS:
        warnings.append(f"capacity status is {age} days old ({site.cfg.capacity.label()}): "
                        "confirm with the facility and update capacity.as_of")
    expected = [f"og/{slug}.png" for slug in site.categories] + [f"og/guides/{g.slug}.png" for g in site.guides]
    missing = [path for path in expected if not (site.static_dir / path).exists()]
    if missing:
        warnings.append(f"{len(missing)} share images missing (using the default): run python site/build.py --images")
    return warnings


def stylesheet(site_dir: Path, with_fonts: bool) -> str:
    """The site CSS; production prepends the self-hosted @font-face rules."""
    css = (site_dir / "static" / "styles.css").read_text(encoding="utf-8")
    if with_fonts:
        css = (site_dir / "static" / "fonts.css").read_text(encoding="utf-8") + "\n" + css
    return css


def reset_output(path: Path) -> None:
    """Empty the output directory, refusing anything not named ``dist``."""
    if path.name != "dist":
        raise ValueError(f"refusing to clear {path}: the output directory must be named dist")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def copy_static(static_dirs: list[Path], out: Path) -> None:
    """Copy fonts, share images, and icons into the output; later directories add to or replace earlier ones."""
    for static_dir in static_dirs:
        for name in STATIC_DIRS:
            if (static_dir / name).is_dir():
                shutil.copytree(static_dir / name, out / name, dirs_exist_ok=True)
        for name in STATIC_FILES:
            if (static_dir / name).exists():
                shutil.copy2(static_dir / name, out / name)


def page_links(site: SiteContext) -> list[tuple[str, str, str]]:
    """``(title, path, note)`` for the llms.txt page map."""
    links = [("Capabilities", "capabilities/", "confirmed production lines, services, and certifications")]
    links += [(spec["h1"], f"{slug}/", spec["description"]) for slug, spec in site.categories.items()]
    links += [("FAQ", "faq/", site.cfg.wording.faq_description),
              ("About", "about/", "who we are, how the referral model works, who pays us"),
              ("Contact", "contact/", "direct contact details and the capacity-check form")]
    return links


def write_machine_files(site: SiteContext, pages: list[Page], out: Path) -> None:
    """sitemap.xml, robots.txt, _headers, llms.txt, and llms-full.txt."""
    newest = max((guide.updated for guide in site.guides), default=site.today)
    fresh = {"": newest, "guides": newest}
    entries = [(site.abs_url(page.key), page.lastmod or fresh.get(page.key)) for page in pages if page.in_sitemap]
    files = {
        "sitemap.xml": seo.render_sitemap(entries),
        "robots.txt": seo.render_robots(site.cfg, site.draft),
        "_headers": seo.render_headers(site.cfg, site.draft),
        "llms.txt": seo.render_llms_txt(site.cfg, site.facts, site.guides, page_links(site)),
        "llms-full.txt": seo.render_llms_full(site.cfg, site.facts, site.guides, site.faq),
    }
    ownership = indexnow.key_file(site.cfg)
    if ownership and not site.draft:
        files[ownership[0]] = ownership[1]
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8")


def build_site(options: BuildOptions) -> BuildResult:
    """Render every page and supporting file into the output directory."""
    site, warnings = load_context(options)
    env = environment(options.site_dir / "templates")
    css = stylesheet(options.site_dir, with_fonts=True)
    site.css_version = hashlib.sha256(css.encode("utf-8")).hexdigest()[:10]
    pages = all_pages(site)
    out = options.output_dir
    reset_output(out)
    for page in pages:
        target = out / page.output_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_page(env, site, page, "base.html"), encoding="utf-8")
    copy_static([options.site_dir / "static", site.static_dir], out)
    (out / "styles.css").write_text(css, encoding="utf-8")
    write_machine_files(site, pages, out)
    return BuildResult(pages, warnings, out)


def build_preview(options: BuildOptions) -> BuildResult:
    """Render the whole site as one HTML fragment with hash routing."""
    from markupsafe import Markup

    if options.preview_file is None:
        raise ValueError("preview_file is required for a preview build")
    site, warnings = load_context(options)
    env = environment(options.site_dir / "templates")
    pages = [page for page in all_pages(site) if page.key != "404" and not page.key.startswith("lp/")]
    routes = "\n".join(render_page(env, site, page, "_route.html") for page in pages)
    static = options.site_dir / "static"
    html = env.get_template("preview.html").render(
        site=site, routes=Markup(routes), fonts_url=GOOGLE_FONTS,
        css=Markup(stylesheet(options.site_dir, with_fonts=False) + (static / "preview.css").read_text(encoding="utf-8")),
        script=Markup((static / "preview.js").read_text(encoding="utf-8")))
    options.preview_file.parent.mkdir(parents=True, exist_ok=True)
    options.preview_file.write_text(html, encoding="utf-8")
    return BuildResult(pages, warnings, options.preview_file)


def submit_indexnow(root: Path, site_id: str, client: object | None = None) -> BuildResult:
    """Ping IndexNow with every indexable URL; needs a publishable config (real domain) and a key."""
    site, _ = load_context(BuildOptions(root=root, site_id=site_id, mode="production"))
    urls = [site.abs_url(page.key) for page in all_pages(site) if page.in_sitemap and not page.noindex]
    try:
        status = indexnow.ping(site.cfg, urls, client)  # type: ignore[arg-type]
    except indexnow.IndexNowError as exc:
        raise SiteConfigError(str(exc)) from exc
    return BuildResult([], [], root / "site", f"IndexNow accepted {len(urls)} URLs (HTTP {status})")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Command-line flags for ``site/build.py``."""
    parser = argparse.ArgumentParser(prog="site/build.py", description="Build one site of the family.")
    parser.add_argument("--site", help=f"which site (a folder in site/sites/); default: the {SITE_ENV} environment variable")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--draft", action="store_true", help="build with placeholders highlighted and noindex")
    mode.add_argument("--preview", type=Path, metavar="FILE", help="write the whole site as one HTML file")
    mode.add_argument("--images", action="store_true", help="regenerate share images and icons (needs Pillow; every site unless --site)")
    mode.add_argument("--indexnow", action="store_true", help="after a deploy: tell Bing and other IndexNow engines what changed")
    parser.add_argument("--out", type=Path, help="output directory, must be named dist (default site/dist)")
    return parser.parse_args(argv)


def chosen_site(args: argparse.Namespace, root: Path) -> str:
    """The site to build: ``--site``, else ``OPEN_LINE_SITE``; an error lists the choices."""
    site_id = args.site or os.environ.get(SITE_ENV, "")
    if not site_id:
        raise SiteConfigError(f"say which site to build with --site or {SITE_ENV}: {', '.join(site_ids(root / 'site'))}")
    return site_id


def write_images(root: Path, only: str | None) -> BuildResult:
    """Share images for one site (or every site) and the shared icons."""
    from leadgen.website.images import generate_icons, generate_images

    written: list[Path] = []
    for site_id in [only] if only else site_ids(root / "site"):
        options = BuildOptions(root=root, site_id=site_id, mode="draft")
        site, _ = load_context(options)
        written += generate_images(site, options.own_dir / "static", root / "site" / "static" / "fonts")
    written += generate_icons(root / "site" / "static")
    return BuildResult([], [], root / "site", f"wrote {len(written)} images under {root / 'site'} (commit them)")


def run(args: argparse.Namespace, root: Path) -> BuildResult:
    """Dispatch to the requested build."""
    if args.images:
        return write_images(root, args.site or os.environ.get(SITE_ENV) or None)
    site_id = chosen_site(args, root)
    if args.indexnow:
        return submit_indexnow(root, site_id)
    if args.preview:
        return build_preview(BuildOptions(root=root, site_id=site_id, mode="preview", preview_file=args.preview))
    return build_site(BuildOptions(root=root, site_id=site_id, mode="draft" if args.draft else "production", dist=args.out))


def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    """Entry point; returns a process exit code (2 when the config or content is not ready)."""
    args = parse_args(argv)
    root = root or Path(__file__).resolve().parents[3]
    try:
        result = run(args, root)
    except (SiteConfigError, ContentError) as exc:
        print(f"build stopped: {exc}", file=sys.stderr)
        return 2
    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    print(result.message or f"built {len(result.pages)} pages -> {result.output}")
    return 0
