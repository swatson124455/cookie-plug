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

## 3. What stays manual, and why

- **Exhibitor directories.** Most are JavaScript apps behind a login or a bot wall. Pull them by hand four weeks before each show (`docs/10`).
- **LinkedIn, Amazon, Faire.** Their terms forbid scraping. The engine gives you the searches; you paste the results.
- **Email verification.** `leadgen emails` proposes addresses; a free lookup or a single test send confirms them.
- **Sending.** Deliberately manual in Phase 0. Every send is logged with `leadgen touch`, which is what makes `leadgen due` and the commission record work.

## 4. The weekly routine, end to end

```bash
scripts/weekly_pipeline.sh            # Monday: watch, enrich, score, qualify, dossier top 5, due, report, export
leadgen due                           # every morning
leadgen touch <lead> <day>            # as each send goes out
leadgen advance <lead> replied        # the moment anyone answers
```

Phase 1 upgrades, once the proof gate is met: a paid contact-data tool feeding `overrides.csv`, and a second inbox with a warm-up service. The pipeline does not change; only the inputs get richer.
