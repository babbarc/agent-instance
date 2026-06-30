# Intent-Based Email Classification

> A pattern for email triage that classifies by what the email IS (purchase, bill, security, newsletter) rather than who sent it. Developed for the heartbeat-watchdog cron (v27-v28).

## The Problem

Sender-based scoring ("spouse +4 | friend +2 | bulk/newsletter → 0") has a blind spot: automated transactional emails from retailers (purchase confirmations, receipts, shipping notifications) look like bulk mail to a sender heuristic. `auto-confirm@amazon.co.uk` with subject "Ordered: Core Balance Anti Burst Gym..." gets classified as "bulk/newsletter → 0 — skip" and never reaches the routing table that says "Purchase confirmation → inventory-manager."

## The Pattern

Replace flat sender scoring with intent-based classification. Each intent has:
1. A **base score** (urgency/relevance)
2. A **routing gate** (does this intent reach the routing table?)
3. **Concrete matching patterns** (subject prefixes, domain patterns, keywords)

### Intent Categories

| Intent | Base Score | Reaches Routing? | Matching Patterns |
|--------|-----------|-----------------|-------------------|
| Personal message from known person | +1 to +4 | Yes | Person-to-person, conversational subject, no order/billing keywords |
| Purchase / order / shipping / receipt | +1 | Yes | "Ordered:", "Dispatched:", "Shipped:", "Delivered:", "Receipt:", "Your order", "Thank you for purchasing" |
| Bill / statement / invoice / financial | +2 | Yes | "statement", "invoice", "bill", "renewal", "your policy", "your account" |
| Security / account alert | +4 | Yes | "security", "password reset", "login", "new device", "unusual sign-in", "verify your account" |
| Calendar / appointment / booking | +1 | Yes | "reminder", "appointment", "booking confirmed", "your reservation" |
| Newsletter / content subscription | 0 — skip | No | substack.com, medium.com, punchbowl.news, editorial/analysis subjects, "Readback", market commentary |
| Promotional / marketing / deal alert | 0 — skip | No | "50% off", "deal", "offer", "earn", "sale", "limited time", "you might like" |

### Key Design Decisions

1. **Purchase intents get +1 (low urgency) but still route.** The output is silent at score 1-3, but the LLM checks routing — "Purchase confirmation → inventory-manager" fires. Without this, purchase emails are correctly classified but never create inventory tasks.

   **Caveat — routing step 1 must not re-classify.** In v27, step 1 asked "Does this need tracking across cycles?" — a one-off purchase failed all criteria (no deadline, no multi-day, no external response) and was killed as D (output only). The fix (v28+): step 1 now asks "Is the item's type in the routing table?" The routing table IS the authority. If the Intent section classified it as a purchase and the routing table maps purchases to inventory-manager, the item proceeds. No per-intent bypass needed — the routing table covers both process items (bills, contracts) and log items (purchase confirmations). See `references/routing-table-authority.md`.

2. **Routing gate stops newsletter/promotional intents entirely.** These two intents never reach the routing table. All others do, regardless of score. This separates "this email needs logging" from "this email is urgent."

3. **Concrete patterns prevent LLM ambiguity.** Giving the LLM specific subject prefixes ("Ordered:", "Dispatched:") and domain patterns ("substack.com", "medium.com") removes the guesswork. The LLM doesn't need to decide whether Amazon is a newsletter sender — the subject starts with "Ordered:", so it's a purchase.

4. **Subject patterns over sender patterns.** Purchase confirmations vary by sender domain but share subject line patterns. "Ordered:" appears at the start of Amazon, Apple, and countless other retailer subjects. Matching on subject works across all retailers without maintaining an allowlist.

### Implementation in Heartbeat Cron

The full implementation is in the heartbeat-watchdog cron prompt (v28+, file: `memory/reference/heartbeat-prompt-snapshot.md`). The email triage section starts with:

```
**Intent (pick one):**

  Personal message from known person:
    ...
  Purchase / order / shipping / receipt confirmation:
    +1 (low urgency, but purchase must reach routing for logging)
    Pattern: subject starts with "Ordered:", "Dispatched:", ...
  ...
**Routing gate:** newsletter and promotional intents stop here.
All other intents proceed to content scoring + relevance + routing.
```

## Relationship to Previous Design

The old approach (sender-based, v1-v26) used:

```
Sender (pick one):
  spouse/family +4 | ... | bulk/newsletter → 0 (stop — skip)
```

This was a single-dimension check that killed purchase emails before they reached routing. The intent-based approach separates classification from urgency scoring and ensures purchase confirmations always reach the routing table.

The old "bulk/newsletter" category was splitting two very different things — automated order confirmations (need routing) and marketing blasts (should skip). The intent-based approach puts them in different buckets with different routing gates.
