"""End-to-end tests for the website build: every mode, every page, every link.

Builds run against the real templates, content, and static files, with
fixture configs for the site and the facility so the assertions do not
depend on how far the owner has filled in the real config files.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from leadgen.website.build import BuildOptions, build_preview, build_site, main, reset_output
from leadgen.website.config import SiteConfigError

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures" / "website"
TODAY = date(2026, 9, 29)
UNCONFIRMED_CLAIMS = ("one food-safety program", "six to twelve months", "nationwide", "FDA-registered facility",
                      "FDA registered", "brands we work with", "SQF Level", "TO_CONFIRM", "TO_FILL")


def make_root(base: Path, site_config: str, facility: str) -> Path:
    """A throwaway repo root: real templates, content, and static files; fixture configs."""
    root = base / "repo"
    (root / "site").mkdir(parents=True)
    (root / "config").mkdir()
    for name in ("templates", "content", "static"):
        (root / "site" / name).symlink_to(REPO / "site" / name, target_is_directory=True)
    (root / "site" / "config.yaml").write_text((FIXTURES / site_config).read_text(encoding="utf-8"), encoding="utf-8")
    (root / "config" / "facility.yaml").write_text((FIXTURES / facility).read_text(encoding="utf-8"), encoding="utf-8")
    return root


def pages(dist: Path) -> dict[str, BeautifulSoup]:
    """Every HTML page in the build, parsed, keyed by path relative to dist."""
    return {str(path.relative_to(dist)): BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
            for path in sorted(dist.rglob("*.html"))}


def jsonld(soup: BeautifulSoup) -> list[dict]:
    """The page's JSON-LD graph nodes."""
    blocks = [json.loads(tag.string) for tag in soup.find_all("script", type="application/ld+json")]
    return [node for block in blocks for node in block["@graph"]]


@pytest.fixture(scope="module")
def production(tmp_path_factory):
    root = make_root(tmp_path_factory.mktemp("prod"), "site_complete.yaml", "facility_unconfirmed.yaml")
    result = build_site(BuildOptions(root=root, mode="production", today=TODAY))
    return result, result.output, pages(result.output)


@pytest.fixture(scope="module")
def confirmed(tmp_path_factory):
    root = make_root(tmp_path_factory.mktemp("confirmed"), "site_complete.yaml", "facility_confirmed.yaml")
    result = build_site(BuildOptions(root=root, mode="production", today=TODAY))
    return result.output, pages(result.output)


@pytest.fixture(scope="module")
def preview(tmp_path_factory):
    base = tmp_path_factory.mktemp("preview")
    root = make_root(base, "site_placeholders.yaml", "facility_unconfirmed.yaml")
    result = build_preview(BuildOptions(root=root, mode="preview", preview_file=base / "preview.html", today=TODAY))
    html = result.output.read_text(encoding="utf-8")
    return html, BeautifulSoup(html, "html.parser")


def test_production_build_writes_every_page_and_file(production):
    result, dist, parsed = production
    expected = {"index.html", "capabilities/index.html", "cookie-co-packer/index.html", "bakery-co-packer/index.html",
                "dog-treat-co-packer/index.html", "pet-food-co-packer/index.html", "guides/index.html", "faq/index.html",
                "about/index.html", "contact/index.html", "privacy/index.html", "thanks/index.html", "404.html",
                "guides/how-to-find-a-cookie-co-packer/index.html"}
    assert expected <= set(parsed)
    assert len([p for p in parsed if p.startswith("guides/") and p != "guides/index.html"]) >= 8
    for name in ("styles.css", "robots.txt", "sitemap.xml", "llms.txt", "llms-full.txt", "_headers", "favicon.svg",
                 "apple-touch-icon.png", "logo.png", "og/default.png", "fonts/archivo-var.woff2"):
        assert (dist / name).exists(), name
    assert result.warnings == []


