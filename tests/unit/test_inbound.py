"""Unit tests for leadgen.inbound: website capacity-check submissions into the pipeline.

Netlify calls go through httpx.MockTransport with responses shaped like the
documented listSiteForms and listFormSubmissions operations.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

import httpx
import pytest

from leadgen import cli, inbound
from leadgen.crm import LeadStore
from leadgen.inbound import (
    FormSubmission,
    NetlifyError,
    fetch_netlify_submissions,
    filter_since,
    import_submissions,
    inbound_note,
    load_csv,
    parse_activity_detail,
    parse_company_field,
    parse_timestamp,
    submission_to_lead,
)
from leadgen.models import Category, Lead, LeadSignals, Segment, Stage
from leadgen.report import InboundEntry, build_report, render_report

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_CSV = REPO_ROOT / "tests" / "fixtures" / "netlify_capacity_check.csv"
TOKEN = "test-token-not-real"
UTC = timezone.utc


@pytest.fixture
def store(tmp_path: Path) -> Iterator[LeadStore]:
    """A fresh on-disk store per test."""
    with LeadStore(tmp_path / "inbound.sqlite3") as store:
        yield store


def _sub(**overrides: Any) -> FormSubmission:
    """A complete, valid submission; override any field."""
    values: dict[str, Any] = {
        "product": "Chewy molasses cookies", "volume": "5,000 to 25,000", "timing": "Within 3 months",
        "current_setup": "Home or shared kitchen", "name": "Maya Ortiz",
        "company": "Molasses & Co, molassesco.com", "email": "maya@molassesco.com",
        "source_page": "/guides/how-to-find-a-cookie-co-packer/", "form_name": "capacity-check",
        "submitted_at": "2026-09-25T14:22:05Z", "submission_id": "sub-1",
    }
    values.update(overrides)
    return FormSubmission(**values)


# --- keys, aliases, timestamps -------------------------------------------------


def test_from_mapping_normalizes_keys_and_ignores_unknown_ones():
    sub = FormSubmission.from_mapping({
        " Product ": "Oat cookies", "VOLUME": "Over 100,000", "Current Setup": "A co-packer",
        "current-setup": "ignored: the first non-empty value wins", "Bot-Field": "", "Form-Name": "capacity-check",
        "Source Page": "/guides/x/", "Website": "crumbco.com", "ID": "abc123",
        "Created at": "2026-10-03T09:22:05-05:00", "ip": "203.0.113.9", None: ["extra cell"],
    })
    assert (sub.product, sub.volume, sub.current_setup) == ("Oat cookies", "Over 100,000", "A co-packer")
    assert (sub.form_name, sub.source_page, sub.website, sub.bot_field) == ("capacity-check", "/guides/x/", "crumbco.com", "")
    assert sub.submission_id == "abc123"
    assert sub.submitted_at == datetime(2026, 10, 3, 14, 22, 5, tzinfo=UTC)
    assert repr(sub) == "FormSubmission(id='abc123', email='', company='')"


@pytest.mark.parametrize("key", ["created_at", "Created at", "date", "_date", "submitted", "Submitted At"])
def test_submitted_at_aliases(key: str):
    sub = FormSubmission.from_mapping({key: "2026-10-03T14:22:05.123Z"})
    assert sub.submitted_at == datetime(2026, 10, 3, 14, 22, 5, 123000, tzinfo=UTC)


@pytest.mark.parametrize("value, expected", [
    ("2026-10-03T09:22:05-05:00", datetime(2026, 10, 3, 14, 22, 5, tzinfo=UTC)),
    ("2026-10-03 14:22:05", datetime(2026, 10, 3, 14, 22, 5, tzinfo=UTC)),
    ("2026-10-03 14:22:05 UTC", datetime(2026, 10, 3, 14, 22, 5, tzinfo=UTC)),
    ("2026-10-03", datetime(2026, 10, 3, tzinfo=UTC)),
    (date(2026, 10, 3), datetime(2026, 10, 3, tzinfo=UTC)),
    (datetime(2026, 10, 3, 9, 30), datetime(2026, 10, 3, 9, 30, tzinfo=UTC)),
    ("", None), ("next Tuesday", None), (None, None),
])
def test_parse_timestamp_is_utc_aware(value: object, expected: datetime | None):
    parsed = parse_timestamp(value)
    assert parsed == expected
    assert parsed is None or parsed.utcoffset() == timedelta(0)


# --- company and website -------------------------------------------------------


@pytest.mark.parametrize("text, email, expected", [
    ("Crumb Co, crumbco.com", "jordan@crumbco.com", ("Crumb Co", "https://crumbco.com")),
    ("Crumb Co (https://www.CrumbCo.com/shop/cookies?ref=site)", "jordan@gmail.com", ("Crumb Co", "https://crumbco.com")),
    ("CRUMBCO.COM - Crumb Co", "jordan@icloud.com", ("Crumb Co", "https://crumbco.com")),
    ("Crumb Co | shop.crumbco.co.uk", "jordan@hotmail.com", ("Crumb Co", "https://shop.crumbco.co.uk")),
    ("Crumb Co", "Jordan@CrumbCo.com", ("Crumb Co", "https://crumbco.com")),
    ("Crumb Co", "jordan@gmail.com", ("Crumb Co", "")),
    ("crumbco.com", "jordan@gmail.com", ("Crumbco", "https://crumbco.com")),
    ("", "jordan@crumbco.com", ("Crumbco", "https://crumbco.com")),
    ("Crumb Co, instagram.com/crumbco", "jordan@yahoo.com", ("Crumb Co", "")),
    ("Crumb Co, jordan@crumbco.com", "jordan@gmail.com", ("Crumb Co", "")),
    ("St.Louis Cookie Co", "sam@gmail.com", ("St.Louis Cookie Co", "")),
    ("", "sam@gmail.com", ("", "")),
    ("", "not-an-email", ("", "")),
])
def test_parse_company_field(text: str, email: str, expected: tuple[str, str]):
    assert parse_company_field(text, email) == expected


def test_website_column_wins_and_matches_lead_domain():
    company, website = parse_company_field("Crumb Co, crumbco.com", "jordan@parentco.com", website="https://www.CrumbCookies.com/")
    assert (company, website) == ("Crumb Co", "https://crumbcookies.com")
    assert Lead(company=company, website=website).domain == "crumbcookies.com"
    assert parse_company_field("Crumb Co", "jordan@parentco.com", website="n/a") == ("Crumb Co", "https://parentco.com")


# --- submission to lead --------------------------------------------------------


def test_submission_to_lead_maps_fields_and_writes_one_note_line():
    lead = submission_to_lead(_sub(phone="512-555-0100", notes="Launching at\nCentral Market"))
    assert (lead.company, lead.website, lead.domain) == ("Molasses & Co", "https://molassesco.com", "molassesco.com")
    assert (lead.source, lead.stage, lead.tags) == ("inbound_website", Stage.NEW, ["inbound", "website"])
    assert (lead.contact_name, lead.email) == ("Maya Ortiz", "maya@molassesco.com")
    assert lead.category == Category.COOKIE and lead.signals.detected_categories == [Category.COOKIE]
    assert lead.notes == (
        "Inbound capacity check 2026-09-25 from /guides/how-to-find-a-cookie-co-packer/: "
        "product=Chewy molasses cookies; volume=5,000 to 25,000; timing=Within 3 months; "
        "setup=Home or shared kitchen; phone=512-555-0100; notes=Launching at Central Market"
    )


@pytest.mark.parametrize("setup, segment, transitioning", [
    ("Home or shared kitchen", Segment.EMERGING_BRAND, True),
    ("NOT IN PRODUCTION YET", Segment.EMERGING_BRAND, False),
    ("Our own facility", Segment.ESTABLISHED_BRAND, True),
    ("a  co-packer", Segment.ESTABLISHED_BRAND, True),
    ("Somewhere else", Segment.UNKNOWN, False),
    ("", Segment.UNKNOWN, False),
])
def test_segment_and_signals_follow_current_setup(setup: str, segment: Segment, transitioning: bool):
    lead = submission_to_lead(_sub(current_setup=setup))
    assert lead.segment == segment
    assert lead.signals.seeking_copacker is True
    assert lead.signals.transitioning is transitioning


def test_category_reads_product_and_notes():
    pet = submission_to_lead(_sub(product="Peanut butter biscuits", notes="our dog treats line"))
    assert pet.category == Category.PET_TREAT and pet.signals.detected_categories == [Category.PET_TREAT]
    sauce = submission_to_lead(_sub(product="Hot sauce"))
    assert sauce.category == Category.OTHER and sauce.signals.detected_categories == []


def test_note_leaves_out_empty_parts_and_the_honeypot():
    sparse = _sub(volume="", timing="", current_setup="", source_page="", submitted_at=None, bot_field="http://spam.example")
    assert inbound_note(sparse) == "Inbound capacity check: product=Chewy molasses cookies"
    empty = _sub(product="", volume="", timing="", current_setup="")
    assert inbound_note(empty) == "Inbound capacity check 2026-09-25 from /guides/how-to-find-a-cookie-co-packer/"


def test_submission_without_any_company_raises():
    with pytest.raises(ValueError, match="missing company"):
        submission_to_lead(_sub(company="", email="sam@gmail.com"))


# --- skipping and CSV loading -------------------------------------------------


def test_import_skips_spam_bad_email_other_forms_and_nameless(store: LeadStore):
    result = import_submissions(store, [
        _sub(bot_field="http://spam.example", submission_id="s1"),
        _sub(email="", submission_id="s2"),
        _sub(email="maya@@molassesco", submission_id="s3"),
        _sub(email="maya at molassesco.com", submission_id=""),
        _sub(form_name="newsletter", submission_id="s5"),
        _sub(company="", email="sam@gmail.com", submission_id="s6"),
    ])
    assert result.imported == [] and store.count() == 0
    assert result.skipped == [
        ("s1", "spam (honeypot)"), ("s2", "missing email"), ("s3", "invalid email"),
        ("maya at molassesco.com", "invalid email"), ("s5", "different form (newsletter)"), ("s6", "missing company"),
    ]
    assert repr(result) == "InboundImport(new=0, merged=0, skipped=6)"


def test_load_csv_fixture():
    subs = load_csv(FIXTURE_CSV)
    assert [s.submission_id[-3:] for s in subs] == ["601", "602", "603", "604", "605", "606"]
    first, spam, last = subs[0], subs[2], subs[-1]
    assert first.company == "Molasses & Co, molassesco.com" and first.form_name == "capacity-check"
    assert first.submitted_at == datetime(2026, 9, 25, 14, 22, 5, 123000, tzinfo=UTC)
    assert spam.bot_field == "http://rankco.example"
    assert last.notes == "Current co-packer raised minimums; need gluten-free.\nWhole Foods regional set in Q1"


def test_load_csv_tolerates_a_byte_order_mark(tmp_path: Path):
    path = tmp_path / "bom.csv"
    path.write_text("Product,Email,Company,Created at\nOat cookies,ann@crumbco.com,Crumb Co,2026-10-01\n", encoding="utf-8-sig")
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    [sub] = load_csv(path)
    assert (sub.product, sub.email, sub.company) == ("Oat cookies", "ann@crumbco.com", "Crumb Co")
    assert sub.submitted_at == datetime(2026, 10, 1, tzinfo=UTC)


def test_filter_since_keeps_undated_submissions():
    subs = [_sub(submitted_at="2026-09-20T23:59:59Z"), _sub(submitted_at="2026-09-21T00:00:00Z"), _sub(submitted_at=None)]
    kept = filter_since(subs, date(2026, 9, 21))
    assert [s.submitted_at for s in kept] == [datetime(2026, 9, 21, tzinfo=UTC), None]
    assert filter_since(subs, None) == subs


# --- dedupe and merge ------------------------------------------------------------


def _researched_lead() -> Lead:
    """A spear account that research already filled in."""
    return Lead(
        company="Molasses & Co", website="https://www.molassesco.com", category=Category.COOKIE,
        segment=Segment.ESTABLISHED_BRAND, contact_name="Jordan Lee", contact_title="Founder",
        email="jordan@molassesco.com", notes="Researched: in 40 Central Market stores", score=72,
        stage=Stage.CONTACTED, tags=["spear"], source="seed", signals=LeadSignals(in_national_retail=True),
    )


def test_merge_into_researched_lead_preserves_facts_and_is_idempotent(store: LeadStore):
    store.upsert(_researched_lead())
    first = import_submissions(store, [_sub()])
    assert [(i.status, i.lead.company, i.email) for i in first.imported] == [("merged", "Molasses & Co", "maya@molassesco.com")]
    lead = store.get("molassesco.com")
    assert (lead.contact_name, lead.contact_title, lead.email) == ("Jordan Lee", "Founder", "jordan@molassesco.com")
    assert (lead.score, lead.stage, lead.website) == (72, Stage.CONTACTED, "https://www.molassesco.com")
    assert (lead.category, lead.segment) == (Category.COOKIE, Segment.ESTABLISHED_BRAND)
    assert lead.notes.startswith("Researched: in 40 Central Market stores || Inbound capacity check 2026-09-25")
    assert lead.tags == ["spear", "inbound", "website"] and lead.source == "seed+inbound_website"
    assert lead.signals.seeking_copacker and lead.signals.transitioning and lead.signals.in_national_retail
    [activity] = store.activities("molassesco.com")
    detail = parse_activity_detail(activity["detail"])
    assert activity["kind"] == "inbound"
    assert detail["summary"] == "product=Chewy molasses cookies; volume=5,000 to 25,000"
    assert (detail["email"], detail["name"], detail["submission_id"]) == ("maya@molassesco.com", "Maya Ortiz", "sub-1")

    again = import_submissions(store, [_sub(), _sub(submission_id=""), _sub(submission_id="sub-1", product="Changed")])
    assert again.imported == []
    assert [reason for _, reason in again.skipped] == ["already imported"] * 3
    lead = store.get("molassesco.com")
    assert lead.notes.count("Inbound capacity check") == 1
    assert len(store.activities("molassesco.com")) == 1


def test_merge_fills_only_empty_contact_category_and_segment(store: LeadStore):
    store.upsert(Lead(company="Molasses & Co", website="molassesco.com", notes="from an expo list"))
    result = import_submissions(store, [_sub()])
    lead = store.get("molassesco.com")
    assert result.imported[0].status == "merged"
    assert (lead.contact_name, lead.email) == ("Maya Ortiz", "maya@molassesco.com")
    assert (lead.category, lead.segment) == (Category.COOKIE, Segment.EMERGING_BRAND)


def test_new_leads_and_lookup_by_company_name(store: LeadStore):
    store.upsert(Lead(company="Good Pup Bakery", notes="Reddit thread"))  # no website: stored under its name
    pup = _sub(product="Peanut butter dog biscuits", company="Good Pup Bakery", email="sam.goodpup@gmail.com",
               name="Sam Reyes", current_setup="Not in production yet", submission_id="sub-2")
    result = import_submissions(store, [_sub(), pup])
    assert [(i.lead.company, i.status) for i in result.imported] == [("Molasses & Co", "new"), ("Good Pup Bakery", "merged")]
    assert store.count() == 2
    new = store.get("molassesco.com")
    assert new.tags == ["inbound", "website"] and store.activities("molassesco.com")[0]["kind"] == "inbound"
    merged = store.get("good pup bakery")
    assert merged.website == "" and merged.email == "sam.goodpup@gmail.com" and merged.category == Category.PET_TREAT
    assert merged.notes.startswith("Reddit thread || Inbound capacity check")


def test_second_submission_from_a_new_company_merges_in_the_same_batch(store: LeadStore):
    other = _sub(product="Oatmeal cookies", name="Ana Diaz", email="ana@molassesco.com", submission_id="sub-9")
    result = import_submissions(store, [_sub(), other])
    assert [i.status for i in result.imported] == ["new", "merged"]
    lead = store.get("molassesco.com")
    assert lead.contact_name == "Maya Ortiz" and lead.notes.count("Inbound capacity check") == 2
    assert len(store.activities("molassesco.com")) == 2
    assert repr(result) == "InboundImport(new=1, merged=1, skipped=0)"
    assert repr(result.imported[1]) == "ImportedLead(company='Molasses & Co', status=merged)"


def test_identical_answers_from_a_second_person_log_an_activity_but_no_duplicate_note(store: LeadStore):
    result = import_submissions(store, [_sub(), _sub(name="Ana Diaz", email="ana@molassesco.com", submission_id="sub-2")])
    assert [i.status for i in result.imported] == ["new", "merged"]
    assert store.get("molassesco.com").notes.count("Inbound capacity check") == 1
    emails = [parse_activity_detail(a["detail"])["email"] for a in store.activities("molassesco.com")]
    assert emails == ["maya@molassesco.com", "ana@molassesco.com"]


def test_reimport_check_reads_idless_and_foreign_activities(store: LeadStore):
    store.log_activity("elsewhere.com", "inbound", '{"summary": "logged by hand"}')
    assert [i.status for i in import_submissions(store, [_sub(submission_id="")]).imported] == ["new"]
    again = import_submissions(store, [_sub(submission_id="")])
    assert again.skipped == [("maya@molassesco.com", "already imported")]


def test_parse_activity_detail_tolerates_foreign_details():
    assert parse_activity_detail("stage change, not JSON") == {}
    assert parse_activity_detail("[1, 2]") == {}
    assert parse_activity_detail('{"summary": "x", "n": 1}') == {"summary": "x", "n": "1"}


# --- Netlify API ----------------------------------------------------------------

FORMS = [
    {"id": "form-cap", "site_id": "site-1", "name": "capacity-check", "paths": ["/"], "submission_count": 3},
    {"id": "form-news", "site_id": "site-1", "name": "newsletter", "paths": ["/"], "submission_count": 9},
]


def _record(n: int, created_at: str) -> dict[str, Any]:
    """A submission shaped like the spec's ``submission`` definition."""
    data = {"product": f"Cookie {n}", "volume": "Now", "company": f"Brand {n}, brand{n}.com",
            "email": f"owner@brand{n}.com", "ip": "203.0.113.9", "user_agent": "Mozilla/5.0"}
    return {"id": f"sub-{n}", "number": n, "email": data["email"], "data": data,
            "created_at": created_at, "site_url": "https://example.netlify.app"}


