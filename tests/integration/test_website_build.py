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
import yaml
from bs4 import BeautifulSoup

from leadgen.website.build import BuildOptions, build_preview, build_site, main, reset_output
from leadgen.website.config import SiteConfigError, load_site, site_ids

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures" / "website"
TODAY = date(2026, 9, 29)
SITES = tuple(site_ids(REPO / "site"))
BAKERY = "https://bakery.openline.test"
UNCONFIRMED_CLAIMS = ("one food-safety program", "six to twelve months", "nationwide", "FDA-registered facility",
                      "FDA registered", "brands we work with", "SQF Level", "TO_CONFIRM", "TO_FILL")


def domain(site_id: str) -> str:
    """The fictional domain a complete test family gives each site."""
    return f"https://{site_id}.openline.test"


def make_root(base: Path, shared_config: str, facility: str) -> Path:
    """A throwaway repo root: real templates, content, static files, and site folders; fixture configs.

    The fixture replaces site/shared.yaml. With a complete fixture every site also gets a real test domain,
    so the whole family is publishable; with the placeholder fixture the sites keep their placeholder domains.
    """
    root = base / "repo"
    (root / "site" / "sites").mkdir(parents=True)
    (root / "config").mkdir()
    for name in ("templates", "content", "static"):
        (root / "site" / name).symlink_to(REPO / "site" / name, target_is_directory=True)
    shared = yaml.safe_load((FIXTURES / shared_config).read_text(encoding="utf-8"))
    (root / "site" / "shared.yaml").write_text(yaml.safe_dump(shared | {"sites": list(SITES)}), encoding="utf-8")
    for site_id in SITES:
        source, own = REPO / "site" / "sites" / site_id, root / "site" / "sites" / site_id
        own.mkdir()
        for item in source.iterdir():
            if item.name != "site.yaml":
                (own / item.name).symlink_to(item, target_is_directory=item.is_dir())
        settings = yaml.safe_load((source / "site.yaml").read_text(encoding="utf-8"))
        if "TO_FILL" not in shared["domain"]:
            settings["domain"] = domain(site_id)
        (own / "site.yaml").write_text(yaml.safe_dump(settings, sort_keys=False), encoding="utf-8")
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
def family(tmp_path_factory):
    """Every site in the family, built for production once: id -> (result, dist, parsed pages)."""
    root = make_root(tmp_path_factory.mktemp("prod"), "site_complete.yaml", "facility_unconfirmed.yaml")
    built = {}
    for site_id in SITES:
        dist = tmp_path_factory.mktemp(f"out-{site_id}") / "dist"
        result = build_site(BuildOptions(root=root, site_id=site_id, mode="production", today=TODAY, dist=dist))
        built[site_id] = (result, result.output, pages(result.output))
    return built


@pytest.fixture(scope="module")
def production(family):
    """The baked-goods site, where the site-specific assertions look."""
    return family["bakery"]


@pytest.fixture(scope="module")
def confirmed(tmp_path_factory):
    root = make_root(tmp_path_factory.mktemp("confirmed"), "site_complete.yaml", "facility_confirmed.yaml")
    result = build_site(BuildOptions(root=root, site_id="bakery", mode="production", today=TODAY))
    return result.output, pages(result.output)


@pytest.fixture(scope="module")
def preview(tmp_path_factory):
    base = tmp_path_factory.mktemp("preview")
    root = make_root(base, "site_placeholders.yaml", "facility_unconfirmed.yaml")
    result = build_preview(BuildOptions(root=root, site_id="bakery", mode="preview", preview_file=base / "preview.html", today=TODAY))
    html = result.output.read_text(encoding="utf-8")
    return html, BeautifulSoup(html, "html.parser")


COMMON_PAGES = {"index.html", "capabilities/index.html", "guides/index.html", "faq/index.html", "about/index.html",
                "contact/index.html", "privacy/index.html", "thanks/index.html", "404.html"}


def test_production_build_writes_every_page_and_file(family):
    for site_id, (result, dist, parsed) in family.items():
        cfg = load_site(REPO / "site", site_id)
        expected = COMMON_PAGES | {f"{slug}/index.html" for slug in cfg.categories or []}
        expected |= {f"guides/{slug}/index.html" for slug in cfg.guides or []}
        expected |= {f"lp/{slug}/index.html" for slug in cfg.landings or []}
        assert set(parsed) == expected, site_id
        for name in ("styles.css", "robots.txt", "sitemap.xml", "llms.txt", "llms-full.txt", "_headers", "favicon.svg",
                     "apple-touch-icon.png", "logo.png", "og/default.png", "fonts/archivo-var.woff2", f"{cfg.indexnow_key}.txt"):
            assert (dist / name).exists(), (site_id, name)
        assert result.warnings == [], site_id


