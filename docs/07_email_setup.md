# Email Setup for Cold Outreach (Free)

Do this in week 1. Cold email from a domain without authentication lands in spam, and a burned domain takes months to recover. Total cost: the domain you already own, or about $12 a year for a new one.

## 1. Use a separate sending domain

Do not send cold email from your main domain. Register a close variant (for example `getbrandname.com` or `brandname.co`) and set it to redirect to your main site. If the new domain gets flagged, your main domain is untouched.

## 2. Create the mailbox

Google Workspace Business Starter is the reliable choice (about $7 a month per user; if the budget is truly zero this month, use a free Gmail for the warm-up period and move to the domain mailbox when the proof gate is met, accepting lower deliverability until then). One mailbox, one sender name, a real photo in the profile.

## 3. Authenticate the domain (DNS records)

In your domain registrar's DNS panel add:

| Record | Type | Value |
|---|---|---|
| SPF | TXT on `@` | `v=spf1 include:_spf.google.com ~all` |
| DKIM | TXT on `google._domainkey` | the key Google Workspace generates under Apps > Google Workspace > Gmail > Authenticate email |
| DMARC | TXT on `_dmarc` | `v=DMARC1; p=none; rua=mailto:dmarc@yourdomain.com` |

Verify with a free checker (MXToolbox or Google Admin's toolbox). All three must pass before sending.

## 4. Warm up for 14 days

- Days 1 to 7: 10 emails a day to people you know. Ask them to reply. Reply to their replies.
- Days 8 to 14: 20 a day, mix of known contacts and the first real leads.
- Day 15 onward: up to 30 cold emails a day per mailbox. Never more than that from one mailbox.

Free warm-up networks exist but change often; manual warm-up works and costs nothing.

## 5. Sending hygiene

- Plain text. No images, no HTML templates, no tracking pixels, no links in the first email.
- One email at a time from Gmail, or Gmail's scheduled send. No bulk BCC.
- Signature: name, title, phone, physical mailing address (CAN-SPAM), one line "Reply 'no' and I will stop."
- Bounce rate over 3% means the list is bad. Stop and verify emails before continuing.
- Check spam placement weekly by sending to a personal Gmail, Outlook, and Yahoo address.

## 6. Finding email addresses without paid tools

1. Company contact page or press page.
2. LinkedIn: the person's name and title; then the company's email pattern.
3. Pattern: most small brands use `first@brand.com` or `first.last@brand.com`. Verify with a free lookup (Hunter's free tier gives a handful per month) or by sending the day-0 email and watching for a bounce.
4. Founder emails for Shopify brands are often in the site's "Contact" or "Wholesale" page.

Log the source of every address in the lead's notes so you can prove it was found publicly.
