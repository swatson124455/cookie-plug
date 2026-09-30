# Website, SEO, and AIO Plan: Passive Inbound Leads

Goal: a site that a founder finds when they search "cookie co-packer" at 11pm, that AI assistants cite when someone asks "how do I find a dog treat manufacturer with low minimums," and that turns that visit into a lead in the pipeline without you touching it. Outbound finds brands before they know they need you; this catches the ones already looking.

## 1. Whose site is it

**Recommendation: your own brand, not the facility's.** You control it, you can launch it without partner approval, and it can only make the confirmed claims (open capacity, turnkey, one roof). As the data sheet comes back, confirmed certifications, minimums, lead times, sampling turnaround, and location appear on the site automatically. If the partnership ends, the site and its rankings stay yours. Working name: **Open Line Co-Packing** (decision 12; "Cookie Plug" was dropped because it is an existing cookie franchise). Since September 30, 2026 the brand is a family of four sites on four domains (decision 14): Open Line Co-Packing (cookies and baked goods), Open Line Pet Co-Packing, Open Line Formulation, and Open Line Pet Formulation. Each name lives in two fields in its `site/sites/<id>/site.yaml`.

## 2. What the site must do

1. **Rank** for the searches a transitioning founder types.
2. **Be cited by AI answers** (ChatGPT, Perplexity, Google AI Overviews, Claude), which is where a growing share of "how do I find a co-packer" questions now get answered.
3. **Convert** with one low-friction ask: a capacity check form (product, monthly volume, timing, current setup) that lands in the pipeline.
4. **Never overclaim.** Pages render from `config/facility.yaml`; anything still `TO_CONFIRM` does not appear.

## 3. Keyword strategy

Intent-first. Volumes for these terms are small (tens to low hundreds a month each) and that is fine: every searcher is a buyer.

| Cluster | Example queries | Page |
|---|---|---|
| Category + co-packer | cookie co-packer, cookie contract manufacturer, bakery co-packer, brownie co-packer, granola co-packer, dog treat co-packer, dog treat manufacturer, private label dog treats, cat treat manufacturer | Category landing pages |
| Problem-aware | how to find a co-packer, co-packer minimum order quantity, co-packer cost per unit, co-packer vs commercial kitchen, outgrown commissary kitchen, shelf-stable cookies for retail | Guides |
| Retail-gate | SQF certified co-packer, co-packer for Whole Foods, what retailers require from a supplier | Guides (certification claims only once confirmed) |
| Speed | co-packer with open capacity, co-packer no waitlist, small batch co-packer, low MOQ co-packer | Home and capabilities |
| Format and change | private label cookies manufacturer, white label dog treats, refrigerated to shelf-stable cookies, food truck to packaged product | Guides |

Long-tail beats head terms here. "Low MOQ dog treat co-packer with open capacity" is a buyer; "dog treats" is not.

## 4. Site structure (built)

```
/                          Home: dated capacity status, the Capacity Facts panel, who it is for, three steps, lines, services, FAQ, guides, form
/capabilities/             Lines, services, certifications (only once confirmed), numbers (only once confirmed), what to send
/cookie-co-packer/         Line pages, also /bakery-co-packer/, /dog-treat-co-packer/, /pet-food-co-packer/, each with its own FAQ and form
/guides/                   Eight pillar guides, each answer-first with sources, an on-page contents list, and a form
/faq/                      Twenty questions in four groups, marked up as FAQPage
/about/                    Who runs it, how the referral model works, who pays us, what we will never claim
/contact/                  Direct email, phone, address, LinkedIn, and the form
/privacy/                  What the form collects and how to have it deleted
/thanks/  /404.html        Form confirmation and not-found pages (both noindex)
/llms.txt  /llms-full.txt  Plain-text summary and full text for AI assistants
/sitemap.xml  /robots.txt  /_headers
```

Static HTML, no framework, no JavaScript on the live site, self-hosted fonts (about 105 KB), no cookie banner needed. Built by `site/build.py --site <id>` from `site/shared.yaml`, `site/sites/<id>/`, `config/facility.yaml`, and `site/content/`; details in section 11.

## 5. AIO: getting cited by AI assistants

AI answers pull from pages that state facts plainly, answer the question in the first paragraph, and are corroborated elsewhere. The tactics:

