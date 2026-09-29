# Spear Playbook: Account-Based Selling for the Top Twelve

The wide net (`04_outreach_playbook.md`) gets you to the proof numbers. The spear list gets you the accounts that pay for two years. Twelve accounts, worked like a key-account rep would: research first, several people at once, a specific give, and a cadence measured in weeks rather than days. The ranked list with custom emails is `leads/spear_list.md`; full dossiers are in `leads/dossiers/`.

## Why twelve, and which twelve

Twelve is what one person can hold in their head alongside the daily sends. Selection rule: right category, live trigger, national retail or funded, and a product the facility can plausibly make. The list is refreshed monthly; an account leaves when it closes, dies, or gets replaced by a stronger trigger.

## The five differences from the wide net

| Wide net | Spear |
|---|---|
| One contact per company | Two or three people at once: the founder, the operator, and whoever sells to retail |
| Signal-based first line | A dossier: their SKUs, retailers, who makes it today, what they said last month |
| Offer a call | Offer a give: a benchmark sample of their hero SKU, a line-extension concept, or a capacity plan for a named launch |
| 5 touches in 18 days | 8 to 10 touches over 6 weeks across email, LinkedIn, and one physical touch |
| Stop after touch 5 | Never stop; drop to a quarterly check-in with something new each time |

## The cadence (per account, six weeks)

| Week | Touch | Who |
|---|---|---|
| 1 | Engage on LinkedIn: a considered comment on the founder's or company's latest post. No pitch. | Founder |
| 1 | Day-0 email built from the dossier: the trigger, one insight about their category, the give. | Founder or CEO |
| 1 | Connection request with a note referencing the same trigger. | Operator (ops, supply chain, production) |
| 2 | Email to the operator: capacity and second-source angle, short, references the founder email. | Operator |
| 2 | Follow-up to founder: the give again, phrased as "I can have a benchmark to you by [date]". | Founder |
| 3 | The physical touch, once the facility data sheet exists: a benchmark sample or the facility's own product with a handwritten note. Cheapest credible proof there is. | Founder |
| 3 | Email to the retail or wholesale lead: "your next reorder from [retailer]" angle. | Sales lead |
| 4 | LinkedIn message to whoever accepted. One question about their supply setup. | Whoever accepted |
| 5 | Founder email with something new: a relevant article, a retailer program, a tariff note. | Founder |
| 6 | Close-the-loop email; move to quarterly with a new give each quarter. | Founder |

Mark each account with `leadgen tag <lead> spear` (and the bench with `bench`); `leadgen list --tag spear` shows them. The cadence above is `config/templates/spear_sequence.yaml`, with each touch assigned to a thread; render one thread with `leadgen draft <lead> --template config/templates/spear_sequence.yaml --thread operator`. Store the operator and sales contacts in `leads/overrides.csv` (they map to the lead's operator and sales fields). Log every touch with `leadgen touch <lead> <day> --channel <email|linkedin|mail>`.

## Multi-threading rules

- Never send the same email to two people. Each gets the angle their job cares about: founder (growth and risk), operator (lead time, MOQ, quality systems, second source), sales lead (never missing a reorder).
- Reference the other thread lightly: "I sent Carolyn a note about this last week" tells the operator it is real and gives them cover to reply.
- When one replies, tell the others you are in conversation with their colleague and stop pitching them.

## The give: what to actually offer

In order of strength:
1. **Benchmark sample of their hero SKU.** Buy the product, send it to the facility, have R&D match it, ship both back with a spec sheet. Costs the facility a day; converts better than anything else. Needs pin 1 (data sheet) and the partner's sampling commitment.
2. **Line-extension concept.** A dog version of a human cookie (or the reverse), a mini format, a Costco pack. Shows you understand their brand; opens a project that does not compete with their current co-man.
3. **Capacity plan for a named launch.** "Your 2,000-door Target launch needs roughly X units a month; here is how a second line covers reorders without touching your primary."
4. **Reshoring math.** For imported products: landed cost with the tariff versus US production. Numbers from their own public pricing.

Never lead with the facility's certifications until confirmed. Lead with what you know about them.

## Metrics for the spear list

Per account, not per email: threads opened (people who replied), give accepted, sample shipped, discovery call, handoff. Target after six weeks: 6 of 12 accounts with at least one thread open, 3 samples in motion, 1 handoff. If fewer than 4 reply by week 4, the dossiers are not specific enough; rewrite the openers before adding accounts.

## Where the AI helps

- `leadgen brief <lead>` for the one-page prep before any call.
- Paste the dossier into `prompts/qualify.md` in claude.ai (or `leadgen qualify --ai`) for a sharper best-angle and personal line.
- Ask Claude to draft the operator and sales-lead variants from the founder email so the three threads stay consistent without being copies.
