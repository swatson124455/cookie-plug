"""Unit tests for leadgen.facility."""

from leadgen.facility import FacilityProfile, load_facility
from leadgen.models import Category


def test_load_facility_reads_categories(facility):
    assert facility.supports(Category.COOKIE)
    assert facility.supports(Category.PET_FOOD)
    assert not facility.supports(Category.SNACK)


def test_unconfirmed_fields_flags_placeholders(facility):
    pending = facility.unconfirmed_fields()
    assert "certifications.sqf" in pending
    assert "commercial.min_order_units" in pending
    assert "commercial.spare_capacity_pct" not in pending
    assert "name" in pending


def test_confirmed_certifications_excludes_placeholders(facility):
    assert facility.confirmed_certifications() == []
    assert "certifications.fda_registered" in facility.unconfirmed_fields()
    assert "location.ships_nationwide" in facility.unconfirmed_fields()


def test_confirmed_certifications_includes_string_values():
    profile = FacilityProfile(
        name="Real Plant", categories=[Category.COOKIE],
        certifications={"sqf": "SQF Level 2", "organic": "TO_CONFIRM", "kosher": False},
        commercial={"spare_capacity_pct": 40, "min_order_units": 5000},
    )
    assert profile.confirmed_certifications() == ["sqf: SQF Level 2"]
    assert profile.unconfirmed_fields() == ["certifications.organic"]
    assert profile.spare_capacity_pct() == 40
    assert "Real Plant" in repr(profile)


def test_load_facility_tolerates_empty_file(tmp_path):
    path = tmp_path / "f.yaml"
    path.write_text("", encoding="utf-8")
    profile = load_facility(path)
    assert profile.name == "Partner Facility"
    assert profile.categories == []