def test_no_placeholders_or_unconfirmed_claims_anywhere(production):
    _, dist, _ = production
    for path in dist.rglob("*"):
        if path.suffix in {".html", ".txt", ".xml", ".css"} or path.name == "_headers":
            text = path.read_text(encoding="utf-8")
            for phrase in UNCONFIRMED_CLAIMS + ("draft.invalid", "yourdomain", "example.com"):
                assert phrase not in text, f"{phrase!r} in {path.relative_to(dist)}"


def test_every_internal_link_and_asset_resolves(production):
    _, dist, parsed = production
    ids = {name: {tag["id"] for tag in soup.find_all(id=True)} for name, soup in parsed.items()}
    for name, soup in parsed.items():
        for tag in soup.find_all(["a", "link", "img", "script", "form"]):
            target = tag.get("href") or tag.get("src") or tag.get("action")
            if not target or target.startswith(("http", "mailto:", "tel:")):
                continue
            path, _, anchor = target.partition("#")
            path = path.split("?")[0]
            if path:
                file = dist / path.lstrip("/")
                page = str((file / "index.html").relative_to(dist)) if path.endswith("/") else str(file.relative_to(dist))
                assert (dist / page).exists(), f"{name}: broken link {target}"
            else:
                page = name
            if anchor:
                assert anchor in ids[page], f"{name}: missing anchor {target}"


def test_each_page_has_one_h1_a_fitting_title_and_description(production):
    _, _, parsed = production
    for name, soup in parsed.items():
        assert len(soup.find_all("h1")) == 1, name
        assert len(soup.title.string) <= 65, name
        description = soup.find("meta", attrs={"name": "description"})["content"]
        assert 20 <= len(description) <= 170, name


def test_canonical_and_robots_meta(production):
    _, _, parsed = production
    canonical = parsed["faq/index.html"].find("link", rel="canonical")["href"]
    assert canonical == "https://openline.test/faq/"
    for name in ("thanks/index.html", "404.html"):
        assert parsed[name].find("meta", attrs={"name": "robots"})["content"].startswith("noindex")
        assert parsed[name].find("link", rel="canonical") is None
    assert parsed["index.html"].find("meta", attrs={"name": "robots"}) is None


def test_structured_data_describes_each_page(production):
    _, _, parsed = production
    types = {name: {node["@type"] for node in jsonld(soup)} for name, soup in parsed.items()}
    assert {"Organization", "WebSite", "Person", "Service", "FAQPage"} <= types["index.html"]
    assert {"Article", "BreadcrumbList"} <= types["guides/how-to-find-a-dog-treat-co-packer/index.html"]
    assert {"Service", "FAQPage", "BreadcrumbList"} <= types["cookie-co-packer/index.html"]
    faq_nodes = [n for n in jsonld(parsed["faq/index.html"]) if n["@type"] == "FAQPage"]
    assert len(faq_nodes[0]["mainEntity"]) == len(parsed["faq/index.html"].select(".faq details"))
    article = next(n for n in jsonld(parsed["guides/how-to-find-a-dog-treat-co-packer/index.html"]) if n["@type"] == "Article")
    assert article["citation"] and article["image"].startswith("https://openline.test/og/")
    service = next(n for n in jsonld(parsed["index.html"]) if n["@type"] == "Service")
    assert service["broker"] == {"@id": "https://openline.test/#org"} and "provider" not in service


def test_share_images_exist_for_every_page(production):
    _, dist, parsed = production
    for name, soup in parsed.items():
        image = soup.find("meta", property="og:image")["content"]
        assert (dist / image.replace("https://openline.test/", "")).exists(), name


def test_sitemap_llms_and_headers(production):
    _, dist, parsed = production
    sitemap = (dist / "sitemap.xml").read_text(encoding="utf-8")
    locs = set(re.findall(r"<loc>([^<]+)</loc>", sitemap))
    indexable = {f"https://openline.test/{name.replace('index.html', '')}" for name in parsed
                 if name not in {"thanks/index.html", "404.html"}}
    assert locs == indexable
    llms = (dist / "llms.txt").read_text(encoding="utf-8")
    full = (dist / "llms-full.txt").read_text(encoding="utf-8")
    for name in parsed:
        if name.startswith("guides/") and name != "guides/index.html":
            assert f"https://openline.test/{name.replace('index.html', '')}" in llms
    assert "## Frequently asked questions" in full and full.count("Short answer:") >= 8
    headers = (dist / "_headers").read_text(encoding="utf-8")
    assert "Content-Security-Policy: default-src 'self'" in headers and "X-Robots-Tag" not in headers