def test_the_baked_goods_site_carries_only_its_own_lines(production):
    _, _, parsed = production
    assert {"cookie-co-packer/index.html", "bakery-co-packer/index.html"} <= set(parsed)
    assert "dog-treat-co-packer/index.html" not in parsed
    assert len([p for p in parsed if p.startswith("guides/") and p != "guides/index.html"]) >= 8


@pytest.mark.parametrize("site_id", SITES)
def test_no_placeholders_or_unconfirmed_claims_anywhere(family, site_id):
    _, dist, _ = family[site_id]
    for path in dist.rglob("*"):
        if path.suffix in {".html", ".txt", ".xml", ".css"} or path.name == "_headers":
            text = path.read_text(encoding="utf-8")
            for phrase in UNCONFIRMED_CLAIMS + ("draft.invalid", "yourdomain", "example.com"):
                assert phrase not in text, f"{phrase!r} in {site_id}: {path.relative_to(dist)}"


@pytest.mark.parametrize("site_id", SITES)
def test_every_internal_link_and_asset_resolves(family, site_id):
    _, dist, parsed = family[site_id]
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


@pytest.mark.parametrize("site_id", SITES)
def test_each_page_has_one_h1_a_fitting_title_and_description(family, site_id):
    _, _, parsed = family[site_id]
    for name, soup in parsed.items():
        assert len(soup.find_all("h1")) == 1, name
        assert len(soup.title.string) <= 65, name
        description = soup.find("meta", attrs={"name": "description"})["content"]
        assert 20 <= len(description) <= 170, name


def test_canonical_and_robots_meta(production):
    _, _, parsed = production
    canonical = parsed["faq/index.html"].find("link", rel="canonical")["href"]
    assert canonical == f"{BAKERY}/faq/"
    for name in ("thanks/index.html", "404.html"):
        assert parsed[name].find("meta", attrs={"name": "robots"})["content"].startswith("noindex")
        assert parsed[name].find("link", rel="canonical") is None
    assert parsed["index.html"].find("meta", attrs={"name": "robots"}) is None


def test_structured_data_describes_each_page(production):
    _, _, parsed = production
    types = {name: {node["@type"] for node in jsonld(soup)} for name, soup in parsed.items()}
    assert {"Organization", "WebSite", "Person", "Service", "FAQPage"} <= types["index.html"]
    assert {"Article", "BreadcrumbList"} <= types["guides/how-to-find-a-cookie-co-packer/index.html"]
    assert {"Service", "FAQPage", "BreadcrumbList"} <= types["cookie-co-packer/index.html"]
    faq_nodes = [n for n in jsonld(parsed["faq/index.html"]) if n["@type"] == "FAQPage"]
    assert len(faq_nodes[0]["mainEntity"]) == len(parsed["faq/index.html"].select(".faq details"))
    article = next(n for n in jsonld(parsed["guides/how-to-find-a-cookie-co-packer/index.html"]) if n["@type"] == "Article")
    assert article["citation"] and article["image"].startswith(f"{BAKERY}/og/")
    service = next(n for n in jsonld(parsed["index.html"]) if n["@type"] == "Service")
    assert service["broker"] == {"@id": f"{BAKERY}/#org"} and "provider" not in service


def test_share_images_exist_for_every_page(production):
    _, dist, parsed = production
    for name, soup in parsed.items():
        image = soup.find("meta", property="og:image")["content"]
        assert (dist / image.replace(f"{BAKERY}/", "")).exists(), name


def test_sitemap_llms_and_headers(production):
    _, dist, parsed = production
    sitemap = (dist / "sitemap.xml").read_text(encoding="utf-8")
    locs = set(re.findall(r"<loc>([^<]+)</loc>", sitemap))
    indexable = {f"{BAKERY}/{name.replace('index.html', '')}" for name in parsed
                 if name not in {"thanks/index.html", "404.html"} and not name.startswith("lp/")}
    assert locs == indexable
    llms = (dist / "llms.txt").read_text(encoding="utf-8")
    full = (dist / "llms-full.txt").read_text(encoding="utf-8")
    for name in parsed:
        if name.startswith("guides/") and name != "guides/index.html":
            assert f"{BAKERY}/{name.replace('index.html', '')}" in llms
    assert "## Frequently asked questions" in full and full.count("Short answer:") >= 8
    headers = (dist / "_headers").read_text(encoding="utf-8")
    assert "Content-Security-Policy: default-src 'self'" in headers and "X-Robots-Tag" not in headers


