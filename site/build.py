"""Build the static site from site/config.yaml, config/facility.yaml, and site/content/.

Run ``python site/build.py`` to write ``site/dist/``. Every customer-facing
fact comes from configuration: facility claims render only when confirmed
(no ``TO_CONFIRM`` values reach a page), and contact details come from
``site/config.yaml``. Pages carry JSON-LD so search engines and AI
assistants can read them as data.
"""

from __future__ import annotations

import html
import json
import shutil
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from leadgen.facility import FacilityProfile, load_facility  # noqa: E402

SITE = ROOT / "site"
DIST = SITE / "dist"
CONTENT = SITE / "content"

CATEGORY_PAGES: dict[str, dict[str, str]] = {
    "cookie-co-packer": {"line": "cookie", "title": "Cookie Co-Packer With Open Capacity", "noun": "cookie",
                         "intro": "Drop, wire-cut, soft-baked, and sandwich cookies, produced under your brand with formulation, packaging, and labeling handled in one place."},
    "bakery-co-packer": {"line": "bakery", "title": "Bakery and Baked-Goods Co-Packer", "noun": "baked goods",
                         "intro": "Brownies, muffins, granola, crackers, and bars for brands moving from a kitchen into retail."},
    "dog-treat-co-packer": {"line": "pet_treat", "title": "Dog Treat Co-Packer and Manufacturer", "noun": "dog treat",
                            "intro": "Baked biscuits and soft-baked treats with pet-food labeling handled, for brands launching on Chewy, in pet specialty, or in grocery."},
    "pet-food-co-packer": {"line": "pet_food", "title": "Pet Food Co-Packer", "noun": "pet food",
                           "intro": "Baked pet food and treats under one food-safety program alongside human bakery lines."},
}


def load_site_config(path: Path = SITE / "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def confirmed_lines(facility: FacilityProfile) -> list[str]:
    return [c.value.replace("_", " ") for c in facility.categories]


def confirmed_services(facility: FacilityProfile) -> list[str]:
    labels = {"formulation": "Formulation and R&D", "private_label": "Private label", "contract_manufacturing": "Contract manufacturing",
              "packaging": "Packaging", "labeling": "Labeling", "nutrition_panels": "Nutrition panels and label compliance", "shelf_ready": "Shelf-ready case packs"}
    return [labels[k] for k, on in facility.services.items() if on and k in labels]


def confirmed_certifications(facility: FacilityProfile) -> list[str]:
    pretty = {"fda_registered": "FDA registered", "sqf": "SQF", "organic": "Organic", "gluten_free": "Gluten-free certified",
              "kosher": "Kosher", "non_gmo": "Non-GMO Project", "aafco_pet": "AAFCO-compliant pet formulations", "allergen_controlled_lines": "Allergen-controlled lines"}
    out: list[str] = []
    for item in facility.confirmed_certifications():
        key, _, detail = item.partition(": ")
        label = pretty.get(key, key)
        out.append(f"{label} ({detail})" if detail else label)
    return out


def layout(cfg: dict, title: str, description: str, body: str, path: str, jsonld: list[dict] | None = None) -> str:
    """Wrap a page body in the shared head, header, and footer."""
    brand, domain = esc(cfg["brand"]), cfg["domain"].rstrip("/")
    canonical = f"{domain}/{path}".rstrip("/") + ("/" if path else "")
    scripts = "".join(f'<script type="application/ld+json">{json.dumps(item)}</script>' for item in (jsonld or []))
    contact = cfg["contact"]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(description)}"><link rel="canonical" href="{canonical}">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:type" content="website"><meta property="og:url" content="{canonical}">
<link rel="stylesheet" href="/styles.css">{scripts}{cfg.get("analytics_snippet", "")}</head>
<body><header class="site"><div class="wrap"><a class="brand" href="/">{brand}</a><nav><a href="/capabilities/">Capabilities</a><a href="/guides/">Guides</a><a href="/faq/">FAQ</a><a href="/contact/">Contact</a></nav></div></header>
<main class="wrap">{body}</main>
<footer class="site"><div class="wrap"><p><strong>{brand}</strong> · {esc(contact["name"])}, {esc(contact["title"])} · <a href="mailto:{esc(contact["email"])}">{esc(contact["email"])}</a> · {esc(contact["phone"])}</p>
<p>{esc(contact["address"])} · <a href="{esc(contact["linkedin"])}">LinkedIn</a></p>
<p>We represent a US manufacturer and are paid by the facility, not by brands. Facts on this site are limited to what the facility has confirmed in writing.</p></div></footer></body></html>"""


def organization_jsonld(cfg: dict) -> dict:
    c = cfg["contact"]
    return {"@context": "https://schema.org", "@type": "Organization", "name": cfg["brand"], "url": cfg["domain"],
            "description": cfg["tagline"], "email": c["email"], "telephone": c["phone"],
            "address": {"@type": "PostalAddress", "streetAddress": c["address"]},
            "contactPoint": {"@type": "ContactPoint", "contactType": "sales", "email": c["email"], "telephone": c["phone"]}}


def service_jsonld(cfg: dict, name: str, description: str) -> dict:
    return {"@context": "https://schema.org", "@type": "Service", "name": name, "description": description,
            "provider": {"@type": "Organization", "name": cfg["brand"], "url": cfg["domain"]}, "areaServed": "US", "serviceType": "Contract food manufacturing"}


def capacity_form(cfg: dict) -> str:
    action = cfg.get("form_action") or ""
    attrs = f'action="{esc(action)}" method="POST"' if action else 'name="capacity-check" method="POST" data-netlify="true" netlify-honeypot="company-website"'
    hidden = "" if action else '<input type="hidden" name="form-name" value="capacity-check"><p style="display:none"><label>Leave empty <input name="company-website"></label></p>'
    return f"""<form class="capacity" {attrs}>{hidden}
