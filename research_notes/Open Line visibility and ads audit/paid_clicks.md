# Paid clicks and leads: cheapest ways to buy qualified traffic for Open Line Co-Packing (US, as of September 2026)

Research date: 2026-09-30. Method note: web search only. Direct page fetches of wordstream.com, localiq.com, support.google.com, learn.microsoft.com and ppcnewsfeed.com were blocked by the session's network proxy, so figures below come from search-result extracts of those pages and from secondary summaries. Every figure is dated and sourced; anything not sourced is labeled an estimate with its basis. Treat all third-party "2026 benchmark" blog figures (Stackmatix, Benly, Improvado, etc.) as lower-quality aggregations than WordStream/LocaliQ or platform help pages.

Repo context checked for this note: the live site's Netlify form (`site/templates/partials/macros.html`) already posts to a dedicated thank-you page (`site.url('thanks')`, template `site/templates/thanks.html`). `site/config.yaml` has `analytics_snippet` and `analytics_hosts`, and `src/leadgen/website/seo.py::content_security_policy` automatically adds the snippet's origins, hosts, and inline-script hashes to the CSP. CLAUDE.md says the live site ships no JavaScript, so adding a Google/Microsoft/Meta tag is an owner decision (see Q4).

## Q1. Typical CPCs for the target keywords, and how to get exact numbers free

### Takeaway
No published keyword-level CPC data was found for "co-packer", "co-packing", "bakery co-packer", "cookie manufacturer", "dog treat manufacturer" or "private label dog treats"; the closest published keyword figure is "food product manufacturers" at $8.63 CPC (WebFX, undated page). Category benchmarks from the WordStream/LocaliQ 2026 report (US search campaigns, April 2025 to March 2026) put relevant categories at roughly $2 to $6 per click and $30 to $94 per lead; the user can get exact bid ranges for their own keywords free in Google Keyword Planner and the Microsoft Ads planner.