@pytest.mark.parametrize("site_id", SITES)
def test_forms_post_to_netlify_with_honeypot_source_page_and_site(family, site_id):
    from leadgen.website.forms import field_names, load_form

    _, _, parsed = family[site_id]
    form_spec = load_form(REPO / "site" / "sites" / site_id / "form.yaml")
    forms = {name: soup.find("form", class_="capacity-form") for name, soup in parsed.items()}
    with_forms = [name for name, form in forms.items() if form is not None]
    assert {"index.html", "contact/index.html"} <= set(with_forms)
    assert all(name in with_forms for name in parsed if name.startswith(("lp/", "guides/")) and name != "guides/index.html")
    for name in with_forms:
        form = forms[name]
        assert form["name"] == "capacity-check" and form["data-netlify"] == "true" and form["action"] == "/thanks/"
        assert form["netlify-honeypot"] == "bot-field" and form.find("input", attrs={"name": "bot-field"})
        assert form.find("input", attrs={"name": "form-name"})["value"] == "capacity-check"
        expected = "/" + name.replace("index.html", "")
        assert form.find("input", attrs={"name": "source_page"})["value"] == expected
        assert form.find("input", attrs={"name": "site"})["value"] == site_id
        fields = {tag["name"].removesuffix("[]") for tag in form.find_all(["input", "select", "textarea"])}
        assert set(field_names(form_spec)) <= fields


@pytest.mark.parametrize("site_id", SITES)
def test_form_choices_map_to_importer_segments_and_tags(family, site_id):
    from leadgen.inbound import FormSubmission, submission_to_lead

    _, _, parsed = family[site_id]
    form = parsed["index.html"].find("form", class_="capacity-form")
    question = form.find("select", attrs={"name": "current_setup"}) or form.find("select", attrs={"name": "stage"})
    for option in question.find_all("option"):
        if option.get("value") == "":
            continue
        lead = submission_to_lead(FormSubmission.from_mapping({
            "product": "soft-baked cookies", "volume": "5,000 to 25,000", "timing": "Now", question["name"]: option.string,
            "name": "Jo", "company": "Crumb Co, crumbco.com", "email": "jo@crumbco.com", "site": site_id}))
        assert lead.segment.value != "unknown", (site_id, option.string)
        assert f"site:{site_id}" in lead.tags


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
        build_site(BuildOptions(root=root, site_id="bakery", mode="production", today=TODAY))
    assert main(["--site", "bakery"], root=root) == 2
    assert not (root / "site" / "dist").exists()


def test_draft_build_is_noindex_and_highlights_placeholders(tmp_path):
    root = make_root(tmp_path, "site_placeholders.yaml", "facility_unconfirmed.yaml")
    assert main(["--site", "pet", "--draft"], root=root) == 0
    dist = root / "site" / "dist"
    home = (dist / "index.html").read_text(encoding="utf-8")
    assert '<meta name="robots" content="noindex, nofollow">' in home and "draft-ribbon" in home
    assert '<mark class="todo"' in home and "TO_FILL" not in home
    assert (dist / "robots.txt").read_text(encoding="utf-8") == "User-agent: *\nDisallow: /\n"
    assert "X-Robots-Tag: noindex" in (dist / "_headers").read_text(encoding="utf-8")


def test_stale_capacity_status_warns(tmp_path):
    root = make_root(tmp_path, "site_complete.yaml", "facility_unconfirmed.yaml")
    result = build_site(BuildOptions(root=root, site_id="bakery", mode="production", today=date(2026, 12, 15)))
    assert any("capacity status is" in warning for warning in result.warnings)


def test_capacity_lines_must_be_facility_lines(tmp_path):
    root = make_root(tmp_path, "site_complete.yaml", "facility_unconfirmed.yaml")
    config = root / "site" / "sites" / "pet" / "site.yaml"
    settings = yaml.safe_load(config.read_text(encoding="utf-8"))
    config.write_text(yaml.safe_dump(settings | {"lines": ["candy", "pet_food"]}), encoding="utf-8")
    with pytest.raises(SiteConfigError, match="candy"):
        build_site(BuildOptions(root=root, site_id="pet", mode="production", today=TODAY))


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
    completed = subprocess.run([sys.executable, "site/build.py", "--site", "bakery", "--preview", str(target)], cwd=REPO,
                               capture_output=True, text=True, timeout=120)
    assert completed.returncode == 0, completed.stderr
    assert target.read_text(encoding="utf-8").startswith("<title>")


