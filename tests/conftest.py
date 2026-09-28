"""Shared fixtures. Everything here is offline and deterministic."""

from __future__ import annotations

from pathlib import Path

import pytest

from leadgen.facility import FacilityProfile, load_facility
from leadgen.models import Category, Lead, LeadSignals, Segment
from leadgen.outreach import SenderIdentity, SequenceTemplate, load_sequence
from leadgen.scoring import IcpWeights, load_weights

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session")
def facility() -> FacilityProfile:
    return load_facility(REPO_ROOT / "config" / "facility.yaml")


@pytest.fixture(scope="session")
def weights() -> IcpWeights:
    return load_weights(REPO_ROOT / "config" / "icp.yaml")


@pytest.fixture(scope="session")
def sequence_template() -> SequenceTemplate:
    return load_sequence(REPO_ROOT / "config" / "templates" / "sequence.yaml")


@pytest.fixture
def sender() -> SenderIdentity:
    return SenderIdentity(name="Sam Watson", title="Partnerships")


@pytest.fixture
def strong_lead() -> Lead:
    """An established cookie brand with clear capacity triggers."""
    return Lead(
        company="Crumb Co",
        website="https://www.crumbco.com",
        category=Category.COOKIE,
        segment=Segment.ESTABLISHED_BRAND,
        contact_name="Jordan Lee",
        contact_title="Founder",
        email="jordan@crumbco.com",
        signals=LeadSignals(
            is_shopify=True,
            sells_wholesale=True,
            in_national_retail=True,
            retailers_mentioned=["whole foods"],
            out_of_stock=True,
            product_count=24,
        ),
    )


@pytest.fixture
def weak_lead() -> Lead:
    """A tiny brand in an unrelated category with no signals."""
    return Lead(company="Sauce Bros", website="saucebros.com", category=Category.OTHER)


@pytest.fixture
def shopify_html() -> str:
    return (FIXTURES / "homepage_shopify.html").read_text(encoding="utf-8")


@pytest.fixture
def sample_csv() -> Path:
    return FIXTURES / "sample_leads.csv"
