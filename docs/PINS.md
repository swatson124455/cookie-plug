# Pins: things only you can do

Kept current as work proceeds. Each pin says what is blocked without it. Nothing here stops the rest of the build.

| # | Pin | What it unblocks | Where |
|---|---|---|---|
| 1 | Send the facility the data sheet and fill `config/facility.yaml` until `leadgen facility-check` passes | Any certification, MOQ, lead-time, or pricing claim in outreach and on calls; the capabilities one-pager | `docs/05_facility_data_sheet.md`, `docs/06_partner_kickoff.md` |
| 2 | Agree the referral term sheet in writing and get it signed | Safe to hand off the first lead | `docs/06_partner_kickoff.md` section 2 |
| 3 | Register a sending domain, set SPF/DKIM/DMARC, start the 14-day warm-up | Day-0 sends in week 2 | `docs/07_email_setup.md` |
| 4 | Your sender identity: name, title, phone, physical mailing address for the signature | Replace "[Your name]" in every draft; CAN-SPAM compliance | `.env` (`LEADGEN_SENDER_NAME`, `LEADGEN_SENDER_TITLE`) |
| 5 | The facility's name as it may be used with buyers, and who the technical contact is | Outreach currently says "a US manufacturer" | `config/facility.yaml` `name` |
| 6 | Run `leadgen import leads/seed_list.csv` then `leadgen enrich` on your own machine | This cloud session cannot reach brand websites; enrichment adds sold-out and catalog signals and moves scores | `leads/README.md` |
| 7 | Your referral percentage and term in years | Exact account values in the proof memo and prioritization | `leadgen economics --pct X --years Y` |
| 8 | Decide whether an Anthropic API key is in budget now (cents per lead) or after the proof gate | `leadgen qualify` and `draft --ai`; without it the rule-based path runs | `.env` |
| 10 | Create the facility's Keychain and PartnerSlate profiles with the partner, with you as the inbound contact, and add marketplace inbound to the referral definition | The inbound channel, the easiest win in the plan | `docs/11_inbound_demand.md` |
| 11 | Ask the partner for their declined inquiries, unsigned quotes, and lost customers from the past 24 months | The warmest leads available and the fastest route to the proof gate | `docs/11_inbound_demand.md` section 3 |
| 12 | Facility city and state | A regional pass on brands within cheap freight range | `config/facility.yaml` |
| 13 | Confirm sub-referrals are allowed under the facility agreement, so you can pay referral partners a share | Sending the referral-partner outreach in `docs/12` | `docs/06_partner_kickoff.md` section 2 |
| 14 | Decide whether to register the facility for PLMA (Nov 15 to 17, 2026) or an ECRM private-label session | The retail private-label list in `leads/retail_private_label.csv`; those buyers do not answer cold email | `docs/10_trade_show_playbook.md` |
| 15 | Widen this cloud environment's network access, or add these hosts to its allowlist: api.fda.gov, efts.sec.gov, www.sec.gov, the RSS hosts in `config/feeds.yaml`, and brand websites generally | Lets me run `leadgen watch`, `enrich`, and the live feed validation from here instead of only on your machine | Cloud environment menu in the session title bar, then Edit, then Network access |
| 16 | Ask the facility for a capacity-hold commitment for named accounts: line time reserved for a first run within a stated number of weeks of an approved sample | The one claim no competitor can make; goes into every Tier 1 follow-up | `docs/16_first_mover_plan.md` |
| 17 | Ask the facility for a sampling commitment: benchmark sample shipped within ten business days of receiving the product or spec | The first emails promise sampling in weeks; the facility has to make it true | `docs/16_first_mover_plan.md` |
| 18 | Add `ANTHROPIC_API_KEY` to this cloud environment's settings (cloud environment menu in the session title bar, then Edit, under API credentials or as an environment variable) | The weekly Routine's discover, websites, and dossier steps; without it the Routine runs only the free steps | `docs/15_infrastructure.md` section 3b |
| 19 | Optional: SMTP settings in `.env` (`LEADGEN_SMTP_HOST`, `LEADGEN_SMTP_USER`, `LEADGEN_SMTP_PASSWORD`, `LEADGEN_REPORT_TO`) if you want the local cron to email the report; the cloud Routine notifies you without this | Local emailed reports only | `.env.example` |
| 9 | Confirm which product formats the facility can run: bars, no-bake protein balls, dry mixes, soft chews, extruded kibble | Several MODERATE FIT leads in `leads/overrides.csv` hinge on this | `leads/overrides.csv` |
