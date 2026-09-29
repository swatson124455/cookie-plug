"""Machine-readable output: JSON-LD, sitemap, robots, llms.txt, and security headers.

Structured data describes the business honestly: the organization is the
``broker`` of co-packing services, never their provider, because the brand
signs with the facility. Placeholder values are dropped from structured data
so a draft build never publishes them as facts.
"""

from __future__ import annotations

import base64
import hashlib
import re
from datetime import date
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit
from xml.sax.saxutils import escape as xml_escape

from leadgen.website.config import SiteConfig, is_placeholder

if TYPE_CHECKING:
    from leadgen.website.content import FaqItem, Guide
    from leadgen.website.facts import FacilityFacts

SCRIPT_TAG = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.DOTALL | re.IGNORECASE)
SRC_ATTR = re.compile(r"""\bsrc\s*=\s*["']([^"']+)["']""", re.IGNORECASE)


def _real(value: str) -> str:
    """Empty string for placeholders, so structured data never carries them."""
    return "" if is_placeholder(value) else value


def _clean(node: dict[str, Any]) -> dict[str, Any]:
    """Drop empty values (placeholders become empty) from a JSON-LD node, recursively."""
    cleaned: dict[str, Any] = {}
    for key, value in node.items():
        if isinstance(value, dict):
            value = _clean(value)
        elif isinstance(value, list):
            value = [_clean(v) if isinstance(v, dict) else v for v in value if v]
        if value not in ("", None, [], {}):
            cleaned[key] = value
    return cleaned


def org_id(cfg: SiteConfig) -> str:
    """Stable ``@id`` for the organization node."""
    return f"{cfg.base_url}/#org"


def organization_node(cfg: SiteConfig) -> dict[str, Any]:
    """The business: a partnerships service that brokers co-packing capacity."""
    contact = cfg.contact
    return _clean({
        "@type": "Organization", "@id": org_id(cfg), "name": cfg.brand, "alternateName": cfg.brand_short,
        "url": f"{cfg.base_url}/", "logo": f"{cfg.base_url}/logo.png", "description": cfg.tagline,
        "email": _real(contact.email), "telephone": _real(contact.phone),
        "address": {"@type": "PostalAddress", "streetAddress": _real(contact.address), "addressCountry": "US"} if _real(contact.address) else {},
        "sameAs": [_real(contact.linkedin)], "areaServed": {"@type": "Country", "name": "United States"},
        "knowsAbout": ["co-packing", "contract food manufacturing", "private label", "cookie manufacturing",
                       "bakery manufacturing", "pet treat manufacturing", "pet food manufacturing"],
        "contactPoint": {"@type": "ContactPoint", "contactType": "sales", "email": _real(contact.email),
                         "telephone": _real(contact.phone), "areaServed": "US", "availableLanguage": "English"},
    })


def website_node(cfg: SiteConfig) -> dict[str, Any]:
    """The site itself."""
    return {"@type": "WebSite", "@id": f"{cfg.base_url}/#website", "url": f"{cfg.base_url}/", "name": cfg.brand,
            "publisher": {"@id": org_id(cfg)}, "inLanguage": "en-US"}


def person_node(cfg: SiteConfig) -> dict[str, Any]:
    """The named author of every guide (identifiable expertise helps search and AI answers)."""
    return _clean({"@type": "Person", "@id": f"{cfg.base_url}/about/#author", "name": _real(cfg.contact.name),
                   "jobTitle": _real(cfg.contact.title), "description": _real(cfg.author_bio),
                   "url": f"{cfg.base_url}/about/", "sameAs": [_real(cfg.contact.linkedin)], "worksFor": {"@id": org_id(cfg)}})


def service_node(cfg: SiteConfig, name: str, description: str, url: str) -> dict[str, Any]:
    """A co-packing service the organization arranges (``broker``), not one it performs."""
    return {"@type": "Service", "@id": f"{url}#service", "name": name, "description": description, "url": url,
            "serviceType": "Contract food manufacturing (co-packing)", "broker": {"@id": org_id(cfg)},
            "areaServed": {"@type": "Country", "name": "United States"},
            "audience": {"@type": "BusinessAudience", "audienceType": "Food, snack, and pet-food brands"}}


