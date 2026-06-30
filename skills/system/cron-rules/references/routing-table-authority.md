# Routing Table Authority

> The routing table IS the gate — not a secondary check that duplicates it. Developed for the heartbeat-watchdog cron (v28).

## The Problem

A routing decision tree with a standalone step 1 gate that asks a subjective question (e.g. "Does this need tracking?" or "Does ignoring cause future problems?") creates a parallel classification system that duplicates the routing table. The LLM judges independently of the table, and one-off items (purchase confirmations, single statements) fail the subjective gate — even though the routing table explicitly maps them to a domain.

The result: items with a clear routing destination never reach the routing table because a redundant gate kills them first.

## The Pattern

**Step 1 checks the routing table. The routing table IS the authority.** Three rules:

1. **The routing table decides what gets routed.** If the TRIAGE Intent section classified the item's type and the routing table has a domain for that type, the item proceeds to the decision flow. No additional LLM judgment about "should this be tracked?" — the table already encodes that.

2. **The routing table is a standalone section, not embedded in Option B.** It sits at the top of the ROUTING section, before the decision flow. Every option (B, C) references it. One copy, one source of truth.

3. **Newsletter/promo items are already stopped by the TRIAGE routing gate.** They never reach the routing table. The step 1 gate only sees intents that already passed TRIAGE — personal messages, purchases, bills, security alerts, calendar bookings. All of these have potential routing destinations.

## Routing Table Structure

```
### Routing Table

| Type | Domain | Purpose |
|------|--------|---------|
| Statement / bill / invoice | ca-expert | Process and file |
| Purchase confirmation / receipt | inventory-manager | Log to inventory |
| Contract / legal document / notice | legal-expert | Review and action |
| Home maintenance / repair / tradesman | home-manager | Schedule and manage |
| Family event / guest / gathering | family-manager | Coordinate |
| Other actionable | joy | Self-handle |
```

The Purpose column is critical — it tells the LLM WHY each type is routed. "Log to inventory" makes it clear that a purchase confirmation doesn't need multi-step tracking, it needs durable recording. This prevents the LLM from asking "does this need tracking?" and answering "no" for a one-off purchase.

## Calendar Is a Parallel Side-Effect, Not a Gated Step

The calendar check (Option E) must run for EVERY item, not just items in the routing table. A confirmed dinner reservation, doctor's appointment, or social invitation isn't a routing-table type — but it still needs a calendar event.

**Wrong — calendar gated behind routing table:**
```
Step 1: Is type in routing table? → No → D (stop). Never reaches calendar check.
Step 2: Calendar booking? (only reached if Step 1 passed)
```

**Right — calendar runs first, independent of routing:**
```
Step A — Calendar (run for EVERY item):
  Is this a confirmed booking with clear date/time?
  → YES → run Option E (calendar event). Then proceed to routing.
  → NO → skip to routing.

Step B — Routing:
  1. Is the item's type in the routing table?
     → No → D (output only). No kanban task.
     → Yes → continue.
```

This matches the framing in the ROUTING section header: "Calendar event creation (E) and enrichment run alongside other routing — a single item can create a kanban task AND a calendar event if both are needed."

## WhatsApp Items Need Explicit Routing-Table Classification

The TRIAGE Intent section only classifies EMAIL items by type (purchase, bill, security, etc.). WhatsApp items produce urgency buckets (health concern, needs decision, casual) — not routing-table types. Without an explicit instruction, the LLM has no way to map a WhatsApp message like "boiler's leaking, plumber's coming Tuesday" to the home-manager domain.

**Fix:** After the WhatsApp urgency section, add an explicit routing-table mapping instruction:

> For WhatsApp: infer the closest routing-table type from content (e.g. "boiler leaking" = home maintenance, "invitation" = family event, "purchased" = purchase confirmation). Then proceed through the routing flow as normal.

## The D Escape Hatch — B/C Is a Status Decision, Not a Routing Decision

The most subtle bug in a routing decision tree is the Step 3 NO-match branch that offers D (output only) alongside B (new task) and C (pending). These three options mix two fundamentally different decisions:

- **B vs C** is a *status* decision — both create a task in the routed domain, differing only in `--status ready` vs `--status pending`.
- **D** is a *routing* decision — it creates no task at all.

