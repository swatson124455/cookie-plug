"""Unit tests for leadgen.htmlimport."""

from pathlib import Path

from leadgen.htmlimport import candidates_to_leads, extract_candidates, import_html_file
from leadgen.models import Category

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "exhibitors.html"


def test_extract_candidates_filters_and_dedupes():
    found = extract_candidates(FIXTURE.read_text(encoding="utf-8"))
    pairs = [(c.company, c.website) for c in found]
    assert ("Crumb Co", "https://crumbco.com") in pairs
    assert ("Barkery Lane", "https://barkerylane.com") in pairs
    assert ("Muffin Works", "https://muffinworks.com") in pairs
    domains = [c.website for c in found]
    assert domains.count("https://crumbco.com") == 1
    assert not any("instagram" in d or "expowest" in d or "thisshow" in d for d in domains)
    assert "HtmlCandidate" in repr(found[0])


def test_extra_skip_domain():
    found = extract_candidates(FIXTURE.read_text(encoding="utf-8"), extra_skip=("crumbco.com",))
    assert all("crumbco" not in c.website for c in found)


def test_import_html_file_builds_leads():
    leads = import_html_file(FIXTURE, source="expo_test", category=Category.COOKIE)
    assert len(leads) == 3 and all(l.source == "expo_test" and l.category == Category.COOKIE for l in leads)
    assert leads[0].domain == "crumbco.com"
    assert candidates_to_leads([], "x") == []
