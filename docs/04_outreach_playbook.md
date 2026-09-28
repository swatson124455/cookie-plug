# Outreach Playbook

Everything you send, say, or answer, in one place. The engine renders the sequence in section 2 from `config/templates/sequence.yaml`; edit the YAML, not the code, when you learn what works.

## 1. Rules that decide whether cold email works at all

1. **Deliverability before volume.** Own domain, SPF, DKIM, DMARC set. Warm up for two weeks. Plain text. No links, images, or tracking in the day-0 email. Under 30 sends per inbox per day.
2. **The first sentence is about them.** A fact you found: a retailer, a sold-out product, a job post, a launch. The engine writes this from enrichment; Claude writes it better. Never "I hope this finds you well."
3. **One pain, one claim, one ask.** Under 110 words.
4. **Send Tuesday to Thursday, 7 to 9 am their time.** Founders read email early.
5. **Follow up four times.** Most replies come on touches 2 to 4. Stop after five; say you are stopping.
6. **Reply within two hours** during business hours. Speed is the cheapest differentiator you have.
7. **Log everything.** `leadgen touch <lead> 0` when the first email goes out, `leadgen due` every morning for the follow-ups owed, `leadgen touch <lead> <day>` as each one is sent, `leadgen advance <lead> replied` the moment someone answers (which stops the sequence). The activity table is your commission record.

## 2. The five-touch sequence (rendered by `leadgen draft`)

| Day | Channel | Purpose |
|---|---|---|
| 0 | Email | Trigger-based opener, pain, facility, low-friction ask |
| 3 | LinkedIn connect | Face and credibility, no pitch |
| 5 | Email | Two concrete reasons: lead time and one roof |
| 10 | Email | Offer a benchmark sample instead of a call |
| 18 | Email | Polite close, leaves the door open |

Example day-0 output for a lead that the enricher found on Whole Foods shelves:

> **Subject:** Crumb Co x spare cookie capacity
>
> Hi Jordan,
>
> Congrats on getting Crumb Co onto Whole Foods shelves. That kind of retail pull usually turns production into the bottleneck fast.
>
> Most cookie brands at your stage hit the same wall: the next retail order or launch needs more volume than the current setup can produce, and every co-packer they call is booked out or wants a huge minimum.
>
> I work with a US manufacturer that runs cookie, bakery, pet treat, pet food lines under one roof and is a strong fit for cookie production. They have open capacity right now, so we can sample in weeks, not quarters, and we handle formulation, packaging, labeling, and nutrition panels so the product lands shelf-ready.
>
> Worth a 15-minute call to see if the capacity and the specs line up?
>
> Sam Watson
> Partnerships

## 3. Segment-specific openers (swap into the first line)

- **Sold out:** "Noticed three of your treats showing sold out this week. Good problem, usually a capacity one."
- **Hiring ops:** "Saw the production manager role you posted. Brands usually post that right before they hit a capacity wall."
- **New retail listing:** "Congrats on the Sprouts launch. The first reorder is where most brands find out their kitchen can't keep up."
- **Funding:** "Congrats on the round. Most of that usually goes to inventory, and inventory needs a plant that can run it."
- **Pet brand, human-grade angle:** "You already sell human-grade for dogs. The same plant that makes your treats can make the cookie your customers keep asking for."
- **Cookie brand, pet angle:** "Half your Instagram comments are people asking if their dog can have one. There is a version that can."
- **Co-packer trouble in the news:** "If the news about [plant] affects your supply, we have open lines this quarter."

## 4. LinkedIn

Connection note (under 300 characters, no pitch):
> Hi {first_name}, I work with a US {category} manufacturer that has open capacity and does full turnkey. Saw what {company} is doing and thought it was worth a quick hello.

After they accept, wait two days, then one message referencing your day-0 email. Never send the pitch in the connection note.

Two posts a week, from your own account, on: what retail buyers actually require from a supplier; why co-packer MOQs keep rising; how to dual-source production; a short case of a sample turnaround. Posts build the inbound that makes cold outreach warm.