**The problem:** D directly contradicts the premise that got the item here. Anything reaching Step 3 passed Step 1's "Yes" — its type is in the routing table, which already committed to routing it. Offering "Neither applies → D" re-opens the routing question and hands the LLM a lever to reverse Step 1.

This is what happens with one-off purchase confirmations. The LLM decides "logging a receipt is passive, doesn't need domain action → Neither applies → D." It doesn't realise that "log to inventory" IS the domain action — the Purpose column in the routing table already established that.

**The fix — frame the NO-match branch as a pure status decision:**

> → **NO match → a task gets created. Choose its status: B or C (never D).**
>   The item passed Step 1, so its type IS in the Routing Table and the
>   mapping is mandatory. The routing decision is already made — the only
>   open question is the new task's status:
>
>   - **B** (status ready) — default. The assigned domain can act on its
>     own. Every purchase confirmation, receipt, statement, and bill is B:
>     logging/filing IS the domain action, and Step 1 already committed to it.
>   - **C** (status pending, ⏳ on Pallav) — use only when the first step is
>     a decision only the user can make and the domain cannot start until
>     they choose.
>
>   D does not exist in this branch. D is Step 1's answer for types that
>   aren't in the Routing Table, and the YES-branch's answer for routine
>   back-and-forth. An item that reached here is a tracked type with no
>   existing workstream — that is the definition of a new task.

**Where D still belongs:**
- **Step 1** — for types NOT in the routing table (newsletters, promos, casual chat)
- **Step 3 YES branch** — for routine back-and-forth on existing tasks ("ok thanks", scheduling logistics)

**Removing D from the NO-match branch costs nothing** because every legitimate no-task outcome is still expressible — just not at this branch. You haven't reduced the LLM's judgment; you've relocated it. The system makes each "task or no task?" call exactly once, at the step that owns it.

**The one coupling to watch:** This consolidates the entire task/no-task decision into Step 1's gate — specifically the "Other actionable → joy" catch-all row. The specific rows (receipt, bill, contract, family, home) are unconditional and safe. But "Other actionable" is now the ONLY place a judgment-call item can be filtered out, so if it's worded loosely the LLM could over-match it and spam tasks. Make sure that row reads as "genuinely needs a domain to do something," not "anything not obviously ignorable."

## Decision Flow (integrated)

```
For every item that isn't newsletter/promo (those stop at TRIAGE):

**Step A — Calendar (run for EVERY item, independent of routing table):**
Is this a confirmed booking with clear date/time and the user's agreement?
   → YES → run Option E (calendar event). Then proceed to Step B.
   → NO → skip to Step B.

**Step B — Kanban routing:**
**1. Is the item's type in the routing table?**
   The TRIAGE Intent section classified the type for email.
   For WhatsApp: infer the closest routing-table type from content.
   → No → D (output only). No kanban task.
   → Yes → continue to step 2.

**2. Relates to an existing workstream?**
   Match by topic, contact name, project name, or address against
   task titles and body previews in the injected kanban data.
   Ambiguous match → treat as no match — don't force it.

   → YES, clear match → A (update existing task). Only for state changes.
     Routine back-and-forth → D even if the topic matches.

   → NO match → a task gets created. Choose its status: B or C (never D).
     (B = default ready, C = pending on user decision)
```

## What This Replaces

The old step 1 gate asked a subjective question that forced the LLM to re-derive what the routing table already encoded:

- v27: "Does ignoring this item cause future problems?" — examples included "purchase not logged → lost warranty/return reference", but the LLM still judged a one-off yoga mat as not causing problems → D
- v26 and earlier: "Does this need tracking across cycles?" — same problem, different wording

The fix: ask the routing table, not the LLM's subjective risk assessment. The table is the authority. And once an item passes that authority, the routing decision is final — only the status remains to be determined.

## Guardrails for Trimming

When condensing a routing section during maintenance:

- **"Enrichment still runs independently" in the No path is not noise** — it prevents the LLM from skipping enrichment when an item doesn't need a kanban task.
- **"Do not dump raw email text" in Option B is not noise** — it prevents the LLM from pasting the full email body into the kanban task body.
- **Structural formatting (✅/❌ lists, bullet hierarchies) is not noise** — it guides the LLM's parsing. Inline prose loses the visual separation that helps the LLM distinguish examples from rules.

Before trimming any line from a routing section, verify: does this line constrain or guide the LLM's behavior? If yes, keep it. Decorative prose ("to determine the domain" vs "for domain") is safe to trim — guardrails are not.