def faq_node(items: list["FaqItem"], url: str) -> dict[str, Any]:
    """FAQPage markup for a list of questions."""
    return {"@type": "FAQPage", "@id": f"{url}#faq", "url": url, "mainEntity": [
        {"@type": "Question", "name": item.question, "acceptedAnswer": {"@type": "Answer", "text": item.answer}}
        for item in items]}


def article_node(cfg: SiteConfig, guide: "Guide", url: str, image: str) -> dict[str, Any]:
    """Article markup for a guide, with its summary and cited sources."""
    author = {"@id": f"{cfg.base_url}/about/#author"} if _real(cfg.contact.name) else {"@id": org_id(cfg)}
    return _clean({"@type": "Article", "@id": f"{url}#article", "headline": guide.title[:110], "description": guide.description,
                   "abstract": guide.summary, "datePublished": guide.published.isoformat(), "dateModified": guide.updated.isoformat(),
                   "author": author, "publisher": {"@id": org_id(cfg)}, "mainEntityOfPage": url, "image": image,
                   "wordCount": guide.word_count, "inLanguage": "en-US", "citation": [s["url"] for s in guide.sources if s.get("url")]})


def breadcrumb_node(trail: list[tuple[str, str]], url: str) -> dict[str, Any]:
    """BreadcrumbList from ``(name, absolute_url)`` pairs."""
    return {"@type": "BreadcrumbList", "@id": f"{url}#breadcrumb", "itemListElement": [
        {"@type": "ListItem", "position": index + 1, "name": name, "item": link} for index, (name, link) in enumerate(trail)]}


