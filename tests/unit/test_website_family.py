"""Unit tests for the site family: merged configs, per-site content selection, questionnaires, and home copy."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

from leadgen.facility import load_facility
from leadgen.website.config import (
    FamilyMember,
    SiteConfigError,
    load_family,
    load_site,
    merge,
    publish_problems,
    site_ids,
)
from leadgen.website.content import ContentError, load_faq, load_guide, pick, select_guides
from leadgen.website.facts import build_facts
from leadgen.website.forms import field_names, load_form, load_home
from leadgen.website.render import SiteContext

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "website"
REPO = Path(__file__).resolve().parents[2]
TODAY = date(2026, 9, 29)


def _write(path: Path, data: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


@pytest.fixture
def family_dir(tmp_path: Path) -> Path:
    """A two-site family: shared settings from the complete fixture, each site with its own brand and domain."""
    shared = yaml.safe_load((FIXTURES / "site_complete.yaml").read_text(encoding="utf-8"))
    _write(tmp_path / "shared.yaml", shared | {"sites": ["one", "two"]})
    _write(tmp_path / "sites" / "one" / "site.yaml", {"brand": "Open Line One", "domain": "https://one.test",
                                                     "lines": ["cookie"], "guides": ["a", "b"], "family_blurb": "Cookies"})
    _write(tmp_path / "sites" / "two" / "site.yaml", {"brand": "Open Line Two", "domain": "TO_FILL https://two.test",
                                                     "contact": {"email": "two@two.test"}, "guides": ["b"]})
    return tmp_path


def _guide(tmp_path: Path, slug: str, related: list[str]) -> Path:
    meta = {"title": slug.upper(), "description": "d", "date": "2026-09-29", "summary": "s", "related": related}
    path = tmp_path / "guides" / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + yaml.safe_dump(meta) + "---\nBody.\n", encoding="utf-8")
    return path


# config ---------------------------------------------------------------------

def test_merge_is_deep_and_the_override_wins():
    base = {"a": 1, "contact": {"name": "Sam", "email": "s@x.test"}, "lines": [1]}
    assert merge(base, {"contact": {"email": "t@x.test"}, "lines": [2]}) == {
        "a": 1, "contact": {"name": "Sam", "email": "t@x.test"}, "lines": [2]}
    assert base["contact"]["email"] == "s@x.test"


def test_family_loads_in_order_with_siblings(family_dir):
    one, two = load_family(family_dir)
    assert (one.id, two.id) == ("one", "two")
    assert one.contact.name == "Sam Rivera" and two.contact.email == "two@two.test" and two.contact.name == "Sam Rivera"
    assert [member.id for member in one.family] == ["two"] and one.family_order_ids == ["one", "two"]
    assert [member.id for member in two.family_order()] == ["one", "two"]
    assert repr(one.family[0]) == "FamilyMember(id='two')" and "id='one'" in repr(one)


def test_sibling_placeholders_do_not_block_a_publishable_site(family_dir):
    one, two = load_family(family_dir)
    assert publish_problems(one) == []
    assert publish_problems(two) == ["domain is a placeholder"]


def test_unknown_or_missing_sites_are_config_errors(family_dir):
    assert site_ids(family_dir) == ["one", "two"]
    with pytest.raises(SiteConfigError, match="choose one of one, two"):
        load_site(family_dir, "three")
    _write(family_dir / "shared.yaml", {"sites": ["one", "Bad Id", "missing"]})
    with pytest.raises(SiteConfigError, match="Bad Id, missing"):
        site_ids(family_dir)
    _write(family_dir / "shared.yaml", {"sites": []})
    with pytest.raises(SiteConfigError, match="none listed"):
        site_ids(family_dir)


def test_site_files_must_be_valid_mappings(family_dir):
    (family_dir / "sites" / "two" / "site.yaml").write_text("- a list\n", encoding="utf-8")
    with pytest.raises(SiteConfigError, match="must be a mapping"):
        load_family(family_dir)
    _write(family_dir / "sites" / "two" / "site.yaml", {"brand": "Two", "domain": "https://two.test",
                                                         "capacity": {"as_of": "September"}})
    with pytest.raises(SiteConfigError, match="as_of"):
        load_family(family_dir)


def test_site_lines_limit_the_facts(family_dir):
    one, two = load_family(family_dir)
    facility = load_facility(FIXTURES / "facility_unconfirmed.yaml")
    assert [line.key for line in build_facts(facility, one).lines] == ["cookie"]
    assert len(build_facts(facility, two).lines) == 4


# content --------------------------------------------------------------------

def test_pick_keeps_the_site_order_and_names_missing_entries():
    available = {"a": 1, "b": 2, "c": 3}
    assert pick(available, None, "x") is available
    assert list(pick(available, ["c", "a"], "x")) == ["c", "a"]
    with pytest.raises(ContentError, match="not found: z"):
        pick(available, ["a", "z"], "x")


def test_select_guides_drops_related_links_outside_the_site(tmp_path):
    guides = [load_guide(_guide(tmp_path, slug, related)) for slug, related in
              (("a", ["b", "c"]), ("b", ["a"]), ("c", ["a"]))]
    chosen = select_guides(guides, ["a", "b"])
    assert [guide.slug for guide in chosen] == ["a", "b"] and chosen[0].related == ["b"]
    assert select_guides(guides, None) is guides


def test_faq_items_can_be_limited_to_sites(tmp_path, family_dir):
    cfg = load_site(family_dir, "one")
    facts = build_facts(load_facility(FIXTURES / "facility_unconfirmed.yaml"), cfg)
    path = _write(tmp_path / "faq.yaml", [{"q": "Everyone?", "a": "Yes."}, {"q": "Pets?", "a": "Yes.", "sites": ["pet"]}])
    assert [item.question for item in load_faq(path, facts, None, "one")] == ["Everyone?"]
    assert [item.question for item in load_faq(path, facts, None, "pet")] == ["Everyone?", "Pets?"]
    assert len(load_faq(path, facts)) == 2


# render ---------------------------------------------------------------------

def test_shared_guides_have_one_canonical_home(family_dir, tmp_path):
    one, two = load_family(family_dir)
    facts = build_facts(load_facility(FIXTURES / "facility_unconfirmed.yaml"), two)
    later = SiteContext(two, facts, "production", TODAY, tmp_path)
    first = SiteContext(one, facts, "production", TODAY, tmp_path)
    assert later.guide_home("b") == "https://one.test/guides/b/" and later.guide_home("zzz") == ""
    assert first.guide_home("b") == ""
    waiting = one.model_copy(update={"domain": "TO_FILL https://one.test"})
    member = FamilyMember(id="one", brand="One", domain=waiting.domain, guides=["b"])
    assert SiteContext(two.model_copy(update={"family": [member]}), facts, "production", TODAY, tmp_path).guide_home("b") == ""
    assert [m.id for m in first.live_siblings()] == [] and [m.id for m in later.live_siblings()] == ["one"]


def test_line_links_use_the_site_page_for_that_line(family_dir, tmp_path):
    cfg = load_site(family_dir, "one")
    site = SiteContext(cfg, build_facts(load_facility(FIXTURES / "facility_unconfirmed.yaml"), cfg), "production", TODAY, tmp_path)
    site.categories = {"cookie-recipe-development": {"line": "cookie"}}
    assert site.category_for("cookie")[0] == "cookie-recipe-development" and site.category_for("pet_food") is None
    assert site.line_url("cookie") == "/cookie-recipe-development/" and site.line_url("pet_food") == "/capabilities/"


# forms ----------------------------------------------------------------------

FORM = {
    "title": "Check capacity", "intro": "Intro.", "summary": "Two questions", "kicker": "Check",
    "submit": "Send", "steps": ["We reply within {reply_within}."],
    "fields": [{"name": "product", "label": "What?"},
               {"name": "volume", "label": "How many?", "type": "select", "options": ["Few", "Many"]}],
    "fit": {"title": "Fit", "fields": [{"name": "allergens", "label": "Allergens", "type": "checkboxes",
                                        "options": ["Peanuts", "None"], "required": True}]},
}


def test_load_form_fills_defaults_and_tokens(tmp_path):
    form = load_form(_write(tmp_path / "form.yaml", FORM), {"reply_within": "a day"})
    assert form["steps"] == ["We reply within a day."]
    product, volume = form["fields"]
    assert product["type"] == "text" and product["required"] and not product["wide"]
    assert volume["options"] == ["Few", "Many"]
    allergens = form["fit"]["fields"][0]
    assert allergens["wide"] and not allergens["required"]  # checkbox groups are never required
    assert field_names(form)[:3] == ["product", "volume", "allergens"] and field_names(form)[-1] == "site"


@pytest.mark.parametrize("change, message", [
    ({"title": ""}, "missing title"),
    ({"fields": [{"name": "volume", "label": "V"}]}, "must include a field named product"),
    ({"fields": [{"name": "email", "label": "E"}]}, "field name 'email'"),
    ({"fields": [{"name": "product", "label": "P", "type": "slider"}]}, "type must be one of"),
    ({"fields": [{"name": "product"}]}, "needs a label"),
    ({"fields": [{"name": "product", "label": "P", "type": "radio", "options": ["one"]}]}, "at least two options"),
    ({"fields": [{"name": "product", "label": "P"}, {"name": "product", "label": "Q"}]}, "duplicate field names: product"),
    ({"fit": {"fields": [{"name": "product", "label": "P"}]}}, "fields asked twice: product"),
])
def test_load_form_rejects_broken_questionnaires(tmp_path, change, message):
    with pytest.raises(ContentError, match=message):
        load_form(_write(tmp_path / "form.yaml", FORM | change))


def test_load_home_requires_the_sections(tmp_path):
    home = {"kicker": "K", "h1": "H", "lead": "L", "trust": "T within {reply_within}", "who_title": "W", "who_text": "WT",
            "who": [{"title": "a", "text": "b"}], "steps_title": "S", "steps": [{"title": "a", "text": "within {reply_within}"}],
            "lines_title": "Lines"}
    loaded = load_home(_write(tmp_path / "home.yaml", home), {"reply_within": "a day"})
    assert loaded["steps"][0]["text"] == "within a day" and loaded["trust"] == "T within a day"
    with pytest.raises(ContentError, match="missing lines_title"):
        load_home(_write(tmp_path / "home.yaml", home | {"lines_title": ""}))
    with pytest.raises(ContentError, match=r"who items \[1\]"):
        load_home(_write(tmp_path / "home.yaml", home | {"who": [{"title": "only"}]}))


def test_every_repo_site_has_a_valid_form_and_home():
    for site_id in site_ids(REPO / "site"):
        own = REPO / "site" / "sites" / site_id
        form = load_form(own / "form.yaml", {"reply_within": "one business day"})
        home = load_home(own / "home.yaml", {"reply_within": "one business day"})
        assert "product" in field_names(form) and home["h1"], site_id


def test_home_product_lines_are_checked(tmp_path):
    home = {"kicker": "K", "h1": "H", "lead": "L", "trust": "T", "who_title": "W", "who_text": "WT",
            "who": [{"title": "a", "text": "b"}], "steps_title": "S", "steps": [{"title": "a", "text": "b"}],
            "lines_title": "Lines", "skus": {"title": "Bring the line", "lines": [{"name": "Range", "items": ["A", "B"]}]}}
    assert load_home(_write(tmp_path / "home.yaml", home))["skus"]["lines"][0]["items"] == ["A", "B"]
    with pytest.raises(ContentError, match="skus needs title and lines"):
        load_home(_write(tmp_path / "home.yaml", home | {"skus": {"title": "No lines"}}))
    with pytest.raises(ContentError, match=r"skus lines \[1\] need a name and at least two items"):
        load_home(_write(tmp_path / "home.yaml", home | {"skus": {"title": "T", "lines": [{"name": "One", "items": ["A"]}]}}))