## 5. Handling replies

| Reply | Response |
|---|---|
| "Send me more info" | Send the capabilities one-pager and propose two call times. Info alone does not close. |
| "What are your MOQs / prices?" | Give the range from the facility's sheet and ask for their volume so you can be specific. Book the call. |
| "We're happy with our current co-packer" | "Glad to hear it. Most brands we work with keep their primary and use us as a second source for 20% so a hiccup never stops shipments. Worth keeping the door open?" |
| "Not right now" | "Understood. When does the next planning cycle or retail reset happen? I will check back then." Log a nurture date. |
| "We make everything in-house" | "Makes sense. If a new SKU or a retail win ever outruns the plant, we can take overflow without you adding a shift." Tag as nurture. |
| "Do you have SQF / organic / GF?" | Answer only from the confirmed facility sheet. If unknown: "Let me confirm exactly which certificate applies and send it to you today." Then get it. |
| Unsubscribe or hostile | Stop immediately, log closed_lost, honor the opt-out. |

## 6. Discovery call script (15 minutes)

Run `leadgen brief <lead>` before the call for the facts, the fit assessment, and the thread history on one page.

**Open (1 min):** "Thanks for the time. I'll ask a few questions about what you make and where you're headed, tell you how the facility works, and we'll decide together if a sample makes sense. Fair?"

**Their world (6 min):**
1. What are you making today and where is it made?
2. What is the monthly volume now, and where does it need to be in 12 months?
3. What is driving the timing: a PO, a launch, a contract ending?
4. What has the current setup gotten wrong: lead time, MOQ, quality, cost, certifications?
5. Which certifications do your retailers require?
6. Who else is involved in choosing a manufacturer?

**Facility (4 min):** open capacity, turnkey scope, one roof, sample process, and the ranges from the pricing sheet. Only confirmed facts.

**Close (4 min):** "Based on what you said, the right next step is [a benchmark sample of X / a call with the plant's ops lead / a pricing sheet for Y volume]. I'll have it to you by [date]. What do you need from your side to move on it?"

Write the answers into the lead's notes (`leadgen advance <lead> discovery_call --note "..."`).

## 7. Objection handling

| Objection | Response |
|---|---|
| "We need SQF and you're not sure you have it" | "You're right to ask. I will send the exact certificate today. If it isn't the level your buyer requires, I'll tell you straight and we stop there." |
| "Your MOQ is too high" | "What run size would make the numbers work for you? The facility has room now, which is exactly when a plant can be flexible on the first run." |
| "We had a bad co-packer experience" | "Most brands we talk to did. Which part went wrong, quality, communication, or timing? That tells me whether this plant is a fit." |
| "Price is higher than our current" | "Compare landed cost including the orders you couldn't fill. What did the last stockout cost you?" |
| "We're too small" | "Maybe for now. What volume would you need before outsourcing makes sense? I'll check back at that milestone." |
| "Why go through you instead of the plant directly?" | "You're welcome to. I stay on the thread because I'm paid to make sure this works for you, not to fill their lines. If they drop the ball, I'm the one who chases them." |

## 8. Handoff checklist

Before introducing the facility:
- [ ] Volume, timing, product, and requirements written in the lead's notes.
- [ ] Buyer has received the capabilities sheet and the pricing range.
- [ ] Sample sent and feedback captured, or the buyer explicitly waived it.
- [ ] Decision maker confirmed and on the intro thread.
- [ ] Referral agreement covers this account; export the pipeline as a timestamped record.

Intro email: three lines. Who the buyer is, what they need, what the next step is, with a date. Stay cc'd. Check in weekly until the first PO ships.

## 9. Compliance

CAN-SPAM for B2B email: real sender name and address, truthful subject, a physical postal address in the signature, and a way to opt out ("reply 'no' and I'll stop"). Honor every opt-out within ten days; the playbook says immediately. Do not buy or scrape lists of personal emails. Keep records of consent for anything beyond cold B2B email.
