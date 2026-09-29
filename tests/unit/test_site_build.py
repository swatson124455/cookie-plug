"""Tests for the static site build."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("site_build", REPO / "site" / "build.py")
site_build = importlib.util.module_from_spec(spec)
sys.modules["site_build"] = site_build
spec.loader.exec_module(site_build)


@pytest.fixture
def built(tmp_path, facility):
    cfg = site_build.load_site_config()
    cfg["domain"] = "https://test.example"
    cfg["contact"]["email"] = "sam@test.example"
    paths = site_build.build(cfg=cfg, facility=facility, dist=tmp_path / "dist")
    return tmp_path / "dist", paths, cfg


def test_build_writes_all_pages_and_static_files(built):
    dist, paths, _ = built
    assert "" in paths and "capabilities" in paths and "faq" in paths and "contact" in paths
    assert "cookie-co-packer" in paths and "dog-treat-co-packer" in paths
    assert any(p.startswith("guides/") for p in paths)
    for name in ("index.html", "styles.css", "llms.txt", "robots.txt", "sitemap.xml"):
        assert (dist / name).exists()
    assert (dist / "guides" / "how-to-find-a-cookie-co-packer" / "index.html").exists()


def test_no_unconfirmed_claims_reach_pages(built):
    dist, _, _ = built
    for page in dist.rglob("*.html"):
        assert "TO_CONFIRM" not in page.read_text(encoding="utf-8"), page


def test_capabilities_lists_only_confirmed_certifications(built, facility):
    dist, _, _ = built
    text = (dist / "capabilities" / "index.html").read_text(encoding="utf-8")
    assert "FDA registered" in text
    assert "SQF" not in text  # still TO_CONFIRM in config/facility.yaml


def test_structured_data_is_valid_json(built):
    dist, _, cfg = built
    home = (dist / "index.html").read_text(encoding="utf-8")
    faq = (dist / "faq" / "index.html").read_text(encoding="utf-8")
    assert '"@type": "Organization"' in home and '"@type": "Service"' in home
    assert '"@type": "FAQPage"' in faq
    start = faq.index('{"@context": "https://schema.org", "@type": "FAQPage"')
    end = faq.index("</script>", start)
    data = json.loads(faq[start:end])
    assert len(data["mainEntity"]) >= 10


def test_form_uses_netlify_by_default_and_formspree_when_set(built, facility, tmp_path):
    dist, _, cfg = built
    home = (dist / "index.html").read_text(encoding="utf-8")
    assert 'data-netlify="true"' in home and 'name="product"' in home
    cfg["form_action"] = "https://formspree.io/f/abc"
    site_build.build(cfg=cfg, facility=facility, dist=tmp_path / "dist2")
    home2 = (tmp_path / "dist2" / "index.html").read_text(encoding="utf-8")
    assert 'action="https://formspree.io/f/abc"' in home2 and "data-netlify" not in home2


def test_llms_and_sitemap_reference_domain(built):
    dist, paths, cfg = built
    llms = (dist / "llms.txt").read_text(encoding="utf-8")
    assert "https://test.example/guides/" in llms and "sam@test.example" in llms
    sitemap = (dist / "sitemap.xml").read_text(encoding="utf-8")
    assert sitemap.count("<url>") == len(paths)
    assert "https://test.example/faq/" in sitemap


def test_category_page_marks_unsupported_line(built, facility, tmp_path):
    from leadgen.facility import FacilityProfile
    from leadgen.models import Category

    _, _, cfg = built
    cookie_only = FacilityProfile(name="X", categories=[Category.COOKIE], services={"packaging": True})
    site_build.build(cfg=cfg, facility=cookie_only, dist=tmp_path / "dist3")
    pet = (tmp_path / "dist3" / "dog-treat-co-packer" / "index.html").read_text(encoding="utf-8")
    assert "we confirm line fit" in pet
    cookie = (tmp_path / "dist3" / "cookie-co-packer" / "index.html").read_text(encoding="utf-8")
    assert "Open capacity on this line now" in cookie


def test_guide_parsing():
    guide = site_build.parse_guide(REPO / "site" / "content" / "guides" / "co-packer-minimums-lead-times-and-costs.html")
    assert guide["title"].startswith("Co-Packer Minimums") and guide["slug"] == "co-packer-minimums-lead-times-and-costs"
    assert guide["body"].startswith("<p>")
