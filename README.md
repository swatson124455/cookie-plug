# cookie-plug

AI-assisted lead generation for a co-packing referral partnership. The partner facility makes cookies, baked goods, pet treats, and pet food with about 40% open capacity and full turnkey services. This repo holds the strategy and a working engine that finds, enriches, scores, and drafts outreach for the brands most likely to need that capacity, at zero cost until there is proof.

## Read first

| Document | What it is |
|---|---|
| `docs/01_game_plan.md` | Strategy: ICP, triggers, channels, messaging, process, metrics, economics, risks |
| `docs/02_roadmap.md` | 26-week plan at 20 hours a week with spending gates |
| `docs/03_lead_sources.md` | Every free source of leads and how to work it |
| `docs/04_outreach_playbook.md` | Sequences, openers, reply handling, call script, objections, handoff |
| `docs/05_facility_data_sheet.md` | Questions for the partner and the referral terms to sign |

## Quick start

```bash
pip install -r requirements.txt
pip install -e .
cp .env.example .env            # optional; the engine runs without an API key

leadgen facility-check          # lists what the partner still needs to confirm
leadgen queries cookie          # search strings to build your first list
leadgen import my_list.csv --source expo_west
leadgen enrich                  # reads public homepages and Shopify catalogs
leadgen score                   # ranks by ICP weights in config/icp.yaml
leadgen qualify                 # AI fit + opening line (rule-based without a key)
leadgen draft crumbco.com       # five-touch sequence for one lead (--ai sharpens it)
leadgen advance crumbco.com contacted --note "day 0 sent"
leadgen report                  # funnel
leadgen export pipeline.csv     # for a spreadsheet or a CRM
leadgen economics --pct 5 --annual-purchases 400000
```

CSV format: see `tests/fixtures/sample_leads.csv`. Only `company` is required; `website` unlocks enrichment. Optional boolean columns (`in_national_retail`, `recent_funding`, `recent_retail_launch`, `hiring_ops_or_production`, `sells_wholesale`, `mentions_copacker`) let research-found triggers count toward the score before enrichment runs. The committed seed list lives in `leads/`.

## Using the AI layer

With `ANTHROPIC_API_KEY` set, `qualify` and `draft --ai` call Claude (model `claude-opus-5` by default, set `LEADGEN_MODEL` to change) through structured outputs and cost cents per lead. Without a key, the same commands run rule-based logic so nothing blocks.

No key yet? Paste `prompts/qualify.md` or `prompts/draft_email.md` into claude.ai as the instructions, then paste the lead facts printed by the engine. Same prompts, same results, no bill.

## Layout

```
src/leadgen/      engine: models, facility, discover, enrich, scoring, ai, outreach, crm, economics, cli
config/           facility.yaml (partner facts), icp.yaml (scoring weights), templates/sequence.yaml
prompts/          system prompts used by the AI layer and usable by hand
docs/             strategy documents
tests/            unit, integration, fixtures (offline, 99% coverage)
data/             local SQLite pipeline (git-ignored)
```

## Tests

```bash
python -m pytest --cov=leadgen
```

All tests run offline. Network calls are mocked with `httpx.MockTransport`; the Claude client is a fake.

## Principles

- Never claim a facility fact that is still `TO_CONFIRM` in `config/facility.yaml`.
- Every lead and every stage change is logged; the activity table is the commission record.
- Zero paid tools until the proof gate in the roadmap is met.