def graph(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap nodes in one ``@graph`` document."""
    return {"@context": "https://schema.org", "@graph": [node for node in nodes if node]}


def render_sitemap(entries: list[tuple[str, date | None]]) -> str:
    """sitemap.xml from ``(absolute_url, lastmod)`` pairs; lastmod is omitted when unknown."""
    urls = "".join(f"<url><loc>{xml_escape(loc)}</loc>" + (f"<lastmod>{lastmod.isoformat()}</lastmod>" if lastmod else "") + "</url>"
                   for loc, lastmod in entries)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n'


def render_robots(cfg: SiteConfig, draft: bool) -> str:
    """robots.txt: open to search and AI crawlers in production, closed for drafts."""
    if draft:
        return "User-agent: *\nDisallow: /\n"
    return ("# Search engines and AI assistants are welcome to read and cite this site.\n"
            f"User-agent: *\nAllow: /\nDisallow: /thanks/\n\nSitemap: {cfg.base_url}/sitemap.xml\n")


def _analytics_sources(snippet: str) -> tuple[list[str], list[str]]:
    """Script origins and inline-script hashes found in the analytics snippet."""
    origins: list[str] = []
    hashes: list[str] = []
    for attrs, body in SCRIPT_TAG.findall(snippet):
        src = SRC_ATTR.search(attrs)
        if src:
            parts = urlsplit(src.group(1))
            if parts.scheme == "https" and parts.netloc:
                origins.append(f"https://{parts.netloc}")
        elif body.strip():
            digest = base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode("ascii")
            hashes.append(f"'sha256-{digest}'")
    return sorted(set(origins)), hashes


def content_security_policy(cfg: SiteConfig) -> str:
    """A strict CSP: no third-party code except the configured analytics and form endpoint."""
    origins, hashes = _analytics_sources(cfg.analytics_snippet)
    extra = sorted({host if host.startswith("https://") else f"https://{host}" for host in cfg.analytics_hosts})
    script = " ".join(["'self'", *origins, *extra, *hashes])
    connect = " ".join(["'self'", *origins, *extra])
    form_action = "'self'"
    if cfg.form.provider == "formspree" and cfg.form.action:
        form_action += f" https://{urlsplit(cfg.form.action).netloc}"
    return (f"default-src 'self'; script-src {script}; style-src 'self'; img-src 'self' data: {' '.join(extra)}".rstrip()
            + f"; font-src 'self'; connect-src {connect}; form-action {form_action}; frame-ancestors 'none'; "
            "base-uri 'self'; object-src 'none'; upgrade-insecure-requests")


def render_headers(cfg: SiteConfig, draft: bool) -> str:
    """Netlify ``_headers``: security headers everywhere, long caching for fonts."""
    lines = ["/*", "  X-Content-Type-Options: nosniff", "  Referrer-Policy: strict-origin-when-cross-origin",
             "  X-Frame-Options: DENY", "  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()",
             f"  Content-Security-Policy: {content_security_policy(cfg)}"]
    if draft:
        lines.append("  X-Robots-Tag: noindex, nofollow")
    lines += ["/fonts/*", "  Cache-Control: public, max-age=31536000, immutable",
              "/og/*", "  Cache-Control: public, max-age=604800"]
    return "\n".join(lines) + "\n"


def _llms_facts(cfg: SiteConfig, facts: "FacilityFacts") -> list[str]:
    """The confirmed-facts bullet list for llms.txt."""
    certifications = ", ".join(facts.certifications) or "shared on request; the site lists only documented certifications"
    lines = [f"- Open lines: {', '.join(line.label for line in facts.open_lines)}",
             f"- Services: {', '.join(service.label for service in facts.services)}",
             f"- Certifications: {certifications}"]
    lines += [f"- {fact.label}: {fact.value}" for fact in facts.numbers]
    if not facts.numbers:
        lines.append("- Minimums and lead times: confirmed per product on the first call")
    lines.append(f"- Contact: {_real(cfg.contact.name) or cfg.brand}, {_real(cfg.contact.email) or 'via the capacity-check form'}")
    return lines


def render_llms_txt(cfg: SiteConfig, facts: "FacilityFacts", guides: list["Guide"], pages: list[tuple[str, str, str]]) -> str:
    """``/llms.txt`` per llmstxt.org: who we are, confirmed facts, and a link map."""
    base = cfg.base_url
    lines = [f"# {cfg.brand}", "",
             f"> {cfg.brand} connects emerging and growing food and pet-food brands in the United States with a "
             f"contract manufacturer (co-packer) that has open production capacity now for {facts.open_line_labels().lower()}. "
             "Turnkey: formulation, production, packaging, labeling, and nutrition panels. Brands never pay us; the facility does.",
             "", f"Confirmed facts as of {facts.as_of}:", "", *_llms_facts(cfg, facts), "", "## Pages", ""]
    lines += [f"- [{title}]({base}/{path}): {note}" for title, path, note in pages]
    lines += ["", "## Guides", ""]
    lines += [f"- [{guide.title}]({base}/guides/{guide.slug}/): {guide.summary}" for guide in guides]
    lines += ["", "## Optional", "", f"- [Full text of the guides and FAQ]({base}/llms-full.txt)"]
    return "\n".join(lines) + "\n"


def render_llms_full(cfg: SiteConfig, facts: "FacilityFacts", guides: list["Guide"], faq: list["FaqItem"]) -> str:
    """``/llms-full.txt``: the FAQ and every guide in Markdown, for assistants that read whole sites."""
    base = cfg.base_url
    parts = [f"# {cfg.brand}: full text", "", f"{cfg.tagline}. Capacity status as of {facts.as_of}: open for "
             f"{facts.open_line_labels().lower()}.", "", "## Frequently asked questions", ""]
    for item in faq:
        parts += [f"### {item.question}", "", item.answer, ""]
    for guide in guides:
        parts += [f"## {guide.title}", "", f"Source: {base}/guides/{guide.slug}/ (updated {guide.updated.isoformat()})", "",
                  f"Short answer: {guide.summary}", "", guide.markdown.strip(), ""]
    return "\n".join(parts).rstrip() + "\n"
