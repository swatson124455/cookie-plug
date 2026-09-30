"""Tell Bing, and the other IndexNow engines, which pages changed, right after a deploy.

IndexNow is a shared protocol: one POST to api.indexnow.org reaches every
participating engine (Bing, which grounds Microsoft Copilot, among them). The
site proves it owns the domain by serving ``/<key>.txt`` containing the key,
which the production build writes when ``indexnow_key`` is set.

Run ``python site/build.py --indexnow`` after a deploy that changed content,
for example the monthly capacity-status update.
"""

from __future__ import annotations

import re

import httpx

from leadgen.website.config import SiteConfig, is_placeholder

ENDPOINT = "https://api.indexnow.org/indexnow"
KEY_PATTERN = re.compile(r"^[A-Za-z0-9-]{8,128}$")
TIMEOUT_SECONDS = 20.0
MAX_URLS = 10_000


class IndexNowError(RuntimeError):
    """The ping could not be sent or was refused."""


def valid_key(key: str) -> bool:
    """IndexNow keys are 8 to 128 characters of letters, digits, and dashes."""
    return bool(KEY_PATTERN.match(key or ""))


def key_file(cfg: SiteConfig) -> tuple[str, str] | None:
    """``(file name, contents)`` for the ownership file, or None when no valid key is set."""
    return (f"{cfg.indexnow_key}.txt", cfg.indexnow_key) if valid_key(cfg.indexnow_key) else None


def payload(cfg: SiteConfig, urls: list[str]) -> dict[str, object]:
    """The JSON body the protocol expects."""
    host = cfg.base_url.split("://", 1)[-1].split("/", 1)[0]
    return {"host": host, "key": cfg.indexnow_key, "keyLocation": f"{cfg.base_url}/{cfg.indexnow_key}.txt",
            "urlList": urls[:MAX_URLS]}


def ping(cfg: SiteConfig, urls: list[str], client: httpx.Client | None = None) -> int:
    """Submit the URLs; return the HTTP status (200 or 202 means accepted)."""
    if is_placeholder(cfg.domain) or not cfg.domain.startswith("https://"):
        raise IndexNowError("set the real https domain in site/config.yaml before pinging")
    if not valid_key(cfg.indexnow_key):
        raise IndexNowError("set indexnow_key in site/config.yaml (8 to 128 letters, digits, or dashes)")
    if not urls:
        raise IndexNowError("no URLs to submit")
    owns_client = client is None
    http = client or httpx.Client(timeout=TIMEOUT_SECONDS)
    try:
        response = http.post(ENDPOINT, json=payload(cfg, urls))
    except httpx.HTTPError as exc:
        raise IndexNowError(f"could not reach {ENDPOINT}: {type(exc).__name__}") from exc
    finally:
        if owns_client:
            http.close()
    if response.status_code not in (200, 202):
        raise IndexNowError(f"IndexNow refused the submission (HTTP {response.status_code})")
    return response.status_code
