"""CLI smoke tests. Each command runs end to end against a temp database."""

import os
from pathlib import Path

import httpx
import pytest

from leadgen import cli
from leadgen.enrich import WebsiteEnricher
from leadgen.models import Stage

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def run(tmp_path, monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    db = str(tmp_path / "cli.sqlite3")

    def _run(*argv: str) -> int:
        return cli.main(["--db", db, *argv])

    return _run


def test_import_score_report_export(run, sample_csv, tmp_path, capsys):
    assert run("import", str(sample_csv), "--source", "expo") == 0
    assert "imported 2 leads, skipped 2" in capsys.readouterr().out
    assert run("score", "--min-score", "0") == 0
    assert "Crumb Co" in capsys.readouterr().out
    assert run("report") == 0
    assert "new" in capsys.readouterr().out
    out = tmp_path / "x.csv"
    assert run("export", str(out)) == 0
    assert out.exists()


def test_enrich_command_with_mocked_network(run, sample_csv, shopify_html, monkeypatch, capsys):
    transport = httpx.MockTransport(lambda r: httpx.Response(200, text=shopify_html))
    monkeypatch.setattr(cli, "WebsiteEnricher", lambda: WebsiteEnricher(client=httpx.Client(transport=transport)))
    run("import", str(sample_csv))
    assert run("enrich") == 0
    assert "enriched 2 leads" in capsys.readouterr().out
    assert run("enrich", "--all", "--limit", "1") == 0


def test_qualify_and_draft_rule_based(run, sample_csv, capsys):
    run("import", str(sample_csv))
    run("score")
    assert run("qualify", "--min-score", "0", "--threshold", "0") == 0
    assert "RuleBasedQualifier" in capsys.readouterr().out
    assert run("draft", "crumbco.com") == 0
    out = capsys.readouterr().out
    assert "day 0 [email]" in out and "Jordan" in out
    assert run("draft", "crumbco.com", "--ai") == 0


def test_draft_missing_lead(run, capsys):
    assert run("draft", "nobody.com") == 1
    assert "no lead" in capsys.readouterr().err


def test_advance_command(run, sample_csv, capsys):
    run("import", str(sample_csv))
    assert run("advance", "crumbco.com", Stage.REPLIED.value, "--note", "positive") == 0
    assert "-> replied" in capsys.readouterr().out
    assert run("advance", "nobody.com", "replied") == 1


def test_queries_and_economics(run, capsys):
    assert run("queries", "pet_treat") == 0
    assert "dog treats" in capsys.readouterr().out
    assert run("economics", "--pct", "5", "--annual-purchases", "100000") == 0
    assert '"first_year_payout": 5000.0' in capsys.readouterr().out


def test_facility_check_reports_pending(run, capsys):
    assert run("facility-check") == 1
    assert "TO_CONFIRM" in capsys.readouterr().out


def test_facility_check_complete(run, tmp_path, capsys):
    path = tmp_path / "f.yaml"
    path.write_text(
        "name: Real Plant\ncategories: [cookie]\ncertifications: {fda_registered: true}\n"
        "commercial: {spare_capacity_pct: 40, min_order_units: 1000}\nlocation: {city: Austin}\n",
        encoding="utf-8",
    )
    assert cli.main(["--db", str(tmp_path / "d.sqlite3"), "--facility", str(path), "facility-check"]) == 0
    assert "complete" in capsys.readouterr().out


def test_sender_from_env(monkeypatch):
    monkeypatch.setenv("LEADGEN_SENDER_NAME", "Sam")
    assert cli._sender().name == "Sam"
    assert os.environ["LEADGEN_SENDER_NAME"] == "Sam"


def test_touch_due_and_brief(run, sample_csv, capsys):
    run("import", str(sample_csv))
    assert run("touch", "crumbco.com", "0") == 0
    assert "logged day 0" in capsys.readouterr().out
    assert run("due") == 0
    assert "nothing due" in capsys.readouterr().out
    from datetime import date, timedelta

    later = (date.today() + timedelta(days=4)).isoformat()
    assert run("due", "--date", later) == 0
    out = capsys.readouterr().out
    assert "Crumb Co" in out and "linkedin" in out
    assert run("touch", "crumbco.com", "3", "--channel", "linkedin") == 0
    capsys.readouterr()
    assert run("due", "--date", later) == 0
    assert "nothing due" in capsys.readouterr().out
    assert run("brief", "crumbco.com") == 0
    out = capsys.readouterr().out
    assert "Call brief: Crumb Co" in out and "Fit " in out and "stage_change" in out
    assert run("touch", "nobody.com", "0") == 1
    assert run("brief", "nobody.com") == 1


def test_emails_command(run, sample_csv, tmp_path, capsys):
    run("import", str(sample_csv))
    assert run("emails", "crumbco.com") == 0
    out = capsys.readouterr().out
    assert "jordan@crumbco.com" in out and "verified" in out
    no_email = tmp_path / "noemail.csv"
    no_email.write_text("company,website,contact_name\nPup Co,pupco.com,Priya Nair\nNo Site,,Ann Lee\n", encoding="utf-8")
    run("import", str(no_email))
    capsys.readouterr()
    assert run("emails", "pupco.com", "--pattern", "first.last") == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("priya.nair@pupco.com") and "UNVERIFIED" in out
    assert run("emails", "no site") == 1
    assert run("emails", "nobody.com") == 1


def test_watch_command_with_mocked_feeds(run, monkeypatch, capsys):
    from datetime import date

    from leadgen import cli
    from leadgen.sources import RawItem

    class FakeSource:
        name = "rss_fake"

        def fetch(self, since):
            return [
                RawItem(source=self.name, title="Crumb Co launches cookies at Target", url="https://e/1", published=date.today()),
                RawItem(source=self.name, title="Crumb Co raises $2M seed for cookies", url="https://e/2", published=date.today()),
                RawItem(source=self.name, title="Why consumers love snacks", url="https://e/3", published=date.today()),
            ]

    monkeypatch.setattr(cli, "build_sources", lambda config, client: [FakeSource()])
    monkeypatch.setattr(cli, "default_client", lambda: None)
    assert run("watch", "--days", "3") == 0
    out = capsys.readouterr().out
    assert "added 1, updated 1, skipped 1" in out
    assert run("watch", "--source", "nothing") == 0
    assert run("score", "--min-score", "0") == 0
    out = capsys.readouterr().out
    assert "Crumb Co" in out and "recent_funding" in out and "recent_retail_launch" in out


def test_dossier_command_requires_key_and_runs_with_fake_client(run, sample_csv, monkeypatch, capsys, tmp_path):
    from types import SimpleNamespace

    from leadgen import cli

    run("import", str(sample_csv))
    assert run("dossier", "crumbco.com") == 1
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().err
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(cli, "build_dossier", lambda lead, facility, client, model: "**Product line**\n- cookies")
    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", lambda: SimpleNamespace())
    assert run("dossier", "crumbco.com", "--out", str(tmp_path)) == 0
    assert "crumbco_com.md" in capsys.readouterr().out
    assert run("dossier", "nobody.com", "--out", str(tmp_path)) == 1
    run("score")
    assert run("dossier", "--min-score", "0", "--limit", "1", "--out", str(tmp_path)) == 0


def test_list_tag_and_thread_draft(run, sample_csv, capsys):
    run("import", str(sample_csv))
    run("score")
    assert run("tag", "crumbco.com", "spear") == 0
    assert "['spear']" in capsys.readouterr().out
    assert run("tag", "crumbco.com", "spear") == 0
    assert "no change" in capsys.readouterr().out
    assert run("list", "--tag", "spear") == 0
    out = capsys.readouterr().out
    assert "Crumb Co" in out and "Barkery" not in out
    assert run("list", "--tag", "nothing") == 0
    assert "no leads match" in capsys.readouterr().out
    assert run("tag", "crumbco.com", "spear", "--remove") == 0
    assert run("tag", "nobody.com", "x") == 1
    assert run("--template", "config/templates/spear_sequence.yaml", "draft", "crumbco.com", "--thread", "operator") == 0
    out = capsys.readouterr().out
    assert "(operator)" in out and "(founder)" not in out


def test_import_html_command(run, capsys):
    fixture = str(REPO_ROOT / "tests" / "fixtures" / "exhibitors.html")
    assert run("import-html", fixture, "--source", "expo_test", "--dry-run") == 0
    assert "3 candidates" in capsys.readouterr().out
    assert run("import-html", fixture, "--source", "expo_test", "--category", "cookie", "--skip", "barkerylane.com") == 0
    assert "imported 2 new leads" in capsys.readouterr().out
    assert run("import-html", fixture, "--source", "expo_test") == 0
    assert "imported 1 new leads" in capsys.readouterr().out


def test_websites_command(run, monkeypatch, capsys):
    from types import SimpleNamespace

    from leadgen import cli

    assert run("websites") == 1
    capsys.readouterr()
    no_site = REPO_ROOT / "tests" / "fixtures" / "sample_leads.csv"
    run("import", str(no_site))
    run("score", "--min-score", "0")
    capsys.readouterr()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", lambda: SimpleNamespace())
    monkeypatch.setattr(cli, "find_website", lambda lead, client, model: "")
    assert run("websites", "--min-score", "0") == 0
    assert "found 0 of 0" in capsys.readouterr().out
