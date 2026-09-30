# AI answer-engine visibility for Open Line Co-Packing (research notes, 2026-09-30)

Method note: many primary documentation hosts (developers.google.com, developers.openai.com, docs.perplexity.ai, blogs.bing.com, ahrefs.com, searchenginejournal.com, otterly.ai) were blocked by this session's egress proxy, so page bodies could not be fetched. Findings below come from search-result snippets of those pages and from secondary reporting. Where a claim is attributed to an official doc, the URL is the official page but the wording was seen via search snippet, not read in full. Items marked "verify" should be checked against the live page before being quoted as fact. No ChatGPT, Perplexity, Copilot or Google AI Mode sessions could be run (no accounts or API keys in this environment); the buyer-query searches below were run with the WebSearch tool, which is Anthropic's own web search, so they are a rough proxy for what Claude with web search would retrieve, not for other engines.

## 1. Who gets cited today for co-packing buyer questions

### Takeaway
No published study of AI citations for co-packing queries was found. Running the target queries through a live web search shows the retrievable source pool is dominated by (a) marketplaces/directories (PartnerSlate category pages, PickYourOwn.org lists, SpecialtyFoodCoPackers, Specialty Food Resource, UC Davis extension list), (b) individual small co-packers' own "co-packing / low minimums" pages, and (c) vendor blogs (packaging firms, kitchen-rental firms, SaaS tools) that answer pricing and "vs" questions with concrete numbers. Keychain appears for definitional queries. Reddit did not surface in these runs; SFA and trade press did not surface either.

