# Infrastructure: How Leads Get Found Without a Research Day

The first 185 leads and the twelve dossiers were produced by research agents run by hand. That proved the shape of the work; it is not repeatable on 20 hours a week. This is the machinery that replaces it. Everything here is free except the dossier step, which costs API dollars per lead.

## The pipeline

```
public feeds ──► leadgen watch ──► leadgen enrich ──► leadgen score ──► leadgen qualify ──► leadgen dossier ──► leadgen draft
 (FDA, EDGAR,      (triggers →        (website +          (ICP weights)      (fit + angle,        (Claude + web       (sequence,
  trade RSS)        new leads)         Shopify signals)                       AI or rules)         search, top N)      spear emails)
```

`scripts/weekly_pipeline.sh` runs the whole chain. Every stage is idempotent: rerunning updates, it does not duplicate.

## 1. `leadgen watch`: trigger sourcing from public feeds

Polls three kinds of public source, configured in `config/feeds.yaml`:

| Source | What it yields | Why it matters |
|---|---|---|
| openFDA enforcement API | Food and pet-food recalls naming the recalling firm | A recall means the current supply chain failed; the brand needs a new or second maker |
| SEC EDGAR full-text search | Reg CF (Form C) and Reg D filings mentioning cookies, dog treats, baked goods, co-packers | Every crowdfunding brand states its use of funds; "production expansion" is a buying signal, and the filing has audited revenue |
| Trade-press RSS (NOSH, PR Newswire food and pets, Pet Food Processing, Food Business News, Snack & Bakery) | Launches, retail wins, funding, closures, hires | The same headlines the research agents found, delivered daily |

Each item goes through an extractor. The rule-based one (default, free) classifies category and trigger from keywords and cuts the company name from the headline. `--ai` sends each item to Claude with structured outputs for the same decision with better judgment, falling back to the rules on any API error. Relevant items become leads with the trigger stored as a signal (`recent_retail_launch`, `recent_funding`, `hiring_ops_or_production`, `recent_recall`, `new_product_launch`) and the evidence and URL in notes. Items about companies already in the pipeline add the new trigger instead of creating a duplicate.

Run weekly: `leadgen watch --days 7`, then `leadgen score`. Expect a few dozen items a week and five to fifteen new relevant leads.

The SEC asks automated clients to identify themselves: set `LEADGEN_SEC_USER_AGENT="Your Name your@email"` in `.env`.

## 2. `leadgen dossier`: automated account research

For each lead (named, or the top N by score), Claude runs up to twelve web searches with the `web_search` server tool and writes the same dossier the spear list uses: product line, where sold, who makes it today, scale signals, trigger, people, leadership quotes, a proposed give, risks, and a fit score. Output is saved under `leads/dossiers/` and logged as an activity. The prompt is `prompts/dossier.md`.

Cost is roughly one to three dollars per dossier at current pricing, mostly search results. Run it on leads over 55 only. Needs `ANTHROPIC_API_KEY`; the pause-turn continuation is handled so long research sessions complete.

Verify before sending: the dossier says "unknown" where it found nothing, but a found fact can still be stale. Names and emails in a dossier go into `leads/overrides.csv` only after you have looked at the source.

## 2b. `leadgen import-html` and `leadgen websites`: the two gaps around sourcing

Exhibitor directories cannot be fetched by a script, but your browser can save the page. `leadgen import-html saved.html --source expo_west_2027 --category cookie` reads the saved file, keeps every outbound link whose text looks like a company name, drops social networks and the show's own domain, and imports the rest. Use `--dry-run` to review first and `--skip domain` to drop anything the filter missed. A 400-exhibitor page becomes leads in seconds instead of an afternoon.

Leads from `watch` arrive without a website, and enrichment needs one. `leadgen websites --min-score 40` asks Claude, with two web searches each, for the company's own domain and re-keys the lead when it finds one. Cents per lead; run it after `watch` and before `enrich`.

## 3. What stays manual, and why

- **Exhibitor directories.** Most are JavaScript apps behind a login or a bot wall, so the fetch is manual: open the directory, save the page, run `import-html`.
- **LinkedIn, Amazon, Faire.** Their terms forbid scraping. The engine gives you the searches; you paste the results.
- **Email verification.** `leadgen emails` proposes addresses; a free lookup or a single test send confirms them.
- **Sending.** Deliberately manual in Phase 0. Every send is logged with `leadgen touch`, which is what makes `leadgen due` and the commission record work.

## 2c. `leadgen discover`: finding brands too small for the feeds

The feeds only see brands that reach trade press. `leadgen discover cookie bakery pet_treat` runs a fixed set of discovery searches per category through Claude's web search tool (new brand launches, crowdfunding, "outgrown our kitchen", first regional retail, TikTok Shop traction, "looking for a co-packer"), asks for a JSON list of companies with evidence and URLs, validates every entry, and adds them as emerging leads with the trigger as a signal. It is the research-agent pass that built the seed list, as a command. A few dollars per run. The queries live in `src/leadgen/discovery.py`; the prompt is `prompts/discover.md`.

Two free additions in `config/feeds.yaml` reach the same population continually: Google Alerts delivered as RSS (create an alert, choose "Deliver to RSS feed", paste the URL) and Reddit search feeds for founders asking about co-packers.

## 3b. Fully automated: nothing to run by hand

Two schedulers exist; use either or both.

**Cloud Routine (already created):** "cookie-plug weekly lead pipeline" fires every Monday at 12:52 UTC in this cloud environment. It checks out the branch, checks the feeds are reachable, runs watch, discover (if an API key is in the environment), websites, enrich, score, qualify, dossiers for the top three, and the weekly report; commits the pipeline database (`leads/pipeline.sqlite3`), the report (`leads/reports/<date>.txt`), and new dossiers; pushes; and sends the summary as a push notification and email through the Routine's notifications. Until the environment's network policy allows the feed hosts (pin 15), each run reports that it is blocked and stops. Add `ANTHROPIC_API_KEY` to the environment's settings to enable discover, websites, and dossiers (pin 18).

**Local cron:** `scripts/install_cron.sh` installs a Monday 07:00 job on your machine that runs `scripts/weekly_pipeline.sh` and emails the report through `leadgen weekly-report --email` using the `LEADGEN_SMTP_*` settings in `.env` (Gmail works with an app password). Logs land in `data/logs/`.

The report (`leadgen weekly-report`) lists new leads found with their trigger, existing leads that gained a new trigger, follow-ups due, spear-account activity, and the funnel. It is saved under `data/reports/` every run.

## 4. The weekly routine, end to end

```bash
scripts/weekly_pipeline.sh            # Monday: watch, websites, enrich, score, qualify, dossier top 5, due, report, export
leadgen due                           # every morning
leadgen touch <lead> <day>            # as each send goes out
leadgen advance <lead> replied        # the moment anyone answers
```

Phase 1 upgrades, once the proof gate is met: a paid contact-data tool feeding `overrides.csv`, and a second inbox with a warm-up service. The pipeline does not change; only the inputs get richer.