1. **Answer-first writing.** Every guide opens with a two-sentence direct answer, then the detail. Every FAQ answer is one paragraph that stands alone.
2. **Structured data.** JSON-LD for Organization, Service, FAQPage, and Article on every relevant page. The scaffold includes it.
3. **`llms.txt`.** A plain-text file at the root describing who you are, what the facility makes, the confirmed claims, and the contact. Several AI crawlers read it.
4. **Corroboration off-site.** AI systems trust facts that appear in more than one place. Listings on Keychain, PartnerSlate, the Specialty Food Association directory, and Pet Food Processing's supplier directory (all in `docs/11`) say the same thing your site says. Answering co-packer questions on Reddit and in Startup CPG with a consistent description does the same.
5. **Specific numbers once confirmed.** "Minimum run 5,000 units, first sample in 10 business days" gets cited; "flexible minimums" does not. This is why the data sheet gates so much.
6. **Freshness.** A dated "capacity status" line on the home page updated monthly ("Open capacity as of October 2026: cookie and pet-treat lines") signals a live source.
7. **Author identity.** A named author with a short bio on every guide, matching your LinkedIn. AI systems and Google both weight identifiable expertise.

## 6. Technical SEO checklist

- One H1 per page, the target query in the title tag and first paragraph.
- Canonical tags, descriptive meta descriptions under 155 characters, Open Graph tags.
- Sitemap submitted to Google Search Console and Bing Webmaster Tools on launch day.
- Images with alt text, compressed; no hero video.
- Internal links from every guide to the matching category page and the contact form.
- HTTPS by default on the host; Netlify, Cloudflare Pages, and GitHub Pages all do this free.
- Core Web Vitals pass by construction: static HTML, one stylesheet, no third-party scripts except the analytics tag.

## 7. Content plan: the pillar guides (all eight written)

Each guide opens with a two-to-three-sentence short answer, cites its sources, links to related guides and the matching line page, and ends with the capacity-check form. Every regulatory or retailer fact was checked against a primary source in September 2026.

1. How to find a cookie co-packer (and what to ask on the first call)
2. Co-packer minimums, lead times, and what they actually cost
3. When to leave the commissary: signs a brand has outgrown its kitchen
4. How to find a dog treat co-packer: formats, rules, and the right questions
5. Refrigerated to shelf-stable: what changes in the recipe, label, and pitch
6. What big retailers require from a new supplier before the first order
7. Second-source strategy: why one co-packer is a risk and how to add another
8. Farmers market or food truck to packaged product: the manufacturing path

One new guide every two weeks after launch. Each one answers a question a real founder asked in a reply, on Reddit, or in Startup CPG. How to add one is in section 11.

## 8. Conversion

- **One form, on every page that matters** (home, line pages, guides, contact): what you make, monthly volume (ranges), timing, how it is made today, name, brand and website, email, optional phone and notes. A hidden field records which page it was sent from, so you know which guide produced the lead.
- **Spam:** a honeypot field plus Netlify's own filtering. No CAPTCHA.
- **Into the pipeline:** Netlify emails you each submission. Then either download the form's CSV from Netlify and run `leadgen import-form export.csv`, or set `NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID` (the four Netlify site IDs, comma-separated; pin 25) and the weekly Routine runs `leadgen import-form --netlify` itself, one site at a time (one failing site does not stop the others). Each submission becomes a lead with `source=inbound_<site>` (for example `inbound_pet`), tags `inbound`, `website`, and `site:<id>` plus any fit tags, the seeking-a-co-packer signal, and a segment from "how it is made today"; if the brand is already in the pipeline, the submission is merged into it rather than duplicated. The weekly report lists inbound leads first.
- **Direct contact on every page:** email, phone, mailing address in the footer. Founders at two-person brands call.
- **The give, on the page:** "Send us your product; the facility benchmarks it." Same offer as the outreach.
- **No gated PDF, no chatbot, no popup.** Friction loses these visitors.

## 9. Measurement

Plausible or GA4 (Plausible is simpler and cookie-free). Track: organic sessions by landing page, form submissions, direct email clicks, and which guide each lead read first. Search Console for queries and positions. Monthly: which queries are within striking distance (positions 5 to 20) and get a content refresh.

## 10. Launch sequence

