# Roadmap: 26 Weeks, 20 Hours a Week, Zero Budget Until Proof

Three phases with a spending gate between each. You do not buy tools until the previous phase produced the number it was supposed to.

## Phase 0: Proof (weeks 1 to 4). Budget: $0

**Goal:** 10 replies, 3 discovery calls, 1 sample request. This is the evidence you show the facility and yourself before spending money.

### Week 1: foundations (20 h)
- [ ] Send the partner `docs/05_facility_data_sheet.md`. Fill `config/facility.yaml` as answers arrive. Run `leadgen facility-check` until it passes. (2 h)
- [ ] Draft the referral agreement terms (section 4 of the data sheet doc) and send them to the partner in writing. (2 h)
- [ ] Set up sending: a Gmail on your own domain, SPF/DKIM/DMARC, plain-text signature with a physical address. Start warm-up at 10 emails a day to friends and colleagues, asking for replies. (3 h)
- [ ] Run `leadgen queries cookie`, `leadgen queries pet_treat`, `leadgen queries bakery`. Work the trade show and Google searches into a CSV using the column layout in `tests/fixtures/sample_leads.csv`. Target 150 companies. (10 h)
- [ ] `leadgen import leads/seed_list.csv`, `leadgen watch --days 30`, `leadgen enrich`, `leadgen score`. Review the top 40 by hand. (3 h)

### Week 2: first sends (20 h)
- [ ] Find contact names and emails for the top 40 (LinkedIn free, company site, email pattern guessing, Hunter free tier). (6 h)
- [ ] `leadgen draft <lead>` for each; edit the first line by hand where the engine's line is weak; paste the qualify prompt into claude.ai for the top 10 to get sharper openers. (5 h)
- [ ] Send 15 day-0 emails per day, Tuesday to Thursday, plus 10 LinkedIn connection notes per day. Log every send with `leadgen advance <lead> contacted`. (6 h)
- [ ] Add 50 more companies to the list. (3 h)

### Week 3: cadence (20 h)
- [ ] Follow-ups fire on days 3, 5, 10, 18 from the sequence. Track them in a calendar; send by hand. (5 h)
- [ ] 20 new day-0 sends per day. (6 h)
- [ ] Reply handling: within 2 hours in business time. Book discovery calls; use the checklist in `04_outreach_playbook.md`. (4 h)
- [ ] Add 50 more companies; enrich and score. (3 h)
- [ ] Warm-intro sweep: list 20 packaging, ingredient, food-safety, and broker contacts. Email each one the referral-share offer. (2 h)

### Week 4: review the proof (20 h)
- [ ] Sending and follow-ups continue at 25 per day. (12 h)
- [ ] Hold discovery calls; send sample requests to the facility the same day. (4 h)
- [ ] `leadgen report` and `leadgen export`. Compare against the gate: 10 replies, 3 calls, 1 sample. Reweight `config/icp.yaml` based on which segments replied. (2 h)
- [ ] Write a one-page proof memo for the partner with the funnel numbers and the sample in flight. (2 h)

**Gate to Phase 1:** proof numbers hit, referral agreement signed, facility data sheet complete. If replies are under 3% after 200 sends, stop and fix the message before adding volume. If replies are fine but no calls, the qualification is off: tighten the ICP.

## Phase 1: First closes (weeks 5 to 12). Budget: up to $300 a month, unlocked by the gate

**Goal:** 3 handoffs, 1 signed PO, 600 cumulative contacts.

Spend in this order, only as each becomes the bottleneck:
1. Anthropic API key ($20 to $50 a month at this volume): `leadgen qualify` and `leadgen draft --ai` on every lead over score 40.
2. Contact data (Apollo or Hunter paid tier, about $50 to $100): removes the slowest manual step, finding emails.
3. A second sending inbox plus a warm-up tool (about $30 to $100): doubles daily volume safely.

Weekly rhythm (20 h):
- Monday (4 h): `scripts/weekly_pipeline.sh` (watch, enrich, score, qualify, dossiers), add 30 to 60 leads by hand from the show and retailer lists, promote two or three to the spear bench. Plan the week's sends.
- Tuesday to Thursday (3 h each): 30 day-0 sends, follow-ups, LinkedIn, reply handling.
- Friday (4 h): discovery calls, sample chasing with the facility, `leadgen report`, scorecard, ICP reweighting.
- Every week: one LinkedIn post on capacity, MOQs, or what retail buyers require.

Milestones:
- Week 6: first sample delivered and feedback captured.
- Week 8: first handoff with pricing in the buyer's hands.
- Week 10: second and third handoffs; first PO signed or a written reason why not.
- Week 12: pipeline review with the partner. Show the referral value of what is in flight using `leadgen economics`.

**Gate to Phase 2:** at least 1 signed PO and 3 handoffs, reply rate above 5%, facility hitting the sample turnaround it promised.

## Phase 2: Scale (weeks 13 to 26). Budget: a few hundred a month, funded by the first referral payments

**Goal:** 3 closed accounts total, 1,500 cumulative contacts, a repeatable weekly machine.

- Move to a real CRM (HubSpot free) via `leadgen export`; keep this engine as the research and scoring layer.
- Multi-inbox sending through Instantly or Smartlead, 60 to 100 day-0 emails a day.
- Sales Navigator saved searches on the trigger titles (production manager, co-packer manager) and the Tier A segment.
- Add a second category push: pet brands adding human-grade treats, cookie brands adding dog treats. The "one roof" angle is unique and worth its own sequence.
- Referral-share network: brokers, packaging reps, and consultants who send you leads for a cut. Two active referrers can match your own outbound.
- Consider a part-time virtual assistant (10 h a week) for list building and follow-up logging so your 20 hours go to calls and handoffs.

Milestones:
- Week 16: 2 closed accounts.
- Week 20: first repurchase logged on account 1, which validates the two-year referral model.
- Week 26: 3 closed accounts, monthly referral income covering the tool stack several times over.

## What "done" looks like at week 26

- A list of 1,500 scored companies in the database, refreshed weekly.
- A sequence with a measured reply rate, tuned per segment.
- A facility partner who has learned to turn samples around fast because the pipeline forced it.
- Three accounts reordering, paying you every month for two years.
- A written record (exports, activities table) of every referred account, protecting your commission.