def _netlify(pages: Callable[[int], list[dict[str, Any]]], forms: list[dict[str, Any]] | None = None) -> tuple[httpx.Client, list[httpx.Request]]:
    """A client whose transport serves the forms list and one form's pages; it records every request."""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        """Route like the documented listSiteForms and listFormSubmissions paths."""
        calls.append(request)
        assert request.headers["Authorization"] == f"Bearer {TOKEN}"
        if request.url.path == "/api/v1/sites/site-1/forms":
            return httpx.Response(200, json=FORMS if forms is None else forms)
        if request.url.path == "/api/v1/forms/form-cap/submissions":
            assert request.url.params["per_page"] == "100"
            return httpx.Response(200, json=pages(int(request.url.params["page"])))
        raise AssertionError(f"unexpected request to {request.url}")

    return httpx.Client(transport=httpx.MockTransport(handler)), calls


PAGES = {1: [_record(3, "2026-09-27T10:00:00Z"), _record(2, "2026-09-26T09:05:00.5Z")], 2: [_record(1, "2026-09-10T08:00:00Z")]}


def test_fetch_reads_only_the_named_form_across_pages():
    client, calls = _netlify(lambda page: PAGES.get(page, []))
    subs = fetch_netlify_submissions("site-1", TOKEN, client=client)
    assert [s.submission_id for s in subs] == ["sub-3", "sub-2", "sub-1"]
    assert (subs[0].product, subs[0].company, subs[0].email) == ("Cookie 3", "Brand 3, brand3.com", "owner@brand3.com")
    assert subs[0].submitted_at == datetime(2026, 9, 27, 10, tzinfo=UTC)
    assert [c.url.path for c in calls] == ["/api/v1/sites/site-1/forms"] + ["/api/v1/forms/form-cap/submissions"] * 3
    assert [c.url.params.get("page") for c in calls] == [None, "1", "2", "3"]
    assert not client.is_closed  # an injected client belongs to the caller