def test_forms_post_to_netlify_with_honeypot_and_source_page(production):
    _, _, parsed = production
    forms = {name: soup.find("form", class_="capacity-form") for name, soup in parsed.items()}
    with_forms = [name for name, form in forms.items() if form is not None]
    assert {"index.html", "contact/index.html", "cookie-co-packer/index.html",
            "guides/how-to-find-a-cookie-co-packer/index.html"} <= set(with_forms)
    for name in with_forms:
        form = forms[name]
        assert form["name"] == "capacity-check" and form["data-netlify"] == "true" and form["action"] == "/thanks/"
        assert form["netlify-honeypot"] == "bot-field" and form.find("input", attrs={"name": "bot-field"})
        assert form.find("input", attrs={"name": "form-name"})["value"] == "capacity-check"
        expected = "/" + name.replace("index.html", "")
        assert form.find("input", attrs={"name": "source_page"})["value"] == expected
        fields = {tag["name"] for tag in form.find_all(["input", "select", "textarea"])}
        assert {"product", "volume", "timing", "current_setup", "name", "company", "email", "phone", "notes"} <= fields


def test_form_choices_map_to_importer_segments(production):
    from leadgen.inbound import FormSubmission, submission_to_lead

    _, _, parsed = production
    form = parsed["index.html"].find("form", class_="capacity-form")
    setups = [option.string for option in form.find("select", attrs={"name": "current_setup"}).find_all("option") if option.get("value") != ""]
    for setup in setups:
        lead = submission_to_lead(FormSubmission.from_mapping({
            "product": "soft-baked cookies", "volume": "5,000 to 25,000", "timing": "Now", "current_setup": setup,
            "name": "Jo", "company": "Crumb Co, crumbco.com", "email": "jo@crumbco.com"}))
        assert lead.segment.value != "unknown", setup


def test_unconfirmed_facility_shows_no_numbers_or_certifications(production):
    _, _, parsed = production
    capabilities = parsed["capabilities/index.html"].get_text(" ")
    assert "We list only certifications we can document" in capabilities
    assert "confirms them for your product on the first call" in capabilities
    faq = parsed["faq/index.html"].get_text(" ")
    assert "gives you a sample date for your product" in faq


def test_confirmed_facts_appear_once_confirmed(confirmed):
    dist, parsed = confirmed
    capabilities = parsed["capabilities/index.html"].get_text(" ")
    for fact in ("SQF Level 2", "Kosher (OU)", "FDA-registered facility", "5,000 units", "about 10 days", "Springfield, IL", "Ships nationwide"):
        assert fact in capabilities, fact
    assert "about 10 days after it receives your product" in parsed["faq/index.html"].get_text(" ")
    assert "Minimum runs start at 5,000 units" in parsed["cookie-co-packer/index.html"].get_text(" ")
    assert "- Minimum run: 5,000 units" in (dist / "llms.txt").read_text(encoding="utf-8")


def test_production_refuses_placeholders(tmp_path):
    root = make_root(tmp_path, "site_placeholders.yaml", "facility_unconfirmed.yaml")
    with pytest.raises(SiteConfigError, match="contact.email is a placeholder"):
        build_site(BuildOptions(root=root, mode="production", today=TODAY))
    assert main([], root=root) == 2
    assert not (root / "site" / "dist").exists()


def test_draft_build_is_noindex_and_highlights_placeholders(tmp_path):
    root = make_root(tmp_path, "site_placeholders.yaml", "facility_unconfirmed.yaml")
    assert main(["--draft"], root=root) == 0
    dist = root / "site" / "dist"
    home = (dist / "index.html").read_text(encoding="utf-8")
    assert '<meta name="robots" content="noindex, nofollow">' in home and "draft-ribbon" in home
    assert '<mark class="todo"' in home and "TO_FILL" not in home
    assert (dist / "robots.txt").read_text(encoding="utf-8") == "User-agent: *\nDisallow: /\n"
    assert "X-Robots-Tag: noindex" in (dist / "_headers").read_text(encoding="utf-8")


