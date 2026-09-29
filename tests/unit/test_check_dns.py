"""Unit tests for scripts/check_dns.py with DNS mocked."""

import importlib.util
import sys
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("check_dns", Path(__file__).resolve().parents[2] / "scripts" / "check_dns.py")
check_dns = importlib.util.module_from_spec(spec)
sys.modules["check_dns"] = check_dns
spec.loader.exec_module(check_dns)


@pytest.fixture
def fake_dns(monkeypatch):
    table: dict[str, list[str]] = {}
    monkeypatch.setattr(check_dns, "txt_records", lambda name: table.get(name, []))
    return table


def test_all_pass(fake_dns, capsys):
    fake_dns["ex.com"] = ["v=spf1 include:_spf.google.com ~all"]
    fake_dns["google._domainkey.ex.com"] = ["v=DKIM1; k=rsa; p=MIIB"]
    fake_dns["_dmarc.ex.com"] = ["v=DMARC1; p=none; rua=mailto:d@ex.com"]
    assert check_dns.main(["https://ex.com/"]) == 0
    out = capsys.readouterr().out
    assert out.count("PASS  ") == 3 and "ready to send" in out


def test_missing_records_fail(fake_dns, capsys):
    assert check_dns.main(["ex.com"]) == 1
    out = capsys.readouterr().out
    assert out.count("FAIL  ") == 3 and "not ready" in out


def test_spf_without_all_and_duplicate(fake_dns):
    fake_dns["ex.com"] = ["v=spf1 include:_spf.google.com"]
    ok, detail = check_dns.check_spf("ex.com")
    assert not ok and "missing" in detail
    fake_dns["ex.com"] = ["v=spf1 ~all", "v=spf1 -all"]
    ok, detail = check_dns.check_spf("ex.com")
    assert not ok and "exactly one" in detail


def test_spf_redirect_is_valid(fake_dns):
    fake_dns["ex.com"] = ["v=spf1 redirect=_spf.google.com"]
    ok, _ = check_dns.check_spf("ex.com")
    assert ok


def test_dmarc_without_policy(fake_dns):
    fake_dns["_dmarc.ex.com"] = ["v=DMARC1; rua=mailto:d@ex.com"]
    ok, detail = check_dns.check_dmarc("ex.com")
    assert not ok and "missing p=" in detail