def test_fetch_applies_since_to_created_at():
    client, _ = _netlify(lambda page: PAGES.get(page, []))
    subs = fetch_netlify_submissions("site-1", TOKEN, since=date(2026, 9, 26), client=client)
    assert [s.submission_id for s in subs] == ["sub-3", "sub-2"]


def test_fetch_stops_when_the_server_repeats_a_page():
    client, calls = _netlify(lambda page: [_record(1, "2026-09-10T08:00:00Z")])
    assert [s.submission_id for s in fetch_netlify_submissions("site-1", TOKEN, client=client)] == ["sub-1"]
    assert len(calls) == 3  # forms, page 1, page 2 (all repeats, so stop)


def test_fetch_stops_at_the_page_cap(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(inbound, "NETLIFY_MAX_PAGES", 2)
    client, calls = _netlify(lambda page: [_record(page, "2026-09-20T08:00:00Z")])  # never runs dry
    assert [s.submission_id for s in fetch_netlify_submissions("site-1", TOKEN, client=client)] == ["sub-1", "sub-2"]
    assert len(calls) == 3


def test_fetch_builds_and_closes_its_own_client(monkeypatch: pytest.MonkeyPatch):
    client, _ = _netlify(lambda page: [])
    monkeypatch.setattr(inbound, "_netlify_client", lambda: client)
    assert fetch_netlify_submissions("site-1", TOKEN) == []
    assert client.is_closed


def test_default_client_has_a_timeout():
    client = inbound._netlify_client()
    assert client.timeout.read == inbound.NETLIFY_TIMEOUT_SECONDS
    client.close()


@pytest.mark.parametrize("status", [401, 404, 500])
def test_fetch_raises_on_non_2xx_without_the_token(status: int):
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(status, json={"message": TOKEN})))
    with pytest.raises(NetlifyError) as info:
        fetch_netlify_submissions("site-1", TOKEN, client=client)
    assert str(status) in str(info.value) and "/sites/site-1/forms" in str(info.value)
    assert TOKEN not in str(info.value) and TOKEN not in repr(info.value)
    assert isinstance(info.value, RuntimeError)