<label>Your product<input name="product" required placeholder="e.g. soft-baked oatmeal cookies, 6 oz bag"></label>
<label>Monthly volume, now or needed<select name="volume" required><option value="">Choose</option><option>Under 5,000 units</option><option>5,000 to 25,000</option><option>25,000 to 100,000</option><option>Over 100,000</option></select></label>
<label>When you need it<select name="timing" required><option value="">Choose</option><option>Now</option><option>Within 3 months</option><option>3 to 6 months</option><option>Exploring</option></select></label>
<label>How it is made today<select name="current_setup" required><option value="">Choose</option><option>Home or shared kitchen</option><option>Our own facility</option><option>A co-packer</option><option>Not in production yet</option></select></label>
<label>Company and website<input name="company" required placeholder="Brand name, brand.com"></label>
<label>Email<input name="email" type="email" required></label>
<label>Anything else<textarea name="notes" rows="3" placeholder="Retailer, launch date, certifications you need"></textarea></label>
<button class="btn" type="submit">Request a capacity check</button>
<p class="meta">We reply within one business day. No newsletter, no spam.</p></form>"""


def render_home(cfg: dict, facility: FacilityProfile) -> str:
    lines = ", ".join(confirmed_lines(facility))
    services = "".join(f"<li>{esc(s)}</li>" for s in confirmed_services(facility))
    body = f"""<section class="hero"><span class="status">{esc(cfg["capacity_status"])}</span>
<h1>{esc(cfg["tagline"])}</h1>
<p class="lead">Most US co-packers are booked six to twelve months out and keep raising minimums. We work with a manufacturer that has open lines now for {esc(lines)}, and does the whole job under one roof: formulation, production, packaging, labeling, and nutrition panels. First step is a benchmark of your product, not a pitch.</p>
<p><a class="btn" href="#capacity">Request a capacity check</a> <a class="btn secondary" href="/guides/">Read the guides</a></p></section>
<section><h2>Who this is for</h2><div class="grid">
<div class="card"><h3>Outgrowing a kitchen</h3><p>You are turning down wholesale, a buyer asked for an audit certificate, or the founders are on the line at 5am.</p></div>
<div class="card"><h3>Launching into retail</h3><p>A first listing at Sprouts, Chewy, Target, or a regional chain, and the reorder will arrive faster than the first order did.</p></div>
<div class="card"><h3>Changing format</h3><p>Refrigerated to shelf-stable, food truck to packaged, a cookie brand adding dog treats. Formulation is included.</p></div>
<div class="card"><h3>Adding a second source</h3><p>One co-packer is a single point of failure. A second line that has already matched your product is cheap insurance.</p></div></div></section>
<section><h2>How it works</h2><ol class="steps">
<li><strong>Send your product or spec.</strong> A case, not a bag, plus your target price and realistic volume.</li>
<li><strong>Get a benchmark sample in weeks.</strong> The facility matches it and returns it with a spec sheet. You judge blind.</li>
<li><strong>Approve, quote, run.</strong> Written pricing at two volumes, then a first run sized to fit, shipped shelf-ready.</li></ol></section>
<section><h2>What is included</h2><ul class="plain">{services}</ul><p><a href="/capabilities/">Full capabilities</a></p></section>
<section id="capacity"><h2>Request a capacity check</h2><p>Four questions. We reply within one business day with whether the product fits and what a sample would take.</p>{capacity_form(cfg)}</section>"""
    jsonld = [organization_jsonld(cfg), service_jsonld(cfg, "Contract manufacturing and private label for cookies, baked goods, and pet treats", cfg["tagline"])]
    return layout(cfg, f"{cfg['brand']}: {cfg['tagline']}", cfg["tagline"] + ". Sampling in weeks, turnkey from formulation to shelf-ready.", body, "", jsonld)


def render_capabilities(cfg: dict, facility: FacilityProfile) -> str:
    lines = "".join(f"<li>{esc(l)}</li>" for l in confirmed_lines(facility))
    services = "".join(f"<li>{esc(s)}</li>" for s in confirmed_services(facility))
    certs = confirmed_certifications(facility)
    cert_html = "".join(f"<li>{esc(c)}</li>" for c in certs) or "<li>Certification details on request; we list only what we can document.</li>"
    body = f"""<section class="hero"><h1>Capabilities</h1><p class="lead">Everything on this page is confirmed by the facility in writing. If a detail you need is missing, ask and we will confirm it before we answer.</p></section>