### Cited Findings
- Query "how to find a cookie co-packer" (WebSearch, 2026-09-30) returned: PickYourOwn.org US bakery co-packer list and state lists, UC Davis Food Safety co-packer contacts page, PartnerSlate /bakery/, Gold Medal Bakery "How to Find a Co-Packer" blog, mrcheckout.net "Top Private Label Bakery Co-Packers", SpecialtyFoodCoPackers.com (including a "co-packers looking for new business" capacity page and a Cookies page), Specialty Food Resource co-packer directory — [PickYourOwn](https://www.pickyourown.org/copackers-US-Bakeries.php); [UC Davis](https://ucfoodsafety.ucdavis.edu/processing-distribution/food-industry-contacts/co-packers); [PartnerSlate bakery](https://partnerslate.com/bakery/); [Gold Medal Bakery](https://www.goldmedalbakery.com/blog/how-to-find-a-co-packer/); [SpecialtyFoodCoPackers capacity page](https://www.specialtyfoodcopackers.com/CoPackers-Additional-Capacity.html); [Specialty Food Resource](https://www.specialtyfoodresource.com/find-a-business-resource/copackers/)
- The synthesized answer for that query recommended: define requirements, use directories (Comanufacturers.com, Specialty Food Resource, PickYourOwn), ask for referrals, attend trade shows, contact the state agriculture department — i.e. the "answer" is directory-and-process advice, not a named manufacturer — [same search results as above]
- Query "dog treat co-packer low minimums" returned individual small co-packers' pages: Neoteric Brands (claims orders "as small as 150 units", SQF human-grade), Natural Pet Innovations (low MOQs, "30-day concept-to-completion"), Packing Paws (CA small-batch, for brands "turned away for not meeting minimums"), Smart Cookie Barkery, Dilly's Pet, Eco Kind; plus packaging suppliers and The Underbite / PacknFresh guides that supplied the MOQ tier numbers (startup-friendly 2,000–10,000 lb vs 50,000–100,000 lb per SKU at large plants) — [Neoteric](https://www.neotericbrands.com/blogs/general/private-label-dog-treats-your-guide-to-pet-product-manufacturing); [Packing Paws](https://packingpaws.com/); [Dilly's Pet](https://dillyspet.com/pages/contract-manufacturing); [PacknFresh](https://packnfresh.com/pet-food-co-packing/); [The Underbite](https://www.theunderbite.co/product-development/pet-food-co-packer)
- Query "how much do co-packers charge per unit" returned mostly packaging/logistics co-packer blogs and a SaaS blog (GhostLabel "How Much Do Food Co-Packers Charge?"); the synthesized answer quoted specific numbers (setup fees $250–$1,500 per run, storage $25–$100 per pallet, kitting $0.40–$0.60/unit) — [GhostLabel](https://www.ghostlabel.io/blog/how-much-do-food-co-packers-charge); [Industrial Packaging](https://www.industrialpackaging.com/blog/contract-packaging-cost); [Fresh Idea](https://freshideallc.com/how-much-does-a-co-packer-cost/); [South Atlantic Packaging](https://southatlanticpackaging.com/understanding-co-packing-pricing/)
- Query "co-packer vs commissary kitchen" returned kitchen-rental businesses and SaaS blogs (Prep Kitchens, Amped Kitchens, Ardent Seller, The Food Corridor, Farmers Market Toolkit); the answer quoted concrete numbers such as shared kitchens at "$33–$45 per hour ... monthly floors from about $348" and co-packer minimums "1,000–2,000 unit minimum per SKU" — [Prep Kitchens](https://prepkitchens.com/commercial-kitchens-vs-co-packer-which-on-should-you-choose-first/); [Amped Kitchens](https://www.ampedkitchens.com/blog/food-co-packer-vs-commercial-kitchen-costs-for-small-businesses/); [Ardent Seller](https://www.ardentseller.app/blog/co-packer-vs-shared-commercial-kitchen)
- PartnerSlate runs category landing pages (bakery, snacks, pet food, chocolate) and a learning center ("What is a Co-Packer?"), claims a network of "nearly 6,000 co-manufacturers"; Keychain has "What is Co-Packing" content — [PartnerSlate pet food](https://partnerslate.com/petfood/); [PartnerSlate learning center](https://partnerslate.com/learningcenter/what-is-a-copacker/); [Keychain](https://www.keychain.com/k/b/what-is-co-packing)
- A Reddit-targeted search ("reddit co-packer small batch cookies") returned no Reddit threads at all — [WebSearch run 2026-09-30, no usable URL]

### Inferences
- The winning pattern in retrieved results is a page that states specific numbers (MOQ units, $/hour, setup fee ranges) and a clear comparison; the pages cited are often small vendors, not big brands. This is favorable for a new site whose guides already carry numbers and primary sources — but Open Line must avoid stating any facility number still marked TO_CONFIRM.
- Directory/list pages (PickYourOwn, SpecialtyFoodCoPackers, Specialty Food Resource, PartnerSlate, Comanufacturers.com) are where an answer engine "finds" named co-packers. Getting the manufacturer (or Open Line) listed there is likely a faster route into answers than the site itself ranking.
- SpecialtyFoodCoPackers has a page literally titled "co-packers looking for new business"; open capacity is exactly the facility's pitch — a listing there is a high-fit off-site mention.

### Gaps
- No live runs of ChatGPT search, Perplexity, Copilot, Google AI Overviews or AI Mode were possible; which of these sources each engine actually cites for these queries is unverified. Recommend the owner run the 5 target prompts in each engine monthly and log cited URLs (Bing Webmaster Tools AI Performance will also show Copilot grounding queries once the site has any citations).
- No published study specific to food manufacturing / co-packing citations was found.
- Whether Reddit threads (r/smallbusiness, r/foodbusiness, r/Entrepreneur) are cited for these queries in Perplexity/AI Overviews is unknown; the search tool here did not surface them.

## 2. What drives citation (per-engine source preferences, freshness, structure, mentions, indexes)

### Takeaway
Across 2025–2026 studies, a small set of UGC and reference domains (Reddit, Wikipedia, YouTube, LinkedIn) dominate AI citations, with engine-specific skews (ChatGPT toward Wikipedia/major publishers, Perplexity toward Reddit, AI Overviews toward YouTube/Reddit on top of its own index). The strongest correlational signal for being named is off-site brand mentions (especially YouTube), not backlinks. Freshness helps most in ChatGPT; content with statistics, quotes and cited sources lifted visibility in the one controlled academic test. Official Google guidance says no special markup is needed; Microsoft has said schema helps Copilot. ChatGPT is shifting from third-party indexes (including Bing) to its own index.

### Cited Findings
Source mix by engine
- OtterlyAI analyzed 1M+ citations across ChatGPT, Perplexity and Google AI Overviews (Jan–Feb 2026) — [OtterlyAI 2026](https://otterly.ai/blog/the-ai-citations-report-2026/) (body not fetched; snippet only)
- 5W "State of AI Citations 2026" (synthesis of 680M+ tracked citations; PR-agency report, methodology not verified) claims 15 domains capture 68% of AI citations and Reddit ~40% of multi-engine aggregate citation frequency; top ten: Reddit, Wikipedia, YouTube, LinkedIn, Forbes, Amazon, Business Insider, TechRadar, Reuters, NYT — [5WPR index](https://www.5wpr.com/new/5w-publishes-the-ai-platform-citation-source-index-2026-the-50-websites-that-control-ai/); [5W report](https://www.5wpr.com/research/state-of-ai-citations-2026/). Treat as vendor/PR claim.
- Profound (published 2025, data 2024–2025; verify date): Wikipedia is ChatGPT's most cited source at 7.8% of all citations; Reddit leads Perplexity at 6.6% (46.7% of its top-10-source share); AI Overviews: Reddit 2.2%, YouTube 1.9%, Wikipedia 0.6% — [Profound](https://www.tryprofound.com/blog/ai-platform-citation-patterns)
- Search Engine Land reports a study finding AI search engines cite Reddit, YouTube and LinkedIn most — [Search Engine Land](https://searchengineland.com/ai-search-engines-cite-reddit-youtube-and-linkedin-most-study-473138); Semrush 3-month most-cited-domains study — [Semrush](https://www.semrush.com/blog/most-cited-domains-ai/)
- Perplexity averages ~21.9 citations per response, nearly 4x ChatGPT (secondary compilation; verify) — [QuickSEO compilation](https://quickseo.ai/blog/ai-citation-patterns-chatgpt-claude-gemini-perplexity)

Relationship to organic rank
- Share of AI Overview cited pages also in Google's top 10 fell from 76% (mid-2025) to 38% (early 2026) per one analysis; other datasets put overlap at 17–38%; BrightEdge instead reports AIO citations from ranking pages rising 32.3% → 54.5% over 16 months — sources conflict on direction — [Search Engine Journal](https://www.searchenginejournal.com/google-ai-overview-citations-from-top-ranking-pages-drop-sharply/568637/); [BrightEdge](https://www.brightedge.com/resources/weekly-ai-search-insights/rank-overlap-after-16-months-of-aio); [seoClarity](https://www.seoclarity.net/research/aio-rankings-overlap)
- Google says AI Overviews/AI Mode "run on the same index and the same ranking and quality systems as ordinary organic results" (paraphrase in coverage of the June 2026 doc update) — [TechWyse](https://www.techwyse.com/news/ai-search/google-llms-txt-no-ranking-benefit-june-2026)

Brand mentions
- Ahrefs (75,000 brands; original 2025, verify date): branded web mentions correlate 0.664 with AI Overview brand visibility vs 0.218 for backlinks; top three correlates are off-site (mentions 0.664, branded anchors 0.527, branded search volume 0.392); bottom-half brands by mentions show a visibility "cliff" — [Ahrefs](https://ahrefs.com/blog/ai-overview-brand-correlation/)
- Ahrefs follow-up (Dec 2025, publicized May 26, 2026) extended to ChatGPT and AI Mode: YouTube mentions correlate ~0.737 with AI brand visibility, the strongest signal — [Business Wire](https://www.businesswire.com/news/home/20260526119691/en/Across-75000-Brands-YouTube-Mentions-Are-the-Strongest-Signal-of-AI-Visibility-New-Ahrefs-Report-Reveals); [The Next Web](https://thenextweb.com/news/ahrefs-youtube-mentions-ai-visibility-brand-search). Correlation, not causation.

Freshness
- Ahrefs (~17M citations across ChatGPT, Perplexity, Gemini, Copilot, AI Overviews; 2025): AI-cited pages average 1,064 days old vs 1,432 for organic results (~25.7% fresher); ChatGPT cites pages 393–458 days newer than organic; AI Overviews is the exception, citing pages ~16 days older than organic — [Ahrefs AI SEO statistics](https://ahrefs.com/blog/ai-seo-statistics/) (via snippet)
- Bing's Fabrice Canel (SMX Munich, March 2025): "Gen AIs value fresh content in particular" and recommended IndexNow to push updates — [Search Engine Land](https://searchengineland.com/microsoft-bing-copilot-use-schema-for-its-llms-453455)
- A practitioner test questions whether merely changing a page's date helps — [Elmo](https://www.elmohq.com/blog/does-changing-page-date-help-ai-citations) (not read)

Content formatting, statistics, quotes
- Princeton-led GEO paper (arXiv Nov 2023, KDD 2024): on a 10,000-query benchmark, adding quotations, statistics and source citations improved visibility in generative engine responses by roughly 30–40% relative (max, on a position-adjusted word-count metric, on 2023–24 systems) — [arXiv 2311.09735](https://arxiv.org/pdf/2311.09735); critique noting it is a max on older systems — [BLCK Alpaca critique](https://www.blckalpaca.at/en/knowledge-base/seo-geo/geo-generative-engine-optimization/the-princeton-geo-study-methodology-results-and-critique)
- Ahrefs study of 1.4M ChatGPT prompts on why ChatGPT cites one page over another — [Ahrefs](https://ahrefs.com/blog/why-chatgpt-cites-pages/) (not fetched; findings unknown)

Structured data
- Google: no new machine-readable files, AI text files, or special schema.org markup are needed to appear in AI features; structured data must match visible text; basics are crawl access, internal links, page experience, content in text form — [Google: AI features and your website](https://developers.google.com/search/docs/appearance/ai-features); [Google AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide) (seen via snippets)
- Microsoft (Canel, SMX Munich 2025): schema markup helps Microsoft's LLMs (Copilot) understand content — [Search Engine Land](https://searchengineland.com/microsoft-bing-copilot-use-schema-for-its-llms-453455); [SE Roundtable](https://www.seroundtable.com/schema-llms-copilot-bing-microsoft-39093.html)
- Search Engine Land "schema without the hype" piece (not read) — [Search Engine Land](https://searchengineland.com/schema-markup-ai-search-no-hype-472339)

Indexes behind each engine
- Microsoft Copilot grounds on the Bing index; Bing Webmaster Tools' AI Performance report (released Feb 11, 2026) shows Copilot/partner citations, cited pages, and grounding queries; Intents, Topics, Citation Share and Compare were added June 16, 2026 — [Bing Webmaster Tools help](https://www.bing.com/webmasters/help/ai-performance-9f8e7d6c); [Bing blog, June 2026](https://blogs.bing.com/search/2026/6/New-AI-Visibility-Insights-in-Bing-Webmaster-Tools-Intents-Topics-Citation-Share-Compare/)
- ChatGPT: Peec AI (Sept 2026, reverse-engineered from client events May 21–Jul 21, 2026) found a `result_source` field with OpenAI's own index ("Labrador") plus third-party scrapers (Bright, Oxylabs, "SERP"), an experiment "prefer-index-over-serp-v3" on ~8% of chats, and only 1.5% of Labrador URLs appearing in Bing's top 20 for the same fan-outs; conclusion: Bing visibility is no longer a safe proxy for ChatGPT — [Peec AI](https://peec.ai/blog/chatgpt-built-its-own-search-index); [Search Engine Watch](https://searchenginewatch.com/chatgpt-own-search-engine/); [Search Engine Land](https://searchengineland.com/chatgpt-retrieval-stack-index-cache-pages-485036). This is third-party inference, not OpenAI documentation.
- Google AI Overviews / AI Mode use Google's index (see above).

### Inferences
- For a new domain, the controllable on-site factors (answer-first, stats, cited sources, dates, schema) are already done; the binding constraint is (1) being indexed in Google, Bing and OpenAI's own crawler, and (2) off-site mentions. Effort should shift to off-site.
- YouTube's outsized signal suggests even a few short videos (line walk-through, "what a co-packer quote includes") with the brand name in title/description could matter more than more guides. This is correlational evidence.
- Because ChatGPT is building its own index, OAI-SearchBot access (not just Bing) is required.

### Gaps
- No study isolates B2B manufacturing / food co-packing queries; general-population citation shares may not transfer (Wikipedia and Forbes rarely cover "co-packer MOQ").
- The Ahrefs 1.4M-prompt ChatGPT study and the OtterlyAI report bodies could not be read.
- No controlled evidence that FAQPage schema itself increases AI citation; Google restricted FAQ rich results to authoritative government/health sites in 2023 (from background knowledge; not re-verified this session).

## 3. Is llms.txt used by any major engine?

### Takeaway
No. As of September 2026 no major engine documents consuming llms.txt for search/citation; Google explicitly says Search (including AI Overviews and AI Mode) does not use it, and server-log studies show AI crawlers almost never request it. It is harmless to keep, but it should get zero further effort.

### Cited Findings
- Google updated Search Central docs in June 2026: llms.txt files "won't harm (nor help)" visibility; site owners do not need "machine readable files, AI text files, markup, or Markdown" because "Google Search itself doesn't use them" — [TechWyse](https://www.techwyse.com/news/ai-search/google-llms-txt-no-ranking-benefit-june-2026); [Search Engine Journal](https://www.searchenginejournal.com/googles-llms-txt-guidance-depends-on-which-product-you-ask/575431/)
- Google's guidance differs by product: Lighthouse treats llms.txt as optional in an experimental "machine interaction" (agents) category — [Search Engine Journal](https://www.searchenginejournal.com/googles-llms-txt-guidance-depends-on-which-product-you-ask/575431/)
- Ahrefs study of 137,000 sites: 97% of llms.txt files got zero traffic in May 2026 (via secondary snippet) — [Hybrid Ranking summary](https://hybridranking.com/blog/llms-txt-one-year-later)
- 83 sites, 12 weeks of logs: OpenAI fetched llms.txt 7 times, Anthropic 9, Perplexity 0, while fetching robots.txt thousands of times (vendor study) — [ezy.ai](https://www.ezy.ai/research/do-ai-bots-read-llms-txt)
- Another single-site log study: 13 requests to /llms.txt, none from an AI crawler — [SaaSLinks](https://saaslinks.net/blog/llms-txt-server-log-study)
- As of mid-2026, OpenAI, Anthropic, Perplexity, Meta and Mistral publish llms.txt for their own docs but none documents consuming it on external sites (secondary) — [Codersera](https://codersera.com/blog/llms-txt-complete-guide-2026/)

### Inferences
- llms.txt may still help when a user pastes the URL into an agent or IDE tool, but that is not how buyers find co-packers.

### Gaps
- llmstxt.org itself not fetched; no vendor documentation found stating any engine uses it.

## 4. Crawler access and Bing Webmaster Tools / IndexNow

### Takeaway
Allow the search/retrieval bots (OAI-SearchBot, ChatGPT-User, PerplexityBot, Perplexity-User, Claude-SearchBot, Claude-User, Bingbot, Googlebot). Training bots (GPTBot, ClaudeBot, Google-Extended) do not control search citation; allowing them is optional (a small, speculative long-run benefit of being in model knowledge). Register in Bing Webmaster Tools (Copilot citations report) and ping IndexNow on publish; register in Google Search Console. The current draft robots.txt (`User-agent: * / Allow: /`) already allows everything; also check the host/CDN (e.g. Netlify, Cloudflare bot-blocking) is not blocking these agents.

### Cited Findings
- OpenAI: OAI-SearchBot surfaces sites in ChatGPT search; opted-out sites won't be shown in ChatGPT search answers (may still appear as navigational links); GPTBot is for training; settings are independent; OpenAI recommends allowing OAI-SearchBot and its published IP ranges — [OpenAI crawlers overview](https://developers.openai.com/api/docs/bots) (via snippet); [OpenAI help, advertiser guidance](https://help.openai.com/en/articles/20001243-advertiser-guidance-for-allowing-openai-web-crawlers)
- ChatGPT-User is OpenAI's user-triggered fetcher (listed on the same page; exact robots.txt treatment not verified this session) — [OpenAI crawlers overview](https://developers.openai.com/api/docs/bots)
- Anthropic: three bots, each with its own robots.txt token — ClaudeBot (training), Claude-User (fetches when a user asks), Claude-SearchBot (search quality/indexing); all honor robots.txt including Crawl-delay; blocking ClaudeBot does not block the other two — [Anthropic help center](https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler); [Search Engine Land](https://searchengineland.com/anthropic-claude-bots-470171)
- Perplexity: PerplexityBot surfaces/links sites in Perplexity results and is not used for foundation-model training, respects robots.txt; Perplexity-User fetches on user request and "generally ignores robots.txt" — [Perplexity crawlers docs](https://docs.perplexity.ai/docs/resources/perplexity-crawlers) (via snippet)
- Google-Extended controls use for Gemini training/grounding (Gemini Apps, Vertex AI); it "does not impact a site's inclusion in Google Search nor is it used as a ranking signal"; it does not remove content from AI Overviews/AI Mode (those are controlled by nosnippet, data-nosnippet, max-snippet, noindex) — [Anglera](https://www.anglera.com/glossary/google-extended); [SearchScore evidence page](https://searchscore.io/guides/seo/evidence/google-extended-does-not-control-search-ai-features/)
- Bing Webmaster Tools AI Performance report shows Copilot citations, cited pages and grounding queries (Feb 2026), plus Citation Share and Compare (June 2026) — [Bing WMT help](https://www.bing.com/webmasters/help/ai-performance-9f8e7d6c)
- Canel recommended IndexNow to push new/updated content because gen-AI values fresh content — [Search Engine Land](https://searchengineland.com/microsoft-bing-copilot-use-schema-for-its-llms-453455)

### Inferences
- Minimal robots.txt: keep `User-agent: * Allow: /` (covers all), plus the real sitemap URL (draft still says example.com). No need to name bots individually unless a block list is added later.
- IndexNow is cheap to add to the static build (key file + POST of changed URLs on deploy) and doubly useful because of the dated capacity status line and guide updates.

### Gaps
- Whether Google AI Mode uses any crawler beyond Googlebot: not documented in what was retrieved.
- Whether OpenAI's own index (per Peec) is fed solely by OAI-SearchBot is not documented by OpenAI.

## 5. Prioritized tactics for Open Line (with evidence strength)

### Takeaway
On-site work is largely done; the next gains come from indexing (Google, Bing, OpenAI), off-site mentions on the pages answer engines already retrieve (co-packer directories, marketplaces, Reddit, YouTube, trade/association listings), and keeping specific, dated numbers fresh. Measure with Bing AI Performance plus a monthly manual prompt log.

### Cited Findings
(Evidence per tactic is cited in sections 1–4; strength labels: D = documented by platform, S = third-party study/correlation, X = speculation/judgment.)
1. Indexing basics (D): Google Search Console + sitemap; Bing Webmaster Tools + sitemap + IndexNow on every deploy; confirm robots.txt and CDN allow OAI-SearchBot, PerplexityBot, Claude-SearchBot, Bingbot, Googlebot — [Google AI features](https://developers.google.com/search/docs/appearance/ai-features); [OpenAI bots](https://developers.openai.com/api/docs/bots); [Bing WMT](https://www.bing.com/webmasters/help/ai-performance-9f8e7d6c)
2. Get listed where answers already pull named co-packers (S/X): SpecialtyFoodCoPackers.com (incl. its "looking for new business" capacity page and Cookies category), PickYourOwn.org co-packer lists (bakery, relevant state), Specialty Food Resource, Comanufacturers.com, PartnerSlate and Keychain manufacturer profiles (the manufacturer's own profile, with its consent), state ag department co-packer lists, university extension lists (e.g. UC Davis page) — [SpecialtyFoodCoPackers](https://www.specialtyfoodcopackers.com/CoPackers-Additional-Capacity.html); [PickYourOwn](https://pickyourown.org/list_of_copackers.htm); [UC Davis](https://ucfoodsafety.ucdavis.edu/processing-distribution/food-industry-contacts/co-packers)
3. Build brand mentions (S): mentions correlate 0.664 with AIO visibility vs 0.218 for backlinks; YouTube mentions 0.737 — pursue guest quotes/data in trade press (Bakery & Snack, Petfood Industry, Food Business News), association member directories (SFA, APPA, Pet Food Institute where eligible), podcast/newsletter appearances for food founders, and a few YouTube videos — [Ahrefs](https://ahrefs.com/blog/ai-overview-brand-correlation/); [Business Wire](https://www.businesswire.com/news/home/20260526119691/en/Across-75000-Brands-YouTube-Mentions-Are-the-Strongest-Signal-of-AI-Visibility-New-Ahrefs-Report-Reveals)
4. Reddit presence, disclosed (S for Perplexity/AIO skew; X for this niche): answer genuine questions in r/smallbusiness, r/foodbusiness, r/Entrepreneur, r/dogtreats-style communities with a disclosed referral-partner identity; do not astroturf — [Profound](https://www.tryprofound.com/blog/ai-platform-citation-patterns)
5. Keep guides number-dense and dated (S): retrieved pages that won pricing and "vs" queries quoted specific ranges; GEO paper shows stats/quotes/citations lift; ChatGPT favors fresher pages. Add "last reviewed" dates and refresh quarterly; publish an original data point (e.g. anonymized quote ranges gathered from the referral pipeline) that others can cite — [arXiv GEO](https://arxiv.org/pdf/2311.09735); [Ahrefs freshness](https://ahrefs.com/blog/ai-seo-statistics/); [GhostLabel](https://www.ghostlabel.io/blog/how-much-do-food-co-packers-charge)
6. Match query phrasing (X): guide titles/H1s and FAQ questions should mirror buyer prompts verbatim ("dog treat co-packer with low minimums", "co-packer vs commissary kitchen"); the retrieved winners use those exact phrases in titles — [search results in section 1]
7. Keep schema accurate, don't expect it to be decisive (D mixed): Google says none needed; Microsoft says schema helps Copilot; ensure JSON-LD matches visible text — [Google AI features](https://developers.google.com/search/docs/appearance/ai-features); [SE Land on Canel](https://searchengineland.com/microsoft-bing-copilot-use-schema-for-its-llms-453455)
8. Stop investing in llms.txt (D/S) — see section 3.
9. Measure (D): Bing AI Performance (grounding queries, cited pages); monthly manual log of the 5 target prompts in ChatGPT, Perplexity, Copilot, Google AI Mode/AIO and Claude — [Bing WMT](https://www.bing.com/webmasters/help/ai-performance-9f8e7d6c)

### Inferences
- Realistic expectation for a new domain: directory/marketplace listings and Reddit/YouTube mentions can put the manufacturer or Open Line into AI answers within weeks; the site's own guides being cited will likely lag until they are indexed and have some mentions. (Judgment, not measured.)
- Compliance with project rules: any directory listing or Reddit/YouTube copy must follow `config/facility.yaml` — no TO_CONFIRM facts (e.g. turnaround days) stated as claims off-site either.

### Gaps
- No evidence located on how answer engines treat broker/referral sites versus direct manufacturers (possible trust discount); unknown.
- Costs/eligibility for SFA, APPA, PartnerSlate and Keychain listings for a referral partner (vs the manufacturer) not researched here.
