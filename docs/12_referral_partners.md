# Referral Partner Network

Vendors and advisors who talk to growing brands every week are the highest-close-rate channel in this plan: a warm introduction converts to a meeting three to five times more often than a cold email. The researched list is in `leads/referral_partners.csv` (packaging suppliers, label printers, food-safety consultants, brokers, ingredient distributors, accelerators, consultants, pet-industry groups). This is how to work it.

## The offer

You pay a share of your referral commission on any account they introduce that closes. Keep it simple and in writing:

- **Share:** 20 to 30 percent of what you receive from that account, for as long as you receive it. A vendor who sends one $400k account earns thousands a year for one email.
- **Definition:** an introduction is a named email intro or a forwarded request from the brand. A name on a list is not an introduction.
- **No exclusivity, no obligation.** They introduce when it helps their client; you report back on every intro within a week so they look good.
- **Paperwork:** a one-paragraph email agreement is enough at the start; move to a signed one-page agreement after the first payout.

Confirm on the kickoff call that sub-referrals are allowed under the facility agreement (they are your commission to share, but say so).

## Who to contact first

1. **SQF and food-safety consultants.** Brands hire them precisely when a retailer demands a certified facility. They are talking to your Tier B leads at the exact moment the problem appears.
2. **Natural and pet specialty brokers.** They place brands at Sprouts, Whole Foods, Petco. When a brand wins a listing, the broker knows before anyone whether the brand can supply it.
3. **Short-run packaging printers.** Every emerging brand orders pouches. A jump in order size means production is scaling.
4. **Accelerators and community managers.** Startup CPG, Naturally Network chapters, shared kitchens. One post in their channel reaches hundreds of founders.
5. **Fractional COOs and CPG operations consultants.** They are paid to find co-packers for their clients and will take a fee for a good one.

## The outreach (email, under 120 words)

> Subject: a co-packer with open capacity, for your clients
>
> Hi [first name],
>
> You work with [cookie / pet treat] brands at the stage where production becomes the problem. I represent a US manufacturer with open capacity right now for cookies, baked goods, and pet treats, turnkey from formulation to shelf-ready, sampling in weeks rather than the usual 6 to 12 month wait.
>
> When a client of yours needs a second source or has outgrown their kitchen, I would like to be the introduction you make. I pay [25] percent of my referral fee on any account that closes, for as long as it pays, and I report back on every intro.
>
> Worth a 15-minute call to see if it fits how you work?
>
> [Your name], [phone]

Follow up once after five days. Then quarterly with a one-line "still have capacity, here's what we placed this quarter" note.

## Tracking

Import partners with `leadgen import leads/referral_partners.csv --source referral_partner` after adding a `company` column (rename `organization`), or keep them in the CSV and log intros as leads with `source=intro_<partner>`. Every introduced lead's notes must name the introducer, because that is what triggers the share.