<section><h2>Production lines</h2><ul class="plain">{lines}</ul></section>
<section><h2>Services</h2><ul class="plain">{services}</ul></section>
<section><h2>Certifications</h2><ul class="plain">{cert_html}</ul></section>
<section><h2>Formats and minimums</h2><p>Minimums and lead times depend on the line and the format and are confirmed on the first call. A facility with open capacity can usually be flexible on a first run.</p><p><a class="btn" href="/#capacity">Request a capacity check</a></p></section>"""
    return layout(cfg, f"Capabilities | {cfg['brand']}", "Confirmed production lines, services, and certifications at the facility we represent.", body, "capabilities", [organization_jsonld(cfg)])


def render_category(cfg: dict, facility: FacilityProfile, slug: str, spec: dict[str, str]) -> str:
    supported = spec["line"] in {c.value for c in facility.categories}
    availability = "Open capacity on this line now." if supported else "Ask about this format; we confirm line fit before anything else."
    body = f"""<section class="hero"><span class="status">{esc(cfg["capacity_status"])}</span><h1>{esc(spec["title"])}</h1>
<p class="lead">{esc(spec["intro"])} {esc(availability)}</p><p><a class="btn" href="/#capacity">Request a capacity check</a></p></section>
<section><h2>What a {esc(spec["noun"])} co-packer should give you</h2><ul class="plain">
<li>A benchmark sample of your product before any quote</li><li>Written pricing at two volumes</li><li>A minimum that fits a first run and grows with you</li><li>Formulation, packaging, labeling, and nutrition panels in one place</li><li>Lead times in weeks, not quarters</li></ul></section>
<section><h2>Read next</h2><p><a href="/guides/">Guides on finding, qualifying, and switching co-packers</a> · <a href="/faq/">Frequently asked questions</a></p></section>"""
    return layout(cfg, f"{spec['title']} | {cfg['brand']}", spec["intro"], body, slug, [service_jsonld(cfg, spec["title"], spec["intro"])])


def parse_guide(path: Path) -> dict[str, str]:
    """Leading ``key: value`` header lines, then the HTML body from the first tag onward."""
    lines = path.read_text(encoding="utf-8").splitlines()
    meta: dict[str, str] = {}
    index = 0
    while index < len(lines) and not lines[index].lstrip().startswith("<") and ":" in lines[index]:
        key, _, value = lines[index].partition(":")
        meta[key.strip()] = value.strip()
        index += 1
    meta["slug"] = path.stem
    meta["body"] = "\n".join(lines[index:]).strip()
    return meta


def render_guide(cfg: dict, guide: dict[str, str]) -> str:
    author = cfg["contact"]["name"]
    body = f"""<article><p class="meta">Guide · {esc(guide.get("date", ""))} · by {esc(author)}</p><h1>{esc(guide["title"])}</h1>{guide["body"]}