### Cited Findings
- WordStream/LocaliQ 2026 Google Ads benchmarks: 13,474 US search campaigns across 23 industries, data April 2025 to March 2026. All-industry average cost per lead $66.69, ranging $26.84 to $131.63 by industry — [WordStream 2026 Google Ads Benchmarks](https://www.wordstream.com/blog/2026-google-ads-benchmarks); [LocaliQ Search Advertising Benchmarks 2026](https://localiq.com/blog/search-advertising-benchmarks/)
- 2026 (Apr 2025 to Mar 2026) Industrial & Commercial: CPC $5.87, CTR 6.57%, conversion rate 8.20%, CPL $75.19 — [WordStream 2026](https://www.wordstream.com/blog/2026-google-ads-benchmarks); [LocaliQ 2026](https://localiq.com/blog/search-advertising-benchmarks/)
- 2026 Business Services: CPC $5.87, CTR 6.10%, CVR 4.85%, CPL $93.69 — [WordStream 2026](https://www.wordstream.com/blog/2026-google-ads-benchmarks) (figures from search extract; the identical $5.87 CPC for two categories could be a transcription artifact and should be checked on the page)
- 2026 Restaurants & Food: CPC $2.05, CTR 6.83%, CVR 8.05%, CPL $30.57 — [WordStream 2026](https://www.wordstream.com/blog/2026-google-ads-benchmarks)
- 2026 Animals & Pets: CPC $4.06, CTR 7.49%, CVR 16.22%, CPL $31.50 — [WordStream 2026](https://www.wordstream.com/blog/2026-google-ads-benchmarks). Note: these two consumer categories are mostly consumer-facing advertisers (restaurants, pet services), so they understate B2B manufacturing CPCs.
- Keyword-level (undated agency page): "food product manufacturers" CPC $8.63; "beverage manufacturing companies" CPC $4.39 — [WebFX: PPC for Food and Beverage Manufacturing](https://www.webfx.com/industries/food-beverage/food-beverage-manufacturing/ppc/)
- Manufacturing PPC agency ranges (undated, secondary): average manufacturing CPC cited as $2.59; general industrial search CPC $2.56; manufacturing keywords "typically $2 to $8", competitive B2B manufacturing $5 to $15+ — [WebFX: PPC for manufacturing companies](https://www.webfx.com/blog/manufacturing/ppc-for-manufacturing-companies/); [NPWS: PPC for Manufacturers](https://www.npws.net/blog/ppc-for-manufacturers) (search-extract attribution across several agency pages; treat as rough)
- Consumer term "dog treats": 174,500 global monthly searches, CPC $2.66, paid difficulty 100 (undated tool page). This is a consumer query and should be a negative/avoid term, not a target — [AdTargeting: Pet Products Keywords](https://adtargeting.io/industry/pet-products-keywords)
- A 2026 all-industry average search CPC of $5.42 was reported in search results (attribution to a specific study not verified) — [Webtonic: What is cost per click](https://www.webtonic.io/blog/what-is-cost-per-click)
- Google Search CPCs rose only about 1% year over year in Q2 2026 while spend rose 14% (Tinuiti Q2 2026 Digital Ads Benchmark Report) — [Tinuiti Q2 2026](https://tinuiti.com/research-insights/research/digital-ads-benchmark-report/); [Karooya summary](https://www.karooya.com/blog/digital-ads-benchmark-report-by-tinuiti-q2-2026-key-highlights/)
- Keyword Planner is free with a Google Ads account; you can choose "Skip campaign creation" at sign-up and reach the planner without running ads. The "Top of page bid (low range / high range)" columns show bid estimates — [Analytify: Keyword Planner without an ad](https://analytify.io/how-to-use-google-keyword-planner-for-free/); [Google: Keyword Planner](https://business.google.com/us/ad-tools/keyword-planner/)
- Without active spend, Keyword Planner shows search volume in broad ranges (for example "1K to 10K") and may limit bid detail — [Backlinko: Google Keyword Planner guide](https://backlinko.com/google-keyword-planner); [Rankdots](https://rankdots.com/blog/google-keyword-planner)

### Inferences
- Working estimate for Google Search CPC on Open Line's high-intent terms: about $3 to $9 per click (estimate; basis: Industrial & Commercial and Business Services $5.87, Animals & Pets $4.06, "food product manufacturers" $8.63). Pet-treat manufacturing terms may run higher than cookie/bakery terms because pet-food private label has many agency and marketplace bidders (unverified; confirm in Keyword Planner).
- Search volume, not CPC, is likely the binding constraint: terms like "bakery co-packer" and "dog treat co-packer" are probably low-volume, so a $10/day budget may not fully spend on exact/phrase match. That is acceptable; do not loosen to broad match just to spend.
- Free way to get exact numbers, step by step: (1) create a Google Ads account, choose Skip campaign creation (and expert mode if prompted); (2) Tools > Keyword Planner > "Get search volume and forecasts", paste the keyword list, set location United States, language English, last 12 months; (3) read "Top of page bid (low/high range)" and use the Forecast tab to see projected clicks/cost at $10/day; (4) repeat in the Microsoft Advertising keyword planner (Tools > Keyword planner) — Microsoft's tool is also free with an account (not verified this session). Record results in the repo so the plan can be re-costed.
- Suggested keyword list to price (all as exact and phrase): co packer, co-packer, co packing, co-packing, food co packer, bakery co packer, cookie co packer, cookie manufacturer, private label cookies, contract bakery, contract food manufacturer, food contract manufacturing, dog treat manufacturer, private label dog treats, pet treat co packer, pet food co packer, private label pet food, contract pet food manufacturer, small batch co packer, co packer minimums.

### Gaps
- No published US CPC or volume for any of the seven named keywords was found (Semrush/Ahrefs data is behind login; free Semrush checker could not be run from this session). The owner must pull these from Keyword Planner.
- The WordStream/LocaliQ 2026 table could not be fetched directly; industry rows are from search extracts. No "Food & Beverage manufacturing" or "B2B" row exists in that report as far as the extracts show.

## Q2. Platform comparison: Microsoft vs Google, LinkedIn, Reddit, Meta, Quora and niche options

### Takeaway
Search (Google, then Microsoft) is the cheapest source of qualified leads because it captures founders already looking for a co-packer; Microsoft is usually 30 to 35% cheaper per click and uniquely lets you layer LinkedIn industry/company/job-function data onto search, though its CPCs rose 19% year over year in Q2 2026. LinkedIn has the best B2B targeting but costs about $5 to $15 per click with a $10/day minimum; Reddit and Meta are cheap per click but reach people who are not searching, so lead quality is uncertain.

### Cited Findings
Microsoft (Bing) Ads
- Microsoft Ads average CPC reported 33% lower than Google ($1.37 Microsoft Search Network vs $2.06 Google Search); a B2B/SaaS comparison in the same result set gives $2.25 vs $3.44 (34% lower). These all-industry dollar figures are much lower than WordStream's and come from a different dataset; use only the relative difference — [Improvado: Bing Ads vs Google Ads 2026](https://improvado.io/blog/bing-ads-vs-google-ads); [The Ad Spend: Google vs Microsoft 2026](https://theadspend.com/blog/google-ads-vs-microsoft-ads-2026)
- Microsoft CPCs rose 19% year over year in Q2 2026 versus about 1% for Google Search (Tinuiti Q2 2026) — [Digital Applied summary of Tinuiti Q2 2026](https://www.digitalapplied.com/blog/q2-2026-digital-ad-benchmarks-tinuiti-report-analysis); [Karooya summary](https://www.karooya.com/blog/digital-ads-benchmark-report-by-tinuiti-q2-2026-key-highlights/)
- Microsoft Advertising LinkedIn profile targeting: Company, Industry and Job function; set per ad group with a bid adjustment; "Bid only" (adjust bids, show to everyone) or "Target and bid" (show only to matching LinkedIn members). Microsoft is the only platform besides LinkedIn with this data — [Microsoft Learn: LinkedIn profile targeting](https://learn.microsoft.com/en-us/advertising/msa-help/hlp_ba_conc_linkedintargeting); [Optmyzr: LinkedIn targeting in Microsoft Ads](https://www.optmyzr.com/blog/linkedin-targeting-microsoft-ads-b2b/)

LinkedIn Ads
- Minimum $10/day per campaign and $100 lifetime minimum — [Flying V Group: LinkedIn ads minimum budget](https://www.flyingvgroup.com/linkedin-ads-minimum-budget/); [Factors.ai](https://www.factors.ai/blog/understanding-linkedin-ads-budget)
- 2026 CPC benchmarks (secondary aggregators): about $5 to $9 for sponsored content; range $4.50 to $15 (median $7.50); $2.29 for Thought Leader Ads up to $24+ for C-suite targeting. CPM $25 to $65 (median $38); one source gives US average CPM $62.67 — [ClickMinded LinkedIn benchmarks](https://www.clickminded.com/linkedin-ads-benchmarks/); [Benly LinkedIn benchmarks 2026](https://benly.ai/learn/linkedin-ads/linkedin-ads-benchmarks); [Stackmatix LinkedIn cost 2026](https://www.stackmatix.com/blog/linkedin-ads-cost); [AdLibrary LinkedIn costs 2026](https://adlibrary.com/posts/linkedin-advertising-costs-2026)
- Lead Gen Forms (2026, mostly B2B SaaS data): CPL $75 to $200 typical, $68 to $200 range; form conversion rate 8% (low) to 14% (median) to 25% (high); reported 30 to 50% lower CPL than sending to a landing page — [Stackmatix LinkedIn CPL benchmarks](https://www.stackmatix.com/blog/linkedin-ads-cost-per-lead-benchmarks); [Benly](https://benly.ai/learn/linkedin-ads/linkedin-ads-benchmarks); [Cleverly](https://www.cleverly.co/blog/linkedin-lead-generation-cost)
- Targeting: company size, job titles, job function, seniority, industries, company names, skills, groups; job-title targeting is the most expensive, industry + company size the most cost-efficient — [Improvado LinkedIn guide 2026](https://improvado.io/blog/linkedin-advertising-guide); [TripleDart LinkedIn cost 2026](https://www.tripledart.com/saas-ppc/linkedin-advertising-cost)

Reddit Ads
- Minimum $5/day per campaign, $25 lifetime; campaigns under about $20/day often struggle to deliver and exit learning — [Stackmatix: Reddit minimum budget 2026](https://www.stackmatix.com/blog/reddit-ads-minimum-budget-requirements-2026); [AdWave: Reddit costs for SMB](https://adwave.com/resources/reddit-ad-costs-targeting-smb)
- 2026 costs (secondary): CPC roughly $0.50 to $4.00, median $1.25 to $1.85 (another source says $0.30 to $1.50); CPM $3 to $15, median about $6.50. Niche-community CPM about $3.50 vs $5.50 for popular communities; communities of 50K to 200K members run 30 to 50% below median CPM — [Benly: Reddit ads cost 2026](https://benly.ai/learn/reddit-ads/reddit-ads-cost-benchmarks); [Stackmatix Reddit pricing 2026](https://www.stackmatix.com/blog/reddit-ads-cost-pricing-guide-2026); [AdWave](https://adwave.com/resources/reddit-ad-costs-targeting-smb)
- Targeting: community targeting (people who subscribed to or visited chosen subreddits in the last 28 days), keyword targeting (posts/comments containing phrases; Reddit data says adding keywords raises CTR 29.6%), conversation targeting added in 2026; conversation placement shows ads inside comment threads; Lead Gen Ads format exists — [Stackmatix: Reddit targeting 2026](https://www.stackmatix.com/blog/reddit-ads-targeting-options-2026); [Firebrand: Reddit B2B 2026 (Aug 2026)](https://www.firebrand.marketing/2026/08/reddit-ads-best-practices-for-b2b-in-2026/); [Aimers: Reddit ad types](https://aimers.io/blog/reddit-ads-types)

Meta (Facebook/Instagram)
- LocaliQ/WordStream 2026 Facebook benchmarks (US): traffic campaigns CPC $0.60, CTR 1.93%; lead campaigns CTR 2.70%, CPC $1.80, CVR 8.54%, cost per lead $27.39; overall CPM $7.26 — [LocaliQ Facebook benchmarks 2026](https://localiq.com/blog/facebook-advertising-benchmarks/); [WordStream Facebook benchmarks 2026](https://www.wordstream.com/blog/facebook-ads-benchmarks-2026)
- Targeting changes: detailed-targeting exclusions removed from ad sets March 31, 2025; from June 23, 2025 Meta consolidated narrow interests into broader groups; ad sets using removed options stopped delivering January 15, 2026; in 2026 detailed targeting mostly acts as a suggestion under Advantage+ Audience. Broad clusters like "Small business owner" and "Entrepreneurship" remain the suggested levers — [Social Media Today: exclusions removed](https://www.socialmediatoday.com/news/meta-removes-detailed-targeting-exclusions-from-ad-campaigns/723389/); [Social Media Today: consolidation](https://www.socialmediatoday.com/news/meta-removes-more-detailed-ad-targeting-options-facebook-instagram/757856/); [AdvLaunch: detailed targeting removed 2026](https://advlaunch.us/blog/meta-detailed-targeting-removed-2026); [Conversios: Advantage+ vs detailed 2026](https://www.conversios.io/blog/meta-advantage-audience-vs-detailed-targeting-2026-guide/)

Quora and other niche
- Quora: $5/day campaign minimum, no account minimum or commitment; B2B CPC claims $1.50 to $4 (another source $0.50 to $1.80); Quora itself says it publishes no fixed CPC/CPL. Sources are agencies or Quora's own marketing pages — [Stackmatix Quora guide](https://www.stackmatix.com/blog/quora-ads-guide); [Improvado Quora guide 2026](https://improvado.io/blog/quora-ads-guide); [Quora Business](https://business.quora.com/advertising/for-advertisers)

### Inferences
- Cheapest-first ranking for qualified leads (estimate; basis: intent plus cost figures above): (1) Google Search exact/phrase on co-packer terms, paid largely with new-advertiser credit; (2) Microsoft Search, imported from Google, with LinkedIn Industry targeting as "Bid only" +bid for Food and Beverage Manufacturing/Retail/Consumer Goods style industries and job functions like Entrepreneurship/Business Development/Operations; (3) search retargeting and display retargeting of site visitors once the audience is big enough; (4) Reddit community + keyword targeting on founder and food-business communities (candidates to verify in Reddit's picker: r/smallbusiness, r/Entrepreneur, r/startups, and any food-business or pet-business subreddits that exist); (5) Meta lead ads with a broad "Small business owner"/"Entrepreneurship" cluster; (6) Quora on questions about co-packers and starting a food brand; (7) LinkedIn last, or only Thought Leader Ads boosting the founder's own posts.
- Meta's $27.39 average CPL is cheap but is an all-industry average dominated by consumer offers; with interests now treated as suggestions, a co-packing ad will reach many hobby bakers and pet owners. Expect a low qualified share (estimate).
- LinkedIn at $10/day would consume the whole $300/month budget for roughly 20 to 65 clicks (estimate: $300 / $4.50 to $15). Not a first test.

### Gaps
- No platform-published benchmark exists for LinkedIn's "Food and Beverage Manufacturing" industry specifically, and the industry label's exact name in LinkedIn's current taxonomy was not verified this session. LinkedIn's minimum audience size (commonly cited as 300 members) was not verified.
- No sourced data on niche paid options specific to food/pet founders (for example sponsored placements in food-startup newsletters, trade directories, or pet-industry trade media rates). Worth a separate check.
- No Microsoft-published CPC benchmark for food or manufacturing categories was found.

## Q3. Free ad credits and grants as of 2026

### Takeaway
Both Google and Microsoft currently offer spend-match credits to new US advertisers, and together they could roughly double or triple a $300 to $600 test; terms change often and sources conflict on details, so the owner should read the offer shown inside the new account before spending.

### Cited Findings
- Google (May 2026, limited time): new advertisers earn $2 credit per $1 spent in the first 60 days, up to caps; $500 spend unlocks $1,000 credit; $680 unlocks $1,360; $1,400 unlocks $2,800 — [ALM Corp: Google Ads 2x credit for new accounts](https://almcorp.com/blog/google-ads-2x-credit-new-accounts/); [PPC News Feed, May 2026](https://ppcnewsfeed.com/ppc-news/2026-05/get-2-ads-credit-new-google-ads-accounts/)
- Google's standard Partner-offer tiers (1:1 at the low end): spend $500 in 60 days get $500; $680 get $630; $1,400 get $980; $3,200 get $1,600; up to $12,000 get $6,000 — [Google Ads Help: About Google Partners promotional offers](https://support.google.com/google-ads/answer/15329625?hl=en-AU); [ALM Corp: Partners offers 2026](https://almcorp.com/blog/google-partners-promotional-offers/). This conflicts with the 2x figures above; which applies depends on the offer shown in the account at signup.
- Google conditions: account must be new (sources say within 20 days of creation, or apply within 14 days of first impression — conflicting); spend must be met within 60 days; credit posts up to about 30 to 35 days after meeting spend; credit does not pay for costs before it was applied or count toward the spend requirement — [Google Ads Help: About promotional offers](https://support.google.com/google-ads/answer/6388096?hl=en); [Google Ads Help: offers and payment methods](https://support.google.com/google-ads/answer/16915411?hl=en); [ALM Corp](https://almcorp.com/blog/google-ads-2x-credit-new-accounts/)
- Microsoft (2026, US accounts): spend $250 and receive $500 credit (2:1); a separate "spend $25, get $100" offer is also reported. Credit expires 90 days after award; one offer per new customer; new means no prior active Microsoft Advertising account — [Adcore: Microsoft Ads credits for new advertisers](https://www.adcore.com/blog/microsoft-ads-credits-how-new-users-claim-free/); [Adcore: Microsoft Ads 2026 Q&A](https://www.adcore.com/blog/microsoft-ads-coupons-qna/); [Microsoft Q&A: ad credits for new customers](https://learn.microsoft.com/en-us/answers/questions/2289777/microsoft-ad-credits-for-new-customers)

### Inferences
- A $300/month Google-only test spends about $600 in 60 days, which clears the $500 tier: that is $500 (1:1) or $1,000 (2x offer, if still live) of credit usable in months 3 to 4 (estimate from the tiers above).
- Microsoft's $250 threshold is reached in about 50 days at $5/day, earning $500 that must be used within 90 days; at $5/day that credit would not be fully used in 90 days, so raise Microsoft's daily budget once credit posts (inference).
- Google Ad Grants is for nonprofits and does not apply to a for-profit referral business (general knowledge; not re-verified this session).
- Ask in any account-manager or onboarding call whether a current offer is available; do not buy through third-party "coupon" sites.

### Gaps
- No verified current LinkedIn, Reddit, Meta or Quora new-advertiser credit terms were found. These platforms sometimes offer credits via email or in-app; not documented here.
- Google's two offer structures (2x vs Partner tiers) and the eligibility window (20 days vs 14 days) conflict across sources; the in-account offer is authoritative.

## Q4. Tactics to keep costs low, including conversion tracking on the Netlify thank-you page

### Takeaway
Keep spend on exact and phrase match for manufacturer-intent terms, load a large negative list (jobs, recipes, consumer shopping), restrict to the US and business hours, and track every form submission as a conversion; the site already redirects Netlify form posts to a thank-you page, which is the most reliable conversion trigger, but tracking it in Google/Microsoft requires adding their tag, which is a deliberate exception to the site's no-JavaScript rule.

### Cited Findings
- Match types: broad is Google's default and matches related searches without the words; phrase matches queries containing the phrase meaning; exact matches the same meaning including close variants (plurals, misspellings, reorderings) — [Google Ads Help: close variants](https://support.google.com/google-ads/answer/9342105?hl=en); [Store Growers: match types 2026](https://www.storegrowers.com/keyword-match-types/)
- Negative keywords can be broad, phrase or exact, and do not match close variants, so singular and plural must both be added ("recipe" and "recipes") — [Google Ads Help: About negative keywords](https://support.google.com/google-ads/answer/2453972?hl=en); [Store Growers: negative match types](https://www.storegrowers.com/negative-keyword-match-types/)
- Thank-you-page tracking is the recommended form conversion method because a form-submit trigger can misfire, while a page view of /thank-you only happens after a real submission; implement as a Google Ads conversion tag firing on the thank-you URL — [Growmyads: conversion tracking for lead forms](https://growmyads.com/google-search/setting-up-google-ads-conversion-tracking-for-lead-form-submissions/); [Analytics Mania: thank-you page tracking](https://www.analyticsmania.com/thank-you-page-tracking-google-tag-manager/)
- LinkedIn Lead Gen Forms convert 3 to 5x landing pages and cut CPL 30 to 50% (B2B SaaS data) — [Stackmatix LinkedIn CPL](https://www.stackmatix.com/blog/linkedin-ads-cost-per-lead-benchmarks)
- Reddit keyword targeting improves CTR 29.6% vs community/interest alone (Reddit data) — [Stackmatix: Reddit targeting 2026](https://www.stackmatix.com/blog/reddit-ads-targeting-options-2026)

### Inferences
- Keywords: exact and phrase only at launch; no broad match or AI Max until 15 to 30 tracked conversions exist (estimate, common practice). Bid with Manual CPC or Maximize Clicks with a CPC cap (for example $8) until conversions exist, then test Maximize Conversions.
- Starter negative list (recommendation, phrase match unless noted): job, jobs, career, careers, hiring, salary, resume, internship, near me (test), recipe, recipes, homemade, how to make, DIY, cottage food, license, course, class, pdf, definition, what is, meaning, cheap, free, coupon, buy, for sale, amazon, walmart, chewy, delivery, gift, box, bulk (test), wholesale (test: retail buyers, not brands), equipment, machine, oven, packaging supplies, boxes, labels, co packing jobs, warehouse, 3PL, fulfillment, cannabis, CBD, THC, beverage, brewery, supplement, cosmetics. Review the search-terms report twice weekly for the first month.
- Geo: United States, "presence" (people in the location) rather than "presence or interest". Ad schedule: Monday to Friday, about 7am to 7pm across US time zones, since buyers are founders at work (estimate). Devices: keep mobile, but check CPL by device after 30 days.
- Ads: qualify in the copy to repel non-buyers and save clicks, for example "Co-packer for cookie and pet-treat brands. Open capacity. Minimums from X" (only use confirmed facility facts; nothing marked TO_CONFIRM in `config/facility.yaml`).
- Separate campaigns or ad groups for Bakery/Cookie and Pet treat/Pet food so budgets and CPCs can be compared and each gets its own landing page.
- Conversion tracking options, in order of reliability:
  1. Add the Google tag (and Microsoft UET tag if running Microsoft) via `analytics_snippet` and list their hosts in `analytics_hosts` in `site/config.yaml`; the CSP builder in `src/leadgen/website/seo.py` already whitelists snippet origins and hashes inline scripts. Fire the conversion on the thanks page only. This breaks the "no JavaScript on the live site" rule, so it needs owner sign-off (and a privacy-page update).
  2. No-JS fallback: one landing page per channel (for example /lp/google-bakery, /lp/bing-pet) whose Netlify form carries a hard-coded hidden field such as `source=google-bakery`; count leads per channel from Netlify submissions (`leadgen inbound`). Google cannot optimize bids without a tag in this mode, so stay on Manual CPC. Use UTM parameters on final URLs for the owner's own records.
  3. Offline conversion import to Google Ads requires the GCLID, which cannot be captured into a static form without JavaScript; not an option under the current no-JS rule (inference).
- Retargeting: needs a tag (same decision as above) and a minimum audience size before lists serve; skip until the site has steady traffic (estimate).
- Lead-form ads (LinkedIn Lead Gen Forms, Meta Instant Forms, Reddit Lead Gen Ads) avoid the site and the tag question entirely, but leads land in each platform and must be exported to `leadgen inbound`/CRM; add a qualifying question (brand stage, product category, monthly volume) to filter hobbyists.

### Gaps
- Current minimum remarketing-list sizes for Google Search and Display were not verified this session.
- Whether Netlify form submission records include the referring URL (which would let the no-JS mode attribute GCLID-tagged landings) was not verified.

## Q5. Recommended $300/month and $600/month test plans with expected clicks and leads

### Takeaway
Estimate only: $300/month on Google Search should buy roughly 33 to 100 clicks and about 1 to 6 form leads a month; $600/month across Google, Microsoft and a small Reddit test should buy roughly 100 to 450 clicks and about 1 to 15 leads, with most qualified leads expected from search. New-advertiser credits could fund months 3 and 4. Even one closed customer (thousands to tens of thousands of dollars a year in commission) would pay for the whole test several times over.

### Cited Findings
- Google CPC basis: Industrial & Commercial and Business Services $5.87, Animals & Pets $4.06, Restaurants & Food $2.05 (US, Apr 2025 to Mar 2026) — [WordStream 2026](https://www.wordstream.com/blog/2026-google-ads-benchmarks); keyword "food product manufacturers" $8.63 — [WebFX](https://www.webfx.com/industries/food-beverage/food-beverage-manufacturing/ppc/)
- Google conversion-rate basis: Business Services 4.85%, Industrial & Commercial 8.20% — [WordStream 2026](https://www.wordstream.com/blog/2026-google-ads-benchmarks)
- Microsoft CPC about 33% below Google but up 19% year over year in Q2 2026 — [Improvado](https://improvado.io/blog/bing-ads-vs-google-ads); [Digital Applied on Tinuiti Q2 2026](https://www.digitalapplied.com/blog/q2-2026-digital-ad-benchmarks-tinuiti-report-analysis)
- Reddit CPC $0.50 to $4 (median $1.25 to $1.85), $5/day minimum — [Benly](https://benly.ai/learn/reddit-ads/reddit-ads-cost-benchmarks); [Stackmatix](https://www.stackmatix.com/blog/reddit-ads-minimum-budget-requirements-2026)
- Credits: Google $500 spend in 60 days unlocks $500 (1:1 tier) or $1,000 (May 2026 2x offer); Microsoft $250 unlocks $500, 90-day expiry — [ALM Corp](https://almcorp.com/blog/google-ads-2x-credit-new-accounts/); [Google Partners offers](https://support.google.com/google-ads/answer/15329625?hl=en-AU); [Adcore](https://www.adcore.com/blog/microsoft-ads-credits-how-new-users-claim-free/)

### Inferences
All numbers in this section are estimates. Assumptions stated per line.

Assumptions shared by both plans
- Google CPC $3 to $9 (basis above). Google landing-page conversion rate 2% to 6%: set below the 4.85% to 8.2% benchmarks because the site is a new, unknown referral brand with no reviews and the offer is a high-consideration B2B decision.
- Microsoft CPC $2 to $6 (about 30% below Google, tempered by the +19% trend); same 2% to 6% conversion rate.
- Reddit CPC $0.50 to $4; conversion rate 0.5% to 2% (cold audience that is not searching).
- Qualified share of form leads (real brand, in category, plausible volume): 30% to 60% for search, 10% to 30% for Reddit/Meta (estimate, no benchmark found).
- Low-volume keywords may cap spend below budget; that is fine.

Plan A: $300/month (about $10/day)
| Channel | Budget | Clicks/month | Form leads/month | Implied CPL |
|---|---|---|---|---|
| Google Search, exact+phrase, two ad groups (bakery/cookie, pet treat/food) | $300 ($10/day) | 33 to 100 | about 1 to 6 | about $50 to $450 |
- Qualified leads: about 0 to 4 a month.
- Credit: about $600 spent by day 60 clears the $500 tier, so $500 to $1,000 credit arrives around day 90 and funds months 3 to 4 at the same pace.
- Weeks 0 to 1 before spend: pull Keyword Planner data, confirm volume exists; if forecast clicks at $10/day are under about 30/month, add Microsoft rather than broadening match.

Plan B: $600/month (about $20/day)
| Channel | Budget | Clicks/month | Form leads/month |
|---|---|---|---|
| Google Search (as Plan A, plus a third ad group for "contract manufacturer" generic terms) | $300 ($10/day) | 33 to 100 | about 1 to 6 |
| Microsoft Search, imported from Google, LinkedIn Industry "Bid only" +20 to +40% | $150 ($5/day) | 25 to 75 | about 0.5 to 4.5 |
| Reddit, community + keyword targeting, conversation placement, sends to a channel landing page | $150 ($5/day, the minimum) | 37 to 300 | about 0 to 6 |
| Total | $600 | about 95 to 475 | about 1.5 to 16 |
- Qualified leads: roughly 1 to 7 a month, most from search.
- Credits: Google as Plan A; Microsoft's $250 threshold is met around day 50, giving $500 to use within 90 days (raise Microsoft to about $10/day while credit lasts).
- Reddit at $5/day is below the roughly $20/day level sources say is needed for stable delivery, so treat it as a 30-day creative and audience probe; cut it if cost per qualified lead exceeds search after 30 days.
- Alternative for Plan B if the owner prefers fewer platforms: $450 Google + $150 Microsoft, no Reddit.

Decision rules (estimate-based)
- After 60 days (or about 100 search clicks), keep a channel if cost per qualified lead is under about $300, given customer value of thousands to tens of thousands a year.
- Zero leads from 100+ targeted search clicks points to the landing page or offer, not the channel; fix the page before adding spend.
- Only after search proves demand: test Meta lead ads (broad Small business owner/Entrepreneurship cluster, qualifying questions) and LinkedIn Thought Leader Ads or Lead Gen Forms at the $10/day minimum.

### Gaps
- No benchmark for the conversion rate of a new B2B referral site; the 2% to 6% assumption is a judgment and should be replaced with the first 60 days of data.
- Actual click volumes depend on keyword search volume, which is not published for these terms; Keyword Planner forecasts are needed before launch.