| Week | Action |
|---|---|
| 1 | Clear the name and buy the domain (decision 12, pin 20), fill `site/shared.yaml` and each `site.yaml` (pin 21), connect the repo to Netlify (pin 22), connect the domain, submit the sitemap to Search Console and Bing |
| 1 | Turn on Netlify form detection and the email notification; send a test capacity check and import it with `leadgen import-form` |
| 2 | Directory listings that corroborate the site (Keychain, PartnerSlate, SFA, Pet Food Processing), Google Business Profile if there is a physical address |
| 2 to 8 | Eight guides are live at launch; add one every two weeks; a LinkedIn post for each; answer three community questions a week linking to the matching guide |
| 4 | First Search Console review; fix titles and descriptions that are not earning clicks |
| 8 | Facility page with certifications, once confirmed and approved |
| 12 | Decide on paid search (decision 13) based on which queries convert organically |

Realistic expectation: first organic leads in 8 to 12 weeks; a steady one to four inbound capacity checks a month by month six for a site in this niche, more with the guides compounding. It is a slow channel that never stops.

## 11. How the site is built and kept current

**Four sites, one engine.** One set of templates and one content pool build four sites, each on its own domain, each with its own audience wording, lines, guides, landing pages, and questionnaire:

| Site id | Brand (working) | Audience | Lines | Line pages |
|---|---|---|---|---|
| `bakery` | Open Line Co-Packing | cookie and baked-goods brands, and makers of other foods who want to ask | cookie, bakery | `/cookie-co-packer/`, `/bakery-co-packer/` |
| `pet` | Open Line Pet Co-Packing | dog-treat and pet-food brands | pet treats, pet food | `/dog-treat-co-packer/`, `/pet-food-co-packer/` |
| `formulation` | Open Line Formulation | founders with a kitchen recipe, a product to match, or a concept (human food) | cookie, bakery | `/cookie-recipe-development/`, `/bakery-product-development/` |
| `pet-formulation` | Open Line Pet Formulation | the same, for pet treats and pet food | pet treats, pet food | `/dog-treat-formulation/`, `/pet-food-formulation/` |

**Where things live.** Code: `src/leadgen/website/` (config, facts, content, forms, pages, render, SEO output, images). Settings every site shares (contact, capacity status, form provider, the family order): `site/shared.yaml`. One site's own settings, merged over the shared ones: `site/sites/<id>/site.yaml` (brand, domain, IndexNow key, lines, which line pages, guides, and landing pages it carries, and its `wording`). Its home page copy: `site/sites/<id>/home.yaml`. Its questionnaire: `site/sites/<id>/form.yaml`. Its share images: `site/sites/<id>/static/og/`. Shared copy: `site/content/` (guides in Markdown, `faq.yaml` with `sites:` tags on audience-specific answers, `categories.yaml`, `landing.yaml`). Layout: `site/templates/`. Styles, fonts, icons: `site/static/`.

**Build modes.** Every command names a site with `--site <id>`, or reads it from the `OPEN_LINE_SITE` environment variable (how each Netlify site says which one it is).

| Command | What it does |
|---|---|
| `python site/build.py --site bakery` | Production build into `site/dist/`. Stops with a list of every `TO_FILL` placeholder still in `site/shared.yaml` or that site's `site.yaml`, so a half-filled site cannot go live. A sibling's placeholders never block it |
| `python site/build.py --site bakery --draft` | The same pages with placeholders highlighted, every page `noindex`, robots.txt closed. For a private look on Netlify before launch |
| `python site/build.py --site bakery --preview FILE` | The whole site as one HTML file with in-page navigation, for review anywhere |
| `python site/build.py --images` | Redraws every site's share images and the shared icons (needs Pillow; `--site` limits it to one); commit the results |
| `python site/build.py --site bakery --indexnow` | After a deploy that changed content: tells Bing (which feeds Copilot) and the other IndexNow engines which pages to re-read. Needs the site's real domain and `indexnow_key`; the production build publishes the key file |

**Shared guides, one canonical home.** A guide can appear on several sites. The first site in the `sites:` order of `site/shared.yaml` that lists it, and has a real domain, is its home: the copies on the other sites carry `rel=canonical` to it and stay out of their sitemaps and IndexNow pings, so four domains never compete with copies of one page. Until the home site's domain is set, each copy is its own canonical. A Markdown link to a guide the site does not carry goes to the sibling that does, or becomes plain text while no sibling is live. Every footer links the other live sites.

