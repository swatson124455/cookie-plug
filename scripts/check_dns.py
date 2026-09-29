"""Check a sending domain's SPF, DKIM, and DMARC records.

Usage: python scripts/check_dns.py yourdomain.com [--dkim-selector google]

Prints each record and a pass/fail verdict against the setup in
docs/07_email_setup.md. Requires dnspython (pip install dnspython).
"""

from __future__ import annotations

import argparse
import sys

try:
    import dns.resolver
except ImportError:  # pragma: no cover - guidance for the user, not logic
    sys.exit("dnspython is required: pip install dnspython")


def txt_records(name: str) -> list[str]:
    """Return every TXT record at ``name``, or an empty list if none resolve."""
    try:
        answers = dns.resolver.resolve(name, "TXT", lifetime=10)
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.resolver.LifetimeTimeout):
        return []
    return [b"".join(r.strings).decode("utf-8", "replace") for r in answers]


def check_spf(domain: str) -> tuple[bool, str]:
    spf = [r for r in txt_records(domain) if r.lower().startswith("v=spf1")]
    if not spf:
        return False, "no SPF record"
    if len(spf) > 1:
        return False, f"{len(spf)} SPF records found; there must be exactly one"
    record = spf[0]
    verdict = "ok" if ("~all" in record or "-all" in record) else "missing ~all or -all"
    return verdict == "ok", f"{record} ({verdict})"


def check_dkim(domain: str, selector: str) -> tuple[bool, str]:
    records = txt_records(f"{selector}._domainkey.{domain}")
    if not records:
        return False, f"no DKIM record at {selector}._domainkey.{domain}"
    return True, records[0][:60] + ("..." if len(records[0]) > 60 else "")


def check_dmarc(domain: str) -> tuple[bool, str]:
    records = [r for r in txt_records(f"_dmarc.{domain}") if r.lower().startswith("v=dmarc1")]
    if not records:
        return False, "no DMARC record"
    record = records[0]
    policy = next((p.split("=")[1] for p in record.replace(" ", "").split(";") if p.startswith("p=")), "")
    note = "ok" if policy in ("none", "quarantine", "reject") else "missing p= policy"
    return note == "ok", f"{record} (policy {policy or 'unset'})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check SPF, DKIM, and DMARC for a sending domain")
    parser.add_argument("domain")
    parser.add_argument("--dkim-selector", default="google", help="Google Workspace uses 'google'")
    args = parser.parse_args(argv)
    domain = args.domain.lower().strip().removeprefix("http://").removeprefix("https://").split("/")[0]
    results = {
        "SPF": check_spf(domain),
        "DKIM": check_dkim(domain, args.dkim_selector),
        "DMARC": check_dmarc(domain),
    }
    all_ok = True
    for name, (ok, detail) in results.items():
        all_ok = all_ok and ok
        print(f"{'PASS' if ok else 'FAIL'}  {name:<6} {detail}")
    print("ready to send" if all_ok else "not ready: fix the FAIL lines before any cold email")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
