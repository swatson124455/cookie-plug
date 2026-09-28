# Lead Sources That Cost Nothing

Each source below is public, legal to read, and produces companies you can load with `leadgen import`. Expected yield is companies per hour of work after you get the hang of it. Automated scraping of LinkedIn, Amazon, and Faire violates their terms, so those are manual exports; the engine gives you the search strings and does the enrichment and scoring instead.

## 1. Trade show exhibitor lists (best Tier A source; 40 to 60 companies per hour)

Exhibitors pay thousands to be there, which means they are investing in growth. Lists are public on each show's site.

| Show | Categories | Where |
|---|---|---|
| Natural Products Expo West | cookies, bakery, snacks, natural pet | expowest.com exhibitor directory |
| Sweets & Snacks Expo | cookies, bakery, confection | sweetsandsnacks.com |
| Summer / Winter Fancy Food Show | premium bakery, cookies | specialtyfood.com |
| SuperZoo | pet treats, pet food | superzoo.org |
| Global Pet Expo | pet treats, pet food | globalpetexpo.org |
| Private Label Manufacturers Association (PLMA) show | private label buyers | plma.com |

How: open the directory, filter by category, copy company name and website into the CSV. Note the show name in `source`. Prioritize exhibitors with a small booth (growing, not enterprise).

## 2. Retailer "new brand" and local programs (Tier A trigger baked in; 20 to 30 per hour)

- Whole Foods local supplier pages and "Local and Emerging Accelerator Program" alumni.
- Target Forward Founders and Target Accelerators alumni lists.
- Sprouts Innovation Center and "new brands" pages.
- Petco and PetSmart "new arrivals" in treats; Chewy "new brands".
- Kroger and H-E-B local supplier programs.

Every brand on these lists just got a retail listing and now needs volume.

## 3. Shopify store discovery (Tier B; 15 to 25 per hour)

- Google: `"cookies" "powered by shopify"`, `"dog treats" "sold out" site:myshopify.com`.
- Instagram hashtags: #smallbatchcookies, #dogtreats, #homemadedogtreats, #cookiebusiness, then click through to the site.
- The engine's `enrich` step reads `/products.json` on any Shopify site to count products and detect sold-out items.

## 4. Amazon best sellers (Tier A and B; 20 per hour)

Amazon > Best Sellers > Grocery > Cookies; > Pet Supplies > Dogs > Treats; > Cats > Treats. Skip national brands. Look for 4+ star products with 500 to 5,000 reviews from brands you have not heard of. Search the brand name to find their site.

## 5. Funding and news (Tier A trigger; 10 per hour, high value)

- Google Alerts (free) on: `"cookie brand" raises`, `"dog treat" funding`, `"pet food" "series A"`, `co-packer closing`, `bakery recall`, `co-manufacturer bankruptcy`.
- Crunchbase free search: food and beverage, pet, seed and Series A, last 12 months.
- Food industry press: Food Dive, Snack Food & Wholesale Bakery, Pet Food Processing, Pet Product News, NOSH, BevNET's sister site for snacks.

## 6. Job postings (Tier A trigger; 10 per hour)

LinkedIn Jobs, Indeed, and company careers pages for: production manager, plant manager, co-packer manager, co-manufacturing manager, supply chain manager, QA manager, at companies in cookies, bakery, pet treats, pet food. A brand hiring a co-packer manager is literally telling you they are outsourcing.

## 7. Wholesale marketplaces (Tier B; 30 per hour)

Faire, Abound, and RangeMe list thousands of small food and pet brands with their categories and often their location. Search the category, open the brand page, copy the site. Brands on Faire have proven wholesale demand.

## 8. Kickstarter and Indiegogo (Tier B and C; 10 per hour)

Funded food and pet treat projects have demand and no factory. Search "cookie", "dog treats", "biscuit" under Food and Crafts.

## 9. Brand extensions (Tier C; 10 per hour)

- Coffee roasters with a retail line (their customers buy cookies).
- Breweries and distilleries selling snacks.
- Pet influencers, dog-training brands, groomers and daycare chains with an audience.
- Veterinary groups and pet insurance brands exploring private label.
- Corporate gifting companies, fundraising companies (cookie dough programs), hospitality groups, sports teams' merchandise arms.

## 10. Warm-intro network (highest close rate)

People who already talk to your buyers every week: packaging suppliers, ingredient distributors, flavor houses, food-safety consultants, label printers, freight brokers, commissary kitchens, food business accelerators, SBDC and SCORE mentors, food law attorneys. Offer them a share of your referral for introductions. Ten of these contacts can outproduce a hundred cold emails.

## Working the list

1. Put every company in one CSV with the columns from `tests/fixtures/sample_leads.csv`. Company and website are the only required fields; the engine fills the rest. When you saw a trigger while researching (a retail listing, a funding round, a job post), mark it `true` in the matching column (`in_national_retail`, `recent_funding`, `recent_retail_launch`, `hiring_ops_or_production`, `sells_wholesale`, `mentions_copacker`) so it counts immediately.
2. `leadgen import path.csv --source expo_west_2026`.
3. `leadgen enrich` then `leadgen score`. Anything over 55 gets a contact search; 40 to 55 goes in a nurture list; under 40 is archived.
4. Find the person: LinkedIn search "founder" or "operations" plus the company; verify the email pattern with a free lookup or the company's contact page.
5. `leadgen draft <domain>` and send.