**Questionnaires.** Each `form.yaml` lists the audience questions: a short required core (what the product is, volume, timing, and how it is made today, or the stage and goal on the formulation sites) and an optional fit section that opens on request (storage, allergens, certifications, claims, recipe status, SKU count, pack format, target price, channels; species and product type on the pet sites; on the formulation sites, whether the facility should make the product once the recipe is approved, since formulation leads to production). The template adds the contact fields, notes, the honeypot, and hidden `source_page` and `site` fields. Every site posts to the same Netlify form name, `capacity-check`; `leadgen import-form` records the site as a `site:<id>` tag and `inbound_<id>` source, keeps every answer in the lead note, and turns fit answers into tags (`fit:refrigerated`, `fit:peanut`, `need-cert:kosher`, `need:formulation`, `formulation-only`). Field names and choices are read by `src/leadgen/inbound.py`; change them together.

**What the site may say.** Facility facts come only from `config/facility.yaml`, and only once confirmed. Confirm a certification, a minimum, a lead time, a sampling turnaround, or the location there, rebuild, and the capabilities page, the Capacity Facts panel, the FAQ answers, and `llms.txt` all update. Nothing marked `TO_CONFIRM` can reach a page; the tests check every page for it.

**Monthly upkeep (pin 24).** Confirm the open lines with the facility and update `capacity.as_of` in `site/shared.yaml` (one edit covers all four sites). The date prints on every page; the build warns once it is 45 days old. After the deploys, run `python site/build.py --site <id> --indexnow` for each live site.

**Ad landing pages.** `site/content/landing.yaml` defines pages at `/lp/<slug>/`, each shown on the site whose `landings` lists it (Google and Bing for bakery and pet, Google for each formulation site). They are noindex and outside the sitemap, and the form records the page path, so each lead shows which ad channel it came from without any tracking script. Point each ad group's final URL at one.

**Extra sections on line pages.** A line in `site/content/categories.yaml` can carry `extras` (title, intro, points, optional guide slug); the cookie page uses one for shelf-stable, individually wrapped cookies and the dog-treat page one for private label versus your own recipe.

**Adding a guide.** Create `site/content/guides/<slug>.md` with this front matter, add its slug to the `guides` list of each site that should carry it (the first in family order is its canonical home), then run `python site/build.py --images` and commit everything:

```yaml
---
title: "The H1, 75 characters or less"
seo_title: "60 characters or less, with the search phrase"
description: "The meta description, 120 to 155 characters."
date: 2026-10-13
updated: 2026-10-13
category: general          # or a line page slug from site/content/categories.yaml
summary: "The direct answer in two or three sentences; AI assistants quote this."
related: [co-packer-minimums-lead-times-and-costs, second-source-co-packer-strategy]
sources:
  - title: "Primary source title"
    url: "https://..."
---
## First section (start with an H2)
```

Rules: no facility claims beyond the confirmed ones, every fact about a regulation or retailer backed by a listed source, and internal links written as `/guides/<slug>/`. The build refuses a guide with missing fields or a `related` slug that does not exist.

**Deploy (Netlify).** Create one Netlify site per domain, each connected to this repository, and set `OPEN_LINE_SITE` in each site's environment variables (`bakery`, `pet`, `formulation`, `pet-formulation`). The root `netlify.toml` builds `site/` with `python build.py` and publishes `site/dist/`. A site's first build fails on purpose until its placeholders are filled (pin 21). Launch the sites in any order; `bakery` first is best, since it is the canonical home of the shared guides. Netlify serves `404.html` and applies `_headers` (security headers and a strict content security policy) automatically. Cloudflare Pages also works (build command `pip install -r site/requirements.txt && python site/build.py`, output `site/dist`), but its forms need Formspree: set `form.provider: formspree` and paste the endpoint.

**Tests.** `tests/unit/test_website_units.py`, `tests/unit/test_website_family.py`, and `tests/integration/test_website_build.py` build all four sites in every mode and check every internal link and anchor, one H1 per page, title and description lengths, JSON-LD, the sitemap against the pages, the form wiring against the importer, and that no placeholder or unconfirmed claim appears anywhere.