def test_share_images_are_drawn_from_site_fonts(tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image

    from leadgen.website.build import load_context
    from leadgen.website.images import generate_icons, generate_images

    root = make_root(tmp_path, "site_complete.yaml", "facility_unconfirmed.yaml")
    site, _ = load_context(BuildOptions(root=root, site_id="pet", mode="draft", today=TODAY))
    static = tmp_path / "static"
    written = generate_images(site, static, REPO / "site" / "static" / "fonts")
    assert len(written) == 1 + len(site.categories) + len(site.guides)
    assert Image.open(static / "og" / "default.png").size == (1200, 630)
    assert [path.name for path in generate_icons(static)] == ["apple-touch-icon.png", "logo.png"]
    assert Image.open(static / "apple-touch-icon.png").size == (180, 180)


def test_landing_pages_are_noindex_and_tag_the_channel(production, preview):
    _, dist, parsed = production
    page = parsed["lp/google-bakery/index.html"]
    assert page.find("meta", attrs={"name": "robots"})["content"].startswith("noindex")
    assert page.find("input", attrs={"name": "source_page"})["value"] == "/lp/google-bakery/"
    assert "/lp/" not in (dist / "sitemap.xml").read_text(encoding="utf-8")
    assert "/lp/" not in (dist / "llms.txt").read_text(encoding="utf-8")
    assert not preview[1].find(id="lp-google-bakery")


def test_line_pages_carry_their_extra_sections(family):
    def text(site_id: str, name: str) -> str:
        return " ".join(family[site_id][2][name].get_text(" ").split())

    assert "Shelf-stable and individually wrapped cookies" in text("bakery", "cookie-co-packer/index.html")
    assert "Private label or your own recipe" in text("pet", "dog-treat-co-packer/index.html")


def test_multiple_skus_show_only_once_confirmed(production, confirmed):
    _, _, open_pages = production
    _, confirmed_pages = confirmed
    assert "Multiple welcome" not in open_pages["index.html"].get_text(" ")
    assert "facility confirms line fit for each one" in open_pages["faq/index.html"].get_text(" ")
    assert "Multiple welcome" in confirmed_pages["index.html"].get_text(" ")
    assert "Yes. Multiple SKUs are welcome." in confirmed_pages["faq/index.html"].get_text(" ")


def test_indexnow_key_file_ships_only_in_production(production, tmp_path):
    _, dist, _ = production
    key = load_site(REPO / "site", "bakery").indexnow_key
    assert (dist / f"{key}.txt").read_text(encoding="utf-8") == key
    root = make_root(tmp_path, "site_complete.yaml", "facility_unconfirmed.yaml")
    assert main(["--site", "bakery", "--draft"], root=root) == 0
    assert not list((root / "site" / "dist").glob(f"{key}.txt"))


def test_indexnow_ping_submits_every_indexable_url(tmp_path):
    import httpx

    from leadgen.website.build import submit_indexnow

    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(202)

    root = make_root(tmp_path, "site_complete.yaml", "facility_unconfirmed.yaml")
    result = submit_indexnow(root, "bakery", httpx.Client(transport=httpx.MockTransport(handler)))
    body = seen[0]
    key = load_site(REPO / "site", "bakery").indexnow_key
    assert body["host"] == "bakery.openline.test" and body["keyLocation"].endswith(f"/{key}.txt")
    assert f"{BAKERY}/faq/" in body["urlList"] and not any("/lp/" in url or "/thanks/" in url for url in body["urlList"])
    assert "IndexNow accepted" in result.message


def test_indexnow_ping_reports_refusals_and_placeholders(tmp_path):
    import httpx

    from leadgen.website.build import submit_indexnow

    root = make_root(tmp_path, "site_complete.yaml", "facility_unconfirmed.yaml")
    refusing = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(403)))
    with pytest.raises(SiteConfigError, match="HTTP 403"):
        submit_indexnow(root, "bakery", refusing)
    draft_root = make_root(tmp_path / "draft", "site_placeholders.yaml", "facility_unconfirmed.yaml")
    assert main(["--site", "bakery", "--indexnow"], root=draft_root) == 2