def test_stale_capacity_status_warns(tmp_path):
    root = make_root(tmp_path, "site_complete.yaml", "facility_unconfirmed.yaml")
    result = build_site(BuildOptions(root=root, mode="production", today=date(2026, 12, 15)))
    assert any("capacity status is" in warning for warning in result.warnings)


def test_capacity_lines_must_be_facility_lines(tmp_path):
    root = make_root(tmp_path, "site_complete.yaml", "facility_unconfirmed.yaml")
    config = root / "site" / "config.yaml"
    config.write_text(config.read_text(encoding="utf-8").replace("lines: [cookie,", "lines: [candy, cookie,"), encoding="utf-8")
    with pytest.raises(SiteConfigError, match="candy"):
        build_site(BuildOptions(root=root, mode="production", today=TODAY))


def test_reset_output_refuses_other_directories(tmp_path):
    with pytest.raises(ValueError, match="must be named dist"):
        reset_output(tmp_path / "important")


def test_preview_is_one_self_contained_fragment(preview):
    html, soup = preview
    assert html.startswith("<title>") and "<style>" in html[:600]
    assert not re.search(r"<!doctype|<html[\s>]|<head[\s>]|<body[\s>]", html, re.IGNORECASE)
    stylesheets = [tag["href"] for tag in soup.find_all("link", rel="stylesheet")]
    assert stylesheets == [stylesheets[0]] and stylesheets[0].startswith("https://fonts.googleapis.com/")
    assert not soup.find_all("script", src=True) and not soup.find_all("img", src=re.compile("^http"))
    assert 'href="/' not in html and "TO_FILL" not in html and "TO_CONFIRM" not in html


def test_preview_routes_and_links_all_resolve(preview):
    _, soup = preview
    ids = [tag["id"] for tag in soup.find_all(id=True)]
    assert len(ids) == len(set(ids)), "duplicate ids in the preview"
    routes = {tag["id"] for tag in soup.find_all(attrs={"data-route": True})}
    assert {"home", "capabilities", "faq", "contact", "guides", "guide-how-to-find-a-cookie-co-packer"} <= routes
    for link in soup.find_all("a", href=re.compile("^#")):
        assert link["href"][1:] in ids, link["href"]


def test_preview_forms_never_post(preview):
    _, soup = preview
    forms = soup.find_all("form")
    assert forms and all(form.has_attr("data-preview") and not form.has_attr("action") for form in forms)
    assert "event.preventDefault()" in soup.find_all("script")[-1].string


def test_build_script_writes_a_preview(tmp_path):
    target = tmp_path / "preview.html"
    completed = subprocess.run([sys.executable, "site/build.py", "--preview", str(target)], cwd=REPO,
                               capture_output=True, text=True, timeout=120)
    assert completed.returncode == 0, completed.stderr
    assert target.read_text(encoding="utf-8").startswith("<title>")


def test_share_images_are_drawn_from_site_fonts(tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image

    from leadgen.website.build import load_context
    from leadgen.website.images import generate_images

    root = make_root(tmp_path, "site_complete.yaml", "facility_unconfirmed.yaml")
    site, _ = load_context(BuildOptions(root=root, mode="draft", today=TODAY))
    static = tmp_path / "static"
    (static / "fonts").mkdir(parents=True)
    for font in ("archivo-var.woff2", "ibm-plex-mono-500.woff2"):
        (static / "fonts" / font).write_bytes((REPO / "site" / "static" / "fonts" / font).read_bytes())
    written = generate_images(site, static)
    assert len(written) == 1 + len(site.categories) + len(site.guides) + 2
    assert Image.open(static / "og" / "default.png").size == (1200, 630)
    assert Image.open(static / "apple-touch-icon.png").size == (180, 180)
