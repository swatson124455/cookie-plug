# Trade Show Capture Playbook

Shows are the densest source of Tier A buyers. Exhibitors are spending to grow, award finalists have a story to reference, and every show has a public exhibitor directory. This is the calendar-driven plan: what to do in the four weeks before, during, and after each show. Dates verified 2026-09-28; confirm on each show's site before booking anything.

## 12-month calendar

| Show | Dates | Where | Why it matters | Access |
|---|---|---|---|---|
| PLMA Private Label Trade Show | Nov 15 to 17, 2026 | Rosemont IL | Retail private-brand buyers in one building; the only show where the buyer, not the brand, walks the floor | Exhibit (facility) or attend as a supplier |
| Winter FancyFaire (Fancy Food) | Jan 17 to 19, 2027 | San Francisco | Premium cookies, shortbread, biscotti, crackers; sofi finalists announced | Attend; directory public |
| Natural Products Expo West | Mar 2 to 5, 2027 | Anaheim | Largest natural CPG show; NEXTY finalists; pet section | Attend; directory public |
| Global Pet Expo | Mar 17 to 19, 2027 | Orlando | Pet treat brands, New Products Showcase | Attend; directory public |
| ECRM Private Label Food & Beverage | Apr 12 to 14, 2027 (2026 was Apr 20 to 22) | Rosemont IL | Scheduled 1:1 meetings between private-label manufacturers and retail buyers | Supplier registration (paid) |
| ECRM Deli, Dairy & Bakery | Spring Apr 2027; Fall Sep 27 to 29, 2026 | Rosemont IL | Buyers reviewing shelf-stable and thaw-and-serve bakery, new brands and private label | Supplier registration (paid) |
| Sweets & Snacks Expo | May 18 to 20, 2027 | Indianapolis | Cookies, bakery, confection; Most Innovative New Product awards | Attend; directory public |
| SuperZoo | Aug 11 to 13, 2027 (2026 was Aug 12 to 14) | Las Vegas | Largest pet show; Emerging Brands Pavilion is a Tier B goldmine | Attend; directory public |
| Newtopia Now (former Expo East) | Aug 18 to 20, 2026 | Denver | Curated natural CPG, smaller and emerging brands | Attend; directory public |

## Four weeks before: build the list (no ticket needed)

1. Open the exhibitor directory the week it publishes (usually 6 to 8 weeks out). Filter by category. Copy company, website, booth, and any product description into the research CSV with `source=<show>_<year>`.
2. Pull the award and showcase lists separately: NEXTY finalists (Expo West), sofi finalists (Fancy Food), Most Innovative New Product (Sweets & Snacks), New Products Showcase and Emerging Brands Pavilion (SuperZoo), Buyer's Choice (ECRM). Mark `recent_retail_launch=true` when the release says so.
3. Import, score, and qualify. Everything over 55 gets a contact search.
4. Send a pre-show email 10 to 14 days out: "Saw you're exhibiting at [show], booth [N]. If a capacity conversation would be useful while you're there, I'll be walking the floor Tuesday." A pre-show email gets replies because founders are planning their show week.

## At the show (if attending, one show per quarter is enough)

- Register as a buyer or "manufacturer / supplier" attendee; attendee badges are cheap or free for trade, and the badge gives you the mobile app with the full exhibitor list and, at some shows, direct messaging.
- Walk the small-booth aisles and the emerging-brand pavilions first. Ten-by-ten booths with the founder standing in them are the targets. Ask one question: "Who makes this for you today?" The answer sorts every lead in fifteen seconds: in-house (capacity pitch), a co-packer (second-source pitch), or "we're looking" (close).
- Take a photo of the booth sign and the founder's card. Log the note into the lead the same evening with `leadgen advance <lead> replied --note "met at booth N, makes in-house, hitting capacity"`.
- Bring nothing to hand out except the one-pager (`docs/09`), once the facility data sheet is complete. A sample of the facility's own product beats any brochure.

## Two weeks after: the follow-up window

- Day 1 to 3 after the show: email everyone you met, referencing the conversation. This is the highest reply rate of the year.
- Day 3 to 10: email everyone on the exhibitor list you did not meet, with the show as the opener ("Congrats on the show. The first reorder after a show is where capacity gets tight").
- Log all of it; run `leadgen due` daily. Show leads that reply move straight to a discovery call.

## Should the facility exhibit?

Not in Phase 0 or 1. A 10x10 at Expo West or SuperZoo runs several thousand dollars plus travel, and the facility can get most of the value from you walking the floor. The exception is **PLMA** and the **ECRM private-label sessions**: those put the facility in front of retail private-brand buyers who will not answer cold email. Revisit after the first signed account, with the facility paying for the booth and you working it. Put it in the referral agreement that show-sourced accounts count as referred when you logged them.

## Buyer-side data (retailers, not brands)

Retail private-label buyers do not appear in exhibitor lists. Ways to reach them:
- PLMA and ECRM, above.
- Retailer supplier-diversity and local-supplier portals (Target, Kroger, Walmart, H-E-B, Whole Foods) where a manufacturer can register.
- Category-manager names surface in trade press (Store Brands, Progressive Grocer, Pet Age); search "[retailer] private brands director pet" and log them as `retailer_private_label` leads.
- Chewy Made, Tractor Supply, and Petco private-label expansions are already in the seed list.