def test_fetch_raises_on_a_failed_page_and_bad_bodies():
    failing = httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, json=FORMS) if r.url.path.endswith("/forms") else httpx.Response(502)))
    with pytest.raises(NetlifyError, match="502 Bad Gateway for GET /forms/form-cap/submissions"):
        fetch_netlify_submissions("site-1", TOKEN, client=failing)
    for body in ({"text": "<html>maintenance</html>"}, {"json": {"forms": []}}):
        bad = httpx.Client(transport=httpx.MockTransport(lambda r, body=body: httpx.Response(200, **body)))
        with pytest.raises(NetlifyError, match="unexpected body"):
            fetch_netlify_submissions("site-1", TOKEN, client=bad)


def test_fetch_network_error_and_missing_form():
    def refuse(request: httpx.Request) -> httpx.Response:
        """Simulate a connection failure."""
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(NetlifyError, match="could not reach the Netlify API") as info:
        fetch_netlify_submissions("site-1", TOKEN, client=httpx.Client(transport=httpx.MockTransport(refuse)))
    assert TOKEN not in str(info.value)
    client, _ = _netlify(lambda page: [], forms=[{"id": "form-news", "name": "newsletter"}, "junk"])
    with pytest.raises(NetlifyError, match="no form named 'capacity-check' on this site \\(found: newsletter\\)"):
        fetch_netlify_submissions("site-1", TOKEN, client=client)


