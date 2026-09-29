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
| `docs/06_partner_kickoff.md` | Kickoff email, referral term sheet, handoff protocol |
| `docs/07_email_setup.md` | Sending domain, SPF/DKIM/DMARC, warm-up, finding emails |
| `docs/08_proof_memo_template.md` | The 30-day memo that gates tool spending |
| `docs/09_capabilities_one_pager_template.md` | Buyer-facing one-pager, filled from the data sheet |
| `docs/10_trade_show_playbook.md` | 12-month show calendar with before, during, and after plans |
| `docs/11_inbound_demand.md` | Marketplaces and communities where brands already ask for a co-packer |
| `docs/12_referral_partners.md` | Warm-intro network: who, the share offer, the outreach email |
| `docs/16_first_mover_plan.md` | Reaching the Tier 1 accounts this week without waiting on the domain |
| `docs/15_infrastructure.md` | The automated pipeline: feed sourcing, dossiers, what stays manual |
| `docs/14_spear_playbook.md` | Account-based selling for the top twelve: cadence, multi-threading, the give |
| `docs/13_decisions.md` | Open decisions with a recommendation and trade-offs for each |
| `docs/PINS.md` | Everything that needs you |

## Quick start

```bash
pip install -r requirements.txt
pip install -e .
cp .env.example .env            # optional; the engine runs without an API key

leadgen facility-check          # lists what the partner still needs to confirm
leadgen queries cookie          # search strings to build your first list
leadgen watch --days 7          # pull triggers from FDA recalls, EDGAR filings, trade press
leadgen import my_list.csv --source expo_west
leadgen import-html saved_exhibitor_page.html --source expo_west_2027 --category cookie
leadgen websites --min-score 40  # fill missing domains with Claude web search (needs a key)
leadgen enrich                  # reads public homepages and Shopify catalogs
leadgen score                   # ranks by ICP weights in config/icp.yaml
leadgen qualify                 # AI fit + opening line (rule-based without a key)
leadgen draft crumbco.com       # five-touch sequence for one lead (--ai sharpens it)
leadgen tag crumbco.com spear   # mark a spear account; then --template config/templates/spear_sequence.yaml --thread operator
leadgen list --tag spear        # leads by score, stage, or tag
leadgen emails crumbco.com      # ranked, unverified address candidates for the contact
leadgen dossier crumbco.com     # Claude + web search writes the account dossier (needs a key)
leadgen brief crumbco.com       # one-page call prep: facts, fit, history
leadgen touch crumbco.com 0     # log the day-0 send (marks the lead contacted)
leadgen due                     # follow-ups owed today, most overdue first
leadgen touch crumbco.com 3 --channel linkedin
leadgen advance crumbco.com replied --note "asked for capabilities sheet"
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
src/leadgen/      engine: models, facility, discover, sources, triggers, enrich, scoring, ai, dossier, outreach, crm, schedule, contacts, economics, cli
config/           facility.yaml (partner facts), icp.yaml (scoring weights), feeds.yaml (public sources), templates/sequence.yaml
prompts/          system prompts used by the AI layer and usable by hand
docs/             strategy documents
leads/            researched seed list (scored), overrides, and day-0 drafts
scripts/          weekly_pipeline.sh, build_seed_list.py, check_dns.py
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