<div class="note"><p><strong>Capacity is open now.</strong> {esc(cfg["capacity_status"])} <a href="/#capacity">Request a capacity check</a> and we reply within one business day.</p></div>
<p class="meta">About the author: {esc(cfg["author_bio"])}</p></article>"""
    jsonld = [{"@context": "https://schema.org", "@type": "Article", "headline": guide["title"], "description": guide.get("description", ""),
               "datePublished": guide.get("date", ""), "author": {"@type": "Person", "name": author}, "publisher": {"@type": "Organization", "name": cfg["brand"]}}]
    return layout(cfg, f"{guide['title']} | {cfg['brand']}", guide.get("description", ""), body, f"guides/{guide['slug']}", jsonld)


def render_guide_index(cfg: dict, guides: list[dict[str, str]]) -> str:
    items = "".join(f'<div class="card"><h3><a href="/guides/{esc(g["slug"])}/">{esc(g["title"])}</a></h3><p>{esc(g.get("description", ""))}</p></div>' for g in guides)
    body = f'<section class="hero"><h1>Guides for brands choosing a co-packer</h1><p class="lead">Plain answers to the questions founders ask before, during, and after the switch.</p></section><section><div class="grid">{items}</div></section>'
    return layout(cfg, f"Guides | {cfg['brand']}", "How to find, qualify, and switch co-packers for cookies, baked goods, and pet treats.", body, "guides")


def render_faq(cfg: dict, faqs: list[dict[str, str]]) -> str:
    items = "".join(f"<details><summary>{esc(f['q'])}</summary><p>{esc(f['a'])}</p></details>" for f in faqs)
    body = f'<section class="hero"><h1>Frequently asked questions</h1><p class="lead">Straight answers. If yours is not here, <a href="/contact/">ask</a>.</p></section><section class="faq">{items}</section>'
    jsonld = [{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in faqs]}]
    return layout(cfg, f"FAQ | {cfg['brand']}", "Co-packer minimums, sampling, certifications, private label, and costs, answered plainly.", body, "faq", jsonld)


def render_contact(cfg: dict) -> str:
    c = cfg["contact"]
    body = f"""<section class="hero"><h1>Contact</h1><p class="lead">Email or call; founders at small brands often prefer the phone and that is fine.</p>
<p><a href="mailto:{esc(c["email"])}">{esc(c["email"])}</a> · {esc(c["phone"])}<br>{esc(c["name"])}, {esc(c["title"])}<br>{esc(c["address"])}</p></section>
<section id="capacity"><h2>Or send the four questions</h2>{capacity_form(cfg)}</section>"""
    return layout(cfg, f"Contact | {cfg['brand']}", "Reach the partnerships lead directly, or send a four-question capacity check.", body, "contact", [organization_jsonld(cfg)])


def render_llms_txt(cfg: dict, facility: FacilityProfile, guides: list[dict[str, str]]) -> str:
    c = cfg["contact"]
    lines = [f"# {cfg['brand']}", "", f"> {cfg['tagline']}.", "",
             f"{cfg['brand']} is a partnerships service that connects cookie, baked-goods, snack, and pet-treat brands in the United States with a contract manufacturer (co-packer) that has open production capacity. Confirmed facts: production lines for {', '.join(confirmed_lines(facility))}; services include {', '.join(confirmed_services(facility))}. {cfg['capacity_status']}",
             "", f"Contact: {c['name']}, {c['title']}, {c['email']}, {c['phone']}.", "", "## Pages", f"- Capabilities: {cfg['domain']}/capabilities/", f"- FAQ: {cfg['domain']}/faq/", f"- Contact: {cfg['domain']}/contact/", "", "## Guides"]
    lines += [f"- {g['title']}: {cfg['domain']}/guides/{g['slug']}/" for g in guides]
    return "\n".join(lines) + "\n"


def render_sitemap(cfg: dict, paths: list[str]) -> str:
    today = date.today().isoformat()
    urls = "".join(f"<url><loc>{cfg['domain']}/{p}{'/' if p else ''}</loc><lastmod>{today}</lastmod></url>" for p in paths)
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'


def write_page(path: str, content: str) -> None:
    target = DIST / path / "index.html" if path else DIST / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def build(cfg: dict | None = None, facility: FacilityProfile | None = None, dist: Path | None = None) -> list[str]:
    """Render every page; return the list of paths written (for the sitemap and tests)."""
    global DIST
    if dist is not None:
        DIST = dist
    cfg = cfg or load_site_config()
    facility = facility or load_facility(ROOT / "config" / "facility.yaml")
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    guides = [parse_guide(p) for p in sorted((CONTENT / "guides").glob("*.html"))]
    faqs = yaml.safe_load((CONTENT / "faq.yaml").read_text(encoding="utf-8")) or []
    pages: dict[str, str] = {"": render_home(cfg, facility), "capabilities": render_capabilities(cfg, facility),
                             "guides": render_guide_index(cfg, guides), "faq": render_faq(cfg, faqs), "contact": render_contact(cfg)}
    for slug, spec in CATEGORY_PAGES.items():
        pages[slug] = render_category(cfg, facility, slug, spec)
    for guide in guides:
        pages[f"guides/{guide['slug']}"] = render_guide(cfg, guide)
    for path, content in pages.items():
        write_page(path, content)
    (DIST / "styles.css").write_text((SITE / "static" / "styles.css").read_text(encoding="utf-8"), encoding="utf-8")
    (DIST / "llms.txt").write_text(render_llms_txt(cfg, facility, guides), encoding="utf-8")
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {cfg['domain']}/sitemap.xml\n", encoding="utf-8")
    (DIST / "sitemap.xml").write_text(render_sitemap(cfg, list(pages)), encoding="utf-8")
    return list(pages)


if __name__ == "__main__":
    written = build()
    print(f"built {len(written)} pages into {DIST}")
