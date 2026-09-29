# Website, SEO, and AIO Plan: Passive Inbound Leads

Goal: a site that a founder finds when they search "cookie co-packer" at 11pm, that AI assistants cite when someone asks "how do I find a dog treat manufacturer with low minimums," and that turns that visit into a lead in the pipeline without you touching it. Outbound finds brands before they know they need you; this catches the ones already looking.

## 1. Whose site is it

**Recommendation: your own brand, not the facility's.** You control it, you can launch it this week without partner approval, and it can only make the three confirmed claims (open capacity, turnkey, one roof). Once the data sheet is complete and the partner approves, add a facility page with certifications and a named plant. If the partnership ends, the site and its rankings stay yours. Working name in the scaffold: **Cookie Plug**, memorable and already the repo name; change it in one file (`site/config.yaml`). Alternatives in decision 12.

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

## 4. Site structure

```
/                          Home: open capacity now, who it is for, three steps, capacity-check form
/capabilities              Lines, services, formats; certifications rendered only when confirmed
/cookie-co-packer          Category page (also /bakery-co-packer, /dog-treat-co-packer, /pet-food-co-packer)
/guides/                   Pillar content (below)
/faq                       Twenty real questions with plain answers, marked up as FAQPage schema
/contact                   Form plus direct email, phone, and mailing address
/llms.txt                  Plain-text summary for AI crawlers
/sitemap.xml  /robots.txt
```

Static HTML, no framework, no cookies banner needed, loads in under a second. Built by `site/build.py` from `site/config.yaml` and `config/facility.yaml`.

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

## 7. Content plan: the pillar guides

Write these first; they are the pages that rank and get cited. Drafts of the first four ship in the scaffold.

1. How to find a cookie co-packer (and what to ask on the first call)
2. Co-packer minimums, lead times, and what they actually cost
3. When to leave the commissary: the signs a brand has outgrown its kitchen
4. How to find a dog treat co-packer: certifications, formats, and the questions that matter
5. Refrigerated to shelf-stable: what changes in the recipe, the label, and the retailer conversation
6. What Sprouts, Whole Foods, and Chewy require from a new supplier
7. Second-source strategy: why one co-packer is a risk and how to add another without a fight
8. From food truck or farmers market to packaged product: the manufacturing path

One new guide every two weeks after launch. Each one answers a question a real founder asked in a reply, on Reddit, or in Startup CPG.

## 8. Conversion

- **One form, four fields:** product, monthly volume (ranges), when you need it, how it is made today. Optional email and phone. Submissions go to your inbox and a CSV; `leadgen import` takes the CSV with `--source website` and the four fields map to notes and signals.
- **Direct contact on every page:** email, phone, mailing address in the footer. Founders at two-person brands call.
- **The give, on the page:** "Send us your product; we benchmark it." Same offer as the outreach.
- **No gated PDF, no chatbot, no popup.** Friction loses these visitors.

## 9. Measurement

Plausible or GA4 (Plausible is simpler and cookie-free). Track: organic sessions by landing page, form submissions, direct email clicks, and which guide each lead read first. Search Console for queries and positions. Monthly: which queries are within striking distance (positions 5 to 20) and get a content refresh.

## 10. Launch sequence

| Week | Action |
|---|---|
| 1 | Decide brand name and domain (decision 12), fill `site/config.yaml`, build, deploy to Netlify or Cloudflare Pages, connect the domain, submit sitemap to Search Console and Bing |
| 1 | Set up the form endpoint (Netlify Forms or Formspree free tier) and the CSV export into `leadgen import` |
| 2 | Directory listings that corroborate the site (Keychain, PartnerSlate, SFA, Pet Food Processing), Google Business Profile if there is a physical address |
| 2 to 8 | One guide every two weeks; LinkedIn post for each; answer three community questions a week linking to the matching guide |
| 4 | First Search Console review; fix titles and descriptions that are not earning clicks |
| 8 | Facility page with certifications, once confirmed and approved |
| 12 | Decide on paid search (decision 13) based on which queries convert organically |

Realistic expectation: first organic leads in 8 to 12 weeks; a steady one to four inbound capacity checks a month by month six for a site in this niche, more with the guides compounding. It is a slow channel that never stops.
