# Open Decisions

Each one has a recommendation. Nothing here blocks the build; each blocks a specific step of execution, named in the first line.

## 1. Sending domain and mailbox (blocks week-2 sends)
**Recommendation:** buy a variant domain (about $12) and one Google Workspace mailbox (about $7 a month). Treat it as the one exception to the zero-dollar phase.
- Pro: protects your main domain; authenticated mail lands in the inbox; Workspace mailboxes warm faster than free Gmail.
- Con: roughly $100 for the year before proof exists.
- Alternative: free Gmail for the proof month. Pro: $0. Con: lower deliverability, no custom domain, and you cannot set SPF or DKIM, so replies from bigger brands drop.

## 2. Anthropic API key now or after proof (blocks `qualify --ai` and `draft --ai`)
**Recommendation:** now, with a $20 monthly cap. At this volume it is cents per lead.
- Pro: sharper openers on the top 25, where reply rate matters most; a call brief in seconds.
- Con: breaks the strict zero-dollar rule by a few dollars.
- Alternative: paste the prompts into claude.ai by hand. Pro: free. Con: slower, and you will skip it on busy days.

## 3. Name the facility in outreach or stay anonymous (blocks the day-0 email wording)
**Recommendation:** name it, once the partner approves the name and the claims.
- Pro: named manufacturers get materially more replies; anonymity reads like a broker blast.
- Con: needs the partner's sign-off and their agreement to field inbound you did not originate.
- Alternative: "a US manufacturer" until the first handoff. Pro: no approval needed. Con: lower reply rate during the proof month, when you need replies most.

## 4. Where the first spear hours go (blocks the top of the send list)
**Recommendation:** the ten Tier 1 accounts in `leads/spear_list.md` (Legally Addictive, Farm to Pet, Nowhere Bakery, Spoiled Pets, Brune Kitchen, Dog Treat Naturals, Roaring Fork Mill, Fat & Weird, Dupe Loops, Fields Good) plus one Tier 2 question to Mightylicious: are you building or buying capacity?
- Pro: every Tier 1 account has a documented change and no incumbent contract in the way; small accounts grow inside the two-year referral window.
- Con: smaller first orders; the proof memo will show more replies and smaller dollar figures than a big-brand list would.

## 5. Referral share for partners who introduce brands (blocks partner outreach)
**Recommendation:** 25 percent of what you receive, flat, for as long as you receive it.
- Pro: simple, generous enough to motivate a broker, still leaves three quarters to you.
- Con: reduces margin on those accounts; requires the facility agreement to allow sub-referral (pin 13).
- Alternative: 20 percent with a bonus after the second account. Pro: cheaper. Con: harder to explain, weaker first-intro motivation.

## 6. Credit for the facility's own dormant leads that you re-engage (blocks pin 11)
**Recommendation:** full rate for leads dormant more than 12 months, half rate for open quotes under 6 months old, written into the agreement.
- Pro: fair to both sides; makes the partner comfortable handing over the list.
- Con: half-rate accounts are the fastest closes, so early income is lower than it looks.

## 7. PLMA on November 15 to 17 (blocks the retail private-label list)
**Recommendation:** attend as a visitor only if the facility data sheet is complete by November 1; otherwise skip and target the ECRM private-label session in April 2027.
- Pro: the only room where store-brand buyers at Target, Kroger, Petco and the rest actually meet suppliers; a badge is cheap.
- Con: travel cost and two days; useless without certifications and a rate card in hand.

## 8. Marketplace listing ownership (blocks pin 10)
**Recommendation:** the facility's own Keychain and PartnerSlate profiles, with you named as the inbound contact.
- Pro: buyers trust a manufacturer profile; you still touch every lead.
- Con: depends on the partner setting them up and routing inbound to you; the agreement must count marketplace inbound as referred.
- Alternative: your own "representative" profile. Pro: no dependency. Con: some platforms disallow it, and buyers discount it.

## 9. Moderate-fit leads (bars, no-bake bites, dry mixes, soft chews, kibble) in the send list (blocks about 15 leads)
**Recommendation:** hold them until the data sheet confirms which formats run.
- Pro: no promises the plant cannot keep.
- Con: a few of them, MOSH and Day Out Snacks among them, are large and would otherwise be week-2 sends.

## 10. CRM now or later (blocks nothing yet)
**Recommendation:** stay on the built-in SQLite pipeline until about 300 contacts, then `leadgen export` into HubSpot free.
- Pro: zero setup now; the export is one command.
- Con: no email integration or reminders beyond `leadgen due`; you log sends by hand.

## 11. LinkedIn voice (blocks the content plan)
**Recommendation:** post from your personal profile, not a new brand page.
- Pro: personal profiles reach far more people; founders reply to people.
- Con: your name is attached to the facility's promises, so the claims discipline matters.

## 12. Website brand and domain (blocks the site launch)
**Recommendation:** your own brand, not the facility's, under the working name **Open Line Co-Packing** (`brand_short: Open Line`), on a .com you register once the checks below come back clean. **Changed from the earlier "Cookie Plug" recommendation:** Cookie Plug is the partner's own brand, with its own footprint. You need a footprint that is yours: rankings, listings, and inbound that stay with you and document your referrals. The partner has declined to add a page or link pointing to you (September 2026), so every channel is built under your own name; whether you may name the partner publicly is still open (pin 5).
- Pro: "open line" says the one thing that matters (a production line with room) and doubles as "an open line to call"; it reads as a B2B service to a retail buyer, not a bakery; searches in September 2026 found no food company using it. The site renders it from the brand fields in each `site/sites/<id>/site.yaml`, so changing it later costs minutes.
- Con: it is not yet cleared. Before you buy the domain, run a free trademark search at tmsearch.uspto.gov (classes 35 and 40) and check the .com; if either is taken, fall back to a plain descriptive name such as "Open Capacity Partners" and change the two brand fields.
- Alternative: the facility's own site. Pro: buyers trust a named plant. Con: needs the data sheet, the partner's approval on every claim, and you do not own it.

## 13. Paid search at day 60 (blocks nothing yet)
**Recommendation:** decide with Search Console data. If organic impressions for "cookie co-packer" and "dog treat co-packer" are growing and the form converts, spend $10 to $20 a day on exact-match terms only.
- Pro: the searches are pure intent; a click that converts is worth hundreds of dollars in referral income.
- Con: clicks in this niche cost several dollars; without conversion data it is guessing.

## 14. Four sites for four audiences (decided September 30, 2026)
**Decision (yours):** four sites on four separate domains, named as one family: **Open Line Co-Packing** (cookies and baked goods, plus makers of other foods who want to ask), **Open Line Pet Co-Packing** (pet treats and pet food), **Open Line Formulation** (recipe development for human food), and **Open Line Pet Formulation**. One engine builds all four (`docs/17` section 11), each with its own wording, line pages, guides, ad landing pages, and questionnaire.
- Pro: each audience lands on a site that speaks only to it (a dog-treat founder never reads about cookies, and a founder with only a kitchen recipe sees formulation first), and each site can rank and run ads for its own searches.
- Con: four domains to register, clear, and maintain, and each starts with no authority. The shared guides would compete with themselves, so each has one canonical home (the first site in family order that carries it), and the others point to it.
- **Watch: formulation leads and your commission.** Your share is paid on production purchases. A formulation-only project may earn you nothing, and whether the facility takes formulation-only work at all is not confirmed (pin 27). So the formulation sites present formulation as the road to production on the facility's open lines, and their questionnaire asks what should happen after formulation: a lead that answers "formulation only" is tagged `formulation-only`, so you can decide case by case.