def test_error_message_redacts_a_token_that_leaked_into_the_path():
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(403)))
    with pytest.raises(NetlifyError) as info:
        fetch_netlify_submissions(TOKEN, TOKEN, client=client)
    assert TOKEN not in str(info.value) and "***" in str(info.value)


# --- CLI -------------------------------------------------------------------------


@pytest.fixture
def run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[..., int]:
    """Run the CLI against a temp database with no Netlify settings in the environment."""
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.delenv("NETLIFY_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("NETLIFY_SITE_ID", raising=False)
    db = str(tmp_path / "cli.sqlite3")

    def _run(*argv: str) -> int:
        """Invoke ``leadgen --db <tmp> ...``."""
        return cli.main(["--db", db, *argv])

    return _run


def test_cli_import_form_csv_then_reimport(run: Callable[..., int], capsys: pytest.CaptureFixture[str]):
    assert run("import-form", str(FIXTURE_CSV)) == 0
    out = capsys.readouterr().out
    assert "Molasses & Co maya@molassesco.com cookie emerging_brand (new)" in out
    assert "Good Pup Bakery sam.goodpup@gmail.com pet_treat emerging_brand (new)" in out
    assert "Proteincrumb lee@proteincrumb.com cookie established_brand (new)" in out
    assert "skipped 66f1c2e9a0b1c2d3e4f5a603: spam (honeypot)" in out
    assert "skipped 66f1c2e9a0b1c2d3e4f5a604: invalid email" in out
    assert "skipped 66f1c2e9a0b1c2d3e4f5a605: missing email" in out
    assert "import-form: 3 new, 0 merged, 3 skipped." in out
    assert run("import-form", str(FIXTURE_CSV)) == 0
    out = capsys.readouterr().out
    assert "import-form: 0 new, 0 merged, 6 skipped." in out and out.count("already imported") == 3
    assert run("list", "--tag", "inbound") == 0
    assert "Proteincrumb" in capsys.readouterr().out


def test_cli_import_form_since_filters_csv_rows(run: Callable[..., int], capsys: pytest.CaptureFixture[str]):
    assert run("import-form", str(FIXTURE_CSV), "--since", "2026-09-26") == 0
    out = capsys.readouterr().out
    assert "import-form: 2 new, 0 merged, 2 skipped." in out and "Molasses" not in out


def test_cli_import_form_netlify_needs_both_variables(run: Callable[..., int], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    monkeypatch.setenv("NETLIFY_AUTH_TOKEN", TOKEN)
    assert run("import-form", "--netlify") == 1
    captured = capsys.readouterr()
    assert "NETLIFY_AUTH_TOKEN and NETLIFY_SITE_ID" in captured.err
    assert TOKEN not in captured.out + captured.err
    monkeypatch.delenv("NETLIFY_AUTH_TOKEN")
    monkeypatch.setenv("NETLIFY_SITE_ID", "site-1")
    assert run("import-form", "--netlify") == 1


def test_cli_import_form_netlify_success_and_api_failure(run: Callable[..., int], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    monkeypatch.setenv("NETLIFY_AUTH_TOKEN", TOKEN)
    monkeypatch.setenv("NETLIFY_SITE_ID", "site-1")
    seen: dict[str, Any] = {}

    def fake_fetch(site_id: str, token: str, since: date | None = None) -> list[FormSubmission]:
        """Stand in for the API: record the call and return one submission."""
        seen.update(site_id=site_id, token_ok=token == TOKEN, since=since)
        return [_sub()]

    monkeypatch.setattr(cli, "fetch_netlify_submissions", fake_fetch)
    assert run("import-form", "--netlify", "--since", "2026-09-22") == 0
    assert seen == {"site_id": "site-1", "token_ok": True, "since": date(2026, 9, 22)}
    out = capsys.readouterr().out
    assert "Molasses & Co maya@molassesco.com cookie emerging_brand (new)" in out and TOKEN not in out

    def failing_fetch(site_id: str, token: str, since: date | None = None) -> list[FormSubmission]:
        """Stand in for an API that rejects the token."""
        raise NetlifyError("Netlify API returned 401 Unauthorized for GET /sites/site-1/forms")

    monkeypatch.setattr(cli, "fetch_netlify_submissions", failing_fetch)
    assert run("import-form", "--netlify") == 1
    captured = capsys.readouterr()
    assert "Netlify import failed: Netlify API returned 401" in captured.err and TOKEN not in captured.err


def test_cli_import_form_argument_and_file_errors(run: Callable[..., int], tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    assert run("import-form") == 1
    assert "CSV export path or --netlify" in capsys.readouterr().err
    assert run("import-form", str(FIXTURE_CSV), "--since", "last week") == 1
    assert "--since must be YYYY-MM-DD" in capsys.readouterr().err
    assert run("import-form", str(tmp_path / "missing.csv")) == 1
    assert "cannot read" in capsys.readouterr().err
    latin1 = tmp_path / "latin1.csv"
    latin1.write_bytes("product,email\ncr\xe8me cookies,a@crumbco.com\n".encode("latin-1"))
    assert run("import-form", str(latin1)) == 1
    assert "not UTF-8" in capsys.readouterr().err


# --- weekly report ---------------------------------------------------------------


def test_weekly_report_lists_inbound_first(store: LeadStore, sequence_template):
    store.upsert(Lead(company="Old Co", website="old.com", score=40))
    import_submissions(store, load_csv(FIXTURE_CSV))
    store.log_activity("ghost.com", "inbound", '{"summary": "product=x"}')  # its lead is gone: left out
    store.log_activity("old.com", "inbound", "typed by hand")  # not JSON: shown as written
    import_submissions(store, [_sub(product="Ginger snaps", submission_id="sub-late")])  # Molasses again, newest
    report = build_report(store, sequence_template, days=7)
    assert [e.company for e in report.inbound] == ["Molasses & Co", "Old Co", "Proteincrumb", "Good Pup Bakery"]
    assert report.inbound[1] == InboundEntry(company="Old Co", email="", category="other", summary="typed by hand")
    assert repr(report.inbound[2]) == "InboundEntry(company='Proteincrumb', category='cookie')"
    assert "inbound=4" in repr(report)
    text = render_report(report)
    assert text.index("Inbound (website): 4") < text.index("New leads found") < text.index("Follow-ups due now")
    assert "  Molasses & Co, maya@molassesco.com [cookie] product=Ginger snaps; volume=5,000 to 25,000\n" in text
    assert "Chewy molasses cookies; volume" not in text.split("New leads found")[0]  # one line per lead, the latest


def test_weekly_report_leaves_out_inbound_outside_the_window(store: LeadStore, sequence_template):
    import_submissions(store, [_sub()])
    report = build_report(store, sequence_template, days=7, today=date.today() + timedelta(days=30))
    assert report.inbound == []
    text = render_report(report)
    assert text.splitlines()[2] == "Inbound (website): 0"
