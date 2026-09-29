# Seed lead list (built 2026-09-28)

**185 leads, 169 with websites, 89 with a named contact, 35 with a public email address (20 of the top 25).** Score buckets: 26 at 55 and up, 52 at 40 to 54, 107 under 40.

Research pass across Expo West 2026, Sweets & Snacks 2026, Fancy Food 2026, SuperZoo 2025/2026, Global Pet Expo 2026, retailer emerging-brand programs, funding news, retail-launch news, recalls, co-packer closures, and job postings. Every row records only facts seen in a search result, with the source URL in `notes`. Nothing here has been enriched from the brand's own website yet.

| File | What it is |
|---|---|
| `seed_list.csv` | Merged, deduped input rows with the research trigger columns. Import this with `leadgen import leads/seed_list.csv --source seed_2026_09`. |
| `seed_list_scored.csv` | The same rows scored against `config/icp.yaml`, ranked, with score reasons. Review this first. |
| `top_drafts.md` | Day-0 email drafts for the top-ranked leads. Edit the first line by hand using the evidence in `notes`. |
| `spear_list.md` | The twelve accounts worth working as accounts, ranked, with threads, the give, and a custom day-0 email each. Playbook in `docs/14`. |
| `dossiers/` | Full research dossiers behind the spear list, every fact with its URL. |
| `retail_private_label.csv` | 22 retailers with the executive who owns store brands, and their 2025-2026 store-brand expansion news. Work these through PLMA and ECRM (`docs/10`), not cold email. |
| `referral_partners.csv` | 39 brokers, packaging and label suppliers, consultants, accelerators, and pet-industry groups for the warm-intro network (`docs/12`). |
| `overrides.csv` | Hand-verified websites, contacts, fit notes, and exclusions. Add to it as you verify; `scripts/build_seed_list.py` merges it on every rebuild. |

## Segments in the list

- **Brands with triggers** (retail launch, funding, sold out, hiring, recall, co-packer closure): the core outbound list.
- **Retail private label** (`segment=retailer_private_label`): long cycle, reached at PLMA and ECRM; scored into the 40s on purpose so they do not crowd the daily send list.
- **Reshoring** (`source=reshoring`): brands whose cookies, biscuits, or treats are made in New Zealand, Canada, the UK, the Netherlands, Italy, Belgium, Denmark, Germany, Thailand, or China and sold in US retail, with tariff exposure documented in notes. Pitch a US second source.

## How to read the scores

- **55 and up:** contact in weeks 2 and 3. Right category, established or funded, with at least one live trigger.
- **40 to 54:** contact in week 4 or nurture. Right category, weaker or single trigger.
- **Under 40:** nurture list, or capped because the product is not a baked good (see "WEAK FIT" in notes).

## What still needs a human before sending

1. **Websites** for the rows that have none: search the company name, paste the domain into `overrides.csv`, rebuild.
2. **Enrichment:** run `leadgen enrich` on your machine (this cloud session cannot reach brand sites). It reads Shopify catalogs for sold-out signals and product counts and will move scores.
3. **Contact names and emails:** 35 leads carry a public address (wholesale@, hello@, or a named founder) found in search results; most are general inboxes, which founders at small brands do read. For the rest, `leadgen emails <lead>` proposes candidates and `docs/07_email_setup.md` section 6 says how to verify. Put verified addresses in `overrides.csv`.
4. **Fit check** on anything marked MODERATE or UNCERTAIN in notes, against the facility data sheet once it is complete.

## Rebuild

```bash
python scripts/build_seed_list.py path/to/research_1.csv path/to/research_2.csv ...
```

The five original research CSVs are not committed (they were session scratch files); `seed_list.csv` is their merged output and can be passed back in as the single input.