def test_shared_guides_point_to_one_canonical_home(family):
    _, pet_dist, pet_pages = family["pet"]
    shared = "guides/co-packer-minimums-lead-times-and-costs/index.html"
    own = "guides/how-to-find-a-dog-treat-co-packer/index.html"
    assert pet_pages[shared].find("link", rel="canonical")["href"] == f"{BAKERY}/guides/co-packer-minimums-lead-times-and-costs/"
    assert pet_pages[own].find("link", rel="canonical")["href"] == "https://pet.openline.test/guides/how-to-find-a-dog-treat-co-packer/"
    sitemap = (pet_dist / "sitemap.xml").read_text(encoding="utf-8")
    assert "how-to-find-a-dog-treat-co-packer" in sitemap and "co-packer-minimums" not in sitemap
    _, bakery_dist, _ = family["bakery"]
    assert "co-packer-minimums" in (bakery_dist / "sitemap.xml").read_text(encoding="utf-8")


def test_guides_link_to_sibling_sites_for_guides_this_site_lacks(family):
    _, _, parsed = family["bakery"]
    links = [a["href"] for a in parsed["guides/from-farmers-market-to-packaged-product/index.html"].select(".prose a")]
    assert "https://pet.openline.test/guides/how-to-find-a-dog-treat-co-packer/" in links


def test_footers_link_the_family(family):
    for site_id, (_, _, parsed) in family.items():
        links = {a["href"] for a in parsed["index.html"].select(".family a")}
        assert links == {f"https://{other}.openline.test/" for other in SITES if other != site_id}, site_id


def test_each_site_speaks_to_its_audience(family):
    pet_home = family["pet"][2]["index.html"]
    assert "pet" in pet_home.find("h1").get_text().lower()
    assert pet_home.find("select", attrs={"name": "pet_product"}) and pet_home.find("select", attrs={"name": "species"})
    bakery_home = family["bakery"][2]["index.html"]
    assert not bakery_home.find("select", attrs={"name": "species"})
    fit = bakery_home.find("details", class_="fit")
    assert fit and fit.find("input", attrs={"name": "allergens[]"}) and not fit.find(attrs={"required": True})


def test_the_build_needs_a_site(tmp_path, monkeypatch, capsys):
    root = make_root(tmp_path, "site_complete.yaml", "facility_unconfirmed.yaml")
    monkeypatch.delenv("OPEN_LINE_SITE", raising=False)
    assert main(["--draft"], root=root) == 2
    assert "--site or OPEN_LINE_SITE" in capsys.readouterr().err
    monkeypatch.setenv("OPEN_LINE_SITE", "pet")
    assert main(["--draft"], root=root) == 0
    assert "pet" in (root / "site" / "dist" / "index.html").read_text(encoding="utf-8").lower()
    assert main(["--site", "nope", "--draft"], root=root) == 2


def test_images_command_writes_one_site_and_the_shared_icons(tmp_path):
    pytest.importorskip("PIL")
    import shutil

    root = make_root(tmp_path, "site_complete.yaml", "facility_unconfirmed.yaml")
    static = root / "site" / "static"
    static.unlink()  # a private copy, so the command never writes into the repo
    shutil.copytree(REPO / "site" / "static" / "fonts", static / "fonts")
    own_static = root / "site" / "sites" / "pet" / "static"
    if own_static.is_symlink():
        own_static.unlink()
    assert main(["--images", "--site", "pet"], root=root) == 0
    assert (own_static / "og" / "default.png").exists() and (own_static / "og" / "dog-treat-co-packer.png").exists()
    assert (static / "logo.png").exists() and (static / "apple-touch-icon.png").exists()


def test_product_lines_show_only_once_multiple_skus_are_confirmed(production, confirmed):
    _, _, open_pages = production
    _, confirmed_pages = confirmed
    assert not open_pages["index.html"].select(".sku-line")
    lines = confirmed_pages["index.html"].select(".sku-line")
    assert len(lines) == 3 and all(len(line.select("li")) >= 2 for line in lines)
    assert "Bring the whole line" in confirmed_pages["index.html"].get_text(" ")


def test_every_site_asks_for_every_product(family):
    for site_id, (_, _, parsed) in family.items():
        label = parsed["index.html"].find("label", attrs={"for": "capacity-product"})
        assert "List every product" in label.get_text(), site_id
