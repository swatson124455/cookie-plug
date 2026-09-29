"""Unit tests for the website generator: config, facts, content, SEO output, and URL rules."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
import yaml

from leadgen.facility import load_facility
from leadgen.website import seo
from leadgen.website.config import (
    CapacityStatus,
    SiteConfig,
    SiteConfigError,
    display_value,
    is_placeholder,
    load_site_config,
    publish_problems,
    unknown_lines,
)
from leadgen.website.content import (
    ContentError,
    FaqItem,
    fill_tokens,
    load_categories,
    load_faq,
    load_guide,
    load_guides,
    render_markdown,
    resolve_answer,
    split_front_matter,
)
from leadgen.website.facts import build_facts
from leadgen.website.render import SiteContext, keep_hyphenated, rewrite_internal_links

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "website"
REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def complete_cfg() -> SiteConfig:
    return load_site_config(FIXTURES / "site_complete.yaml")


@pytest.fixture
def placeholder_cfg() -> SiteConfig:
    return load_site_config(FIXTURES / "site_placeholders.yaml")


@pytest.fixture
def open_facts(complete_cfg):
    return build_facts(load_facility(FIXTURES / "facility_unconfirmed.yaml"), complete_cfg)


@pytest.fixture
def confirmed_facts(complete_cfg):
    return build_facts(load_facility(FIXTURES / "facility_confirmed.yaml"), complete_cfg)


def _variant(cfg: SiteConfig, update: dict) -> SiteConfig:
    """A copy of the config with top-level or nested (one level) fields replaced."""
    data = cfg.model_dump()
    for key, value in update.items():
        data[key] = {**data[key], **value} if isinstance(value, dict) else value
    return SiteConfig.model_validate(data)


def _guide_file(tmp_path: Path, slug: str, **meta: object) -> Path:
    base = {"title": "A Guide", "description": "What it covers.", "date": "2026-09-29", "summary": "The short answer."}
    base.update(meta)
    path = tmp_path / f"{slug}.md"
    path.write_text("---\n" + yaml.safe_dump(base) + "---\n## First part\n\nBody [link](/faq/).\n", encoding="utf-8")
    return path


# config ---------------------------------------------------------------------

def test_placeholders_are_detected_and_displayed_without_marker():
    assert is_placeholder("TO_FILL Your Name") and not is_placeholder("Sam") and not is_placeholder(3)
    assert display_value("TO_FILL Your Name") == "Your Name"
    assert display_value("TO_FILL") == "to fill"


def test_complete_config_is_ready_to_publish(complete_cfg):
    assert publish_problems(complete_cfg) == []
    assert complete_cfg.base_url == "https://openline.test"
    assert complete_cfg.short_name == "Open Line"
    assert "Open Line Co-Packing" in repr(complete_cfg)


def test_placeholder_config_lists_every_problem(placeholder_cfg):
    problems = publish_problems(placeholder_cfg)
    for field in ("domain", "contact.name", "contact.email", "contact.phone", "contact.linkedin", "author_bio"):
        assert f"{field} is a placeholder" in problems
    assert not any("address" in problem for problem in problems)


@pytest.mark.parametrize("update, expected", [
    ({"domain": "http://openline.test"}, "domain must start with https://"),
    ({"domain": "https://www.example.com"}, "domain is an example domain"),
    ({"contact": {"name": "Sam", "email": "not-an-email"}}, "contact.email is not an email address"),
    ({"contact": {"name": " ", "email": "sam@openline.test"}}, "contact.name is empty"),
    ({"form": {"provider": "formspree", "action": ""}}, "form.action must be the https Formspree endpoint when provider is formspree"),
])
def test_publish_problems_catch_bad_values(complete_cfg, update, expected):
    assert expected in publish_problems(_variant(complete_cfg, update))


def test_capacity_status_label_age_and_validation():
    status = CapacityStatus(as_of="2026-09", lines=["cookie"])
    assert status.label() == "September 2026"
    assert status.age_days(date(2026, 10, 16)) == 45
    assert "2026-09" in repr(status)
    with pytest.raises(ValueError):
        CapacityStatus(as_of="September 2026")


def test_load_site_config_wraps_validation_errors(tmp_path):
    bad = tmp_path / "config.yaml"
    bad.write_text("brand: Only a brand\n", encoding="utf-8")
    with pytest.raises(SiteConfigError):
        load_site_config(bad)


def test_unknown_lines_flags_lines_the_facility_does_not_run(complete_cfg):
    cfg = complete_cfg.model_copy(update={"capacity": CapacityStatus(as_of="2026-09", lines=["cookie", "candy"])})
    assert unknown_lines(cfg, ["cookie", "bakery"]) == ["candy"]


def test_repo_site_config_loads():
    cfg = load_site_config(REPO / "site" / "config.yaml")
    assert cfg.brand and cfg.capacity.lines


# facts ----------------------------------------------------------------------

def test_unconfirmed_facility_yields_lines_and_services_only(open_facts):
    assert [line.label for line in open_facts.open_lines] == ["Cookies", "Baked goods", "Pet treats", "Pet food"]
    assert len(open_facts.services) == 7
    assert open_facts.certifications == [] and open_facts.numbers == []
    assert open_facts.location == "" and open_facts.ships_nationwide is False
    assert open_facts.value("commercial.min_order_units") is None
    assert open_facts.open_line_labels() == "Cookies, baked goods, pet treats, and pet food"
    assert "lines=4" in repr(open_facts)


def test_confirmed_facility_yields_certifications_numbers_and_location(confirmed_facts):
    assert confirmed_facts.certifications == ["FDA-registered facility", "SQF Level 2", "Kosher (OU)"]
    labels = {fact.label: fact.value for fact in confirmed_facts.numbers}
    assert labels["Minimum run"] == "5,000 units"
    assert labels["Benchmark sample"] == "about 10 days"
    assert confirmed_facts.location == "Springfield, IL" and confirmed_facts.ships_nationwide is True


def test_lines_closed_this_month_are_marked_not_open(complete_cfg):
    cfg = complete_cfg.model_copy(update={"capacity": CapacityStatus(as_of="2026-09", lines=["cookie", "pet_treat"])})
    facts = build_facts(load_facility(FIXTURES / "facility_unconfirmed.yaml"), cfg)
    assert [line.key for line in facts.open_lines] == ["cookie", "pet_treat"]
    assert facts.open_line_labels() == "Cookies and pet treats"
    assert not next(line for line in facts.lines if line.key == "bakery").open


# content --------------------------------------------------------------------

def test_split_front_matter_requires_a_mapping_block():
    meta, body = split_front_matter("---\ntitle: X\n---\nBody\n")
    assert meta == {"title": "X"} and body == "Body\n"
    with pytest.raises(ContentError):
        split_front_matter("no front matter")
    with pytest.raises(ContentError):
        split_front_matter("---\n- a list\n---\nBody\n")


def test_render_markdown_prefixes_ids_and_lists_h2s():
    html, toc = render_markdown("## It's \"quoted\"\n\ntext\n\n### Sub\n\n## Second", "guide-x--")
    assert 'id="guide-x--its-quoted"' in html and "&rsquo;" in html
    assert [(entry.anchor, entry.text) for entry in toc] == [("guide-x--its-quoted", "It’s “quoted”"), ("guide-x--second", "Second")]


def test_load_guide_parses_front_matter(tmp_path):
    guide = load_guide(_guide_file(tmp_path, "sample", title="Refrigerated to Shelf-Stable: A Title (Long)",
                                   category="cookie-co-packer", related=["other"],
                                   sources=[{"title": "FDA", "url": "https://www.fda.gov/"}]))
    assert guide.slug == "sample" and guide.category == "cookie-co-packer"
    assert guide.short_title == "Refrigerated to Shelf-Stable"
    assert guide.updated == guide.published == date(2026, 9, 29)
    assert guide.sources[0]["url"] == "https://www.fda.gov/"
    assert guide.reading_minutes == 1 and guide.word_count > 5
    assert "Guide(slug='sample'" in repr(guide)


@pytest.mark.parametrize("meta, message", [
    ({"summary": ""}, "missing summary"),
    ({"category": "candy"}, "category must be one of"),
    ({"date": "Sept 29"}, "date must be YYYY-MM-DD"),
])
def test_load_guide_rejects_bad_front_matter(tmp_path, meta, message):
    with pytest.raises(ContentError, match=message):
        load_guide(_guide_file(tmp_path, "bad", **meta))


def test_load_guides_sorts_newest_first_and_checks_related(tmp_path):
    _guide_file(tmp_path, "older", date="2026-01-01", related=["newer"])
    _guide_file(tmp_path, "newer", date="2026-06-01")
    assert [guide.slug for guide in load_guides(tmp_path)] == ["newer", "older"]
    _guide_file(tmp_path, "broken", related=["missing"])
    with pytest.raises(ContentError, match="related guides not found: missing"):
        load_guides(tmp_path)


def test_answers_switch_to_confirmed_numbers(open_facts, confirmed_facts):
    item = {"q": "Minimum?", "a": "Confirmed per product.",
            "when_confirmed": {"field": "commercial.min_order_units", "a": "From {value} units."}}
    assert resolve_answer(item, open_facts) == "Confirmed per product."
    assert resolve_answer(item, confirmed_facts) == "From 5,000 units."
    assert fill_tokens("Reply within {reply_within}.", {"reply_within": "a day"}) == "Reply within a day."


def test_load_faq_and_categories_validate_required_fields(tmp_path, open_facts):
    faq = tmp_path / "faq.yaml"
    faq.write_text(yaml.safe_dump([{"q": "Only a question"}]), encoding="utf-8")
    with pytest.raises(ContentError, match="needs q and a"):
        load_faq(faq, open_facts)
    categories = tmp_path / "categories.yaml"
    categories.write_text(yaml.safe_dump({"cookie-co-packer": {"line": "cookie"}}), encoding="utf-8")
    with pytest.raises(ContentError, match="needs h1"):
        load_categories(categories, open_facts)


def test_repo_content_loads_and_resolves(open_facts):
    content = REPO / "site" / "content"
    guides = load_guides(content / "guides")
    faq = load_faq(content / "faq.yaml", open_facts, {"reply_within": "one business day"})
    categories = load_categories(content / "categories.yaml", open_facts)
    assert len(guides) >= 8 and len(faq) >= 15 and set(categories) >= {"cookie-co-packer", "dog-treat-co-packer"}
    assert all("{" not in item.answer for item in faq)
    assert sum(item.featured for item in faq) >= 3
    for guide in guides:
        assert 40 <= len(guide.summary.split()) <= 90, guide.slug
        assert len(guide.description) <= 160, guide.slug


# render ---------------------------------------------------------------------

def test_urls_follow_the_build_mode(complete_cfg, open_facts, tmp_path):
    production = SiteContext(complete_cfg, open_facts, "production", date(2026, 9, 29), tmp_path)
    preview = SiteContext(complete_cfg, open_facts, "preview", date(2026, 9, 29), tmp_path)
    assert production.url("") == "/" and production.url("faq") == "/faq/"
    assert production.url("", "capacity") == "/#capacity"
    assert production.abs_url("guides/x") == "https://openline.test/guides/x/"
    assert preview.url("") == "#home" and preview.url("guides/x") == "#guide-x"
    assert preview.url("", "capacity") == "#capacity" and preview.url("faq", "capacity") == "#faq--capacity"
    assert production.draft is False and preview.draft is True and preview.preview is True
    assert "mode='preview'" in repr(preview)
    with pytest.raises(ValueError):
        SiteContext(complete_cfg, open_facts, "staging", date(2026, 9, 29), tmp_path)


def test_field_highlights_placeholders_and_escapes_values(placeholder_cfg, open_facts, tmp_path):
    site = SiteContext(placeholder_cfg, open_facts, "draft", date(2026, 9, 29), tmp_path)
    assert str(site.field("TO_FILL Your Name")).startswith('<mark class="todo"')
    assert str(site.field("<b>")) == "&lt;b&gt;"
    assert site.real("TO_FILL x") == "" and site.real("Sam") == "Sam"
    assert site.tel("TO_FILL (555) 010-0000") == ""
    assert site.tel("(555) 010-2030") == "tel:+15550102030" and site.tel("12") == ""
    assert site.brand_rest == "Co-Packing"
    assert site.og_image("og/missing.png") == "og/default.png"


def test_markdown_links_follow_the_build_mode(complete_cfg, open_facts, tmp_path):
    html = '<a href="/guides/x/">x</a> <a href="/faq/#minimums">m</a> <a href="/">home</a> <a href="https://fda.gov/">f</a>'
    preview = SiteContext(complete_cfg, open_facts, "preview", date(2026, 9, 29), tmp_path)
    production = SiteContext(complete_cfg, open_facts, "production", date(2026, 9, 29), tmp_path)
    assert rewrite_internal_links(html, preview) == (
        '<a href="#guide-x">x</a> <a href="#faq--minimums">m</a> <a href="#home">home</a> <a href="https://fda.gov/">f</a>')
    assert rewrite_internal_links(html, production) == html


def test_hyphenated_words_are_kept_together():
    assert str(keep_hyphenated("Find a Co-Packer & more")) == 'Find a <span class="nw">Co-Packer</span> &amp; more'


# seo ------------------------------------------------------------------------

def test_structured_data_drops_placeholders(placeholder_cfg):
    cfg = _variant(placeholder_cfg, {"domain": "https://draft.invalid"})  # what draft builds substitute
    node = seo.organization_node(cfg)
    assert "email" not in node and "telephone" not in node and "sameAs" not in node
    assert node["contactPoint"]["contactType"] == "sales"
    assert "TO_FILL" not in json.dumps(seo.person_node(cfg))


def test_article_node_cites_sources(complete_cfg, tmp_path):
    guide = load_guide(_guide_file(tmp_path, "g", sources=[{"title": "eCFR", "url": "https://www.ecfr.gov/"}]))
    node = seo.article_node(complete_cfg, guide, "https://openline.test/guides/g/", "https://openline.test/og/default.png")
    assert node["citation"] == ["https://www.ecfr.gov/"]
    assert node["author"] == {"@id": "https://openline.test/about/#author"}
    assert node["datePublished"] == "2026-09-29"


def test_sitemap_robots_and_headers(complete_cfg):
    sitemap = seo.render_sitemap([("https://openline.test/", date(2026, 9, 29)), ("https://openline.test/faq/", None)])
    assert "<lastmod>2026-09-29</lastmod>" in sitemap and "<loc>https://openline.test/faq/</loc></url>" in sitemap
    assert "Disallow: /\n" in seo.render_robots(complete_cfg, draft=True)
    assert "Sitemap: https://openline.test/sitemap.xml" in seo.render_robots(complete_cfg, draft=False)
    assert "X-Robots-Tag" in seo.render_headers(complete_cfg, draft=True)
    assert "X-Robots-Tag" not in seo.render_headers(complete_cfg, draft=False)


def test_csp_allows_only_configured_analytics_and_form_hosts(complete_cfg):
    strict = seo.content_security_policy(complete_cfg)
    assert "script-src 'self';" in strict and "form-action 'self';" in strict and "frame-ancestors 'none'" in strict
    snippet = ('<script defer data-domain="openline.test" src="https://plausible.io/js/script.js"></script>'
               '<script>window.plausible = window.plausible || function () {};</script>')
    cfg = complete_cfg.model_copy(update={"analytics_snippet": snippet, "analytics_hosts": ["stats.example.net"],
                                          "form": complete_cfg.form.model_copy(update={"provider": "formspree", "action": "https://formspree.io/f/abc"})})
    policy = seo.content_security_policy(cfg)
    assert "script-src 'self' https://plausible.io https://stats.example.net 'sha256-" in policy
    assert "connect-src 'self' https://plausible.io https://stats.example.net;" in policy
    assert "form-action 'self' https://formspree.io;" in policy


def test_llms_files_state_confirmed_facts_only(complete_cfg, open_facts, confirmed_facts, tmp_path):
    guide = load_guide(_guide_file(tmp_path, "g"))
    open_text = seo.render_llms_txt(complete_cfg, open_facts, [guide], [("FAQ", "faq/", "questions")])
    assert open_text.startswith("# Open Line Co-Packing\n\n> ")
    assert "Minimums and lead times: confirmed per product" in open_text
    assert "- [A Guide](https://openline.test/guides/g/): The short answer." in open_text
    assert "- Minimum run: 5,000 units" in seo.render_llms_txt(complete_cfg, confirmed_facts, [guide], [])
    full = seo.render_llms_full(complete_cfg, open_facts, [guide], [FaqItem("Q?", "A.")])
    assert "### Q?\n\nA." in full and "Short answer: The short answer." in full
