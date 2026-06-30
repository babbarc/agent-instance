# Routing Flow: Transient Items

## The Anti-Pattern

A triage-routing prompt that combines:
1. A catch-all routing table row (`Other actionable → joy`)
2. An unconditional "Option D FORBIDDEN" on the no-match branch

→ **Result:** Every transient one-shot item (security alert, password reset, one-off
enquiry) permanently becomes a kanban task. The catch-all makes Step B.1 answer
YES for everything, then the universal Option D ban forces task creation.

## Pre-Routing Gate

Insert BEFORE the routing table. This wires the existing scoring disposition into
the flow so "output-only" actually means something:

```
**Step 0 — Output-Only Check:**
Does the item's intent disposition carry "output-only" (security/account alert,
password reset, automated notification)?
  → YES: Use Option D (Output only, no kanban task). Stop.
  → NO: Continue to Routing Table.
```

This handles security alerts, 2FA/OTP emails, and system notifications in one
line without touching the routing table.

## Transient Blocklist

A compact header placed immediately above the routing table. Costs <200 chars
and catches anything the pre-routing gate misses:

```
**Always Option D, regardless of routing:**
OTP/2FA codes, password-reset confirmations, security/device login alerts,
automated system notifications, one-off enquiries with no commitment or
ongoing obligation.
```

## Narrowing the Option D Ban

The original blanket ban ("Option D is FORBIDDEN") was intended to prevent the
LLM from skipping task creation for genuinely tracked workstreams (bills,
contracts, invoices). Change it to a conditional ban:

```
**→ NO (No Match):** You MUST create a new task.
  *Option D is forbidden ONLY if the item implies an ongoing tracked obligation
  (bill, contract, repair quote, legal notice).*
  *One-shot items with no required follow-up → Option D.*
```

## Remove the Catch-All Routing Row (Alternative to Narrowing the Ban)

Instead of narrowing the Option D ban, you can **remove the catch-all row** from
the routing table entirely. This prevents transient items from reaching Step B
in the first place:

```
### Routing Table

| Type | Domain | Purpose |
|------|--------|---------|
| Statement / bill / invoice | ca-expert | Process and file |
| Purchase confirmation / receipt | inventory-manager | Log to inventory |
| Contract / legal document / notice | legal-expert | Review and action |
| Home maintenance / repair / tradesman | home-manager | Schedule and manage |
| Family event / guest / gathering | family-manager | Coordinate |
~~| Other actionable | joy | Self-handle |~~  ← REMOVE THIS
```

**Without the catch-all**, items that don't match a specific domain hit
Step B.1 NO → Option D (output only) automatically. Combined with a
Step 0 transient gate, this eliminates all unexpected task creation.

**Trade-off:** Genuinely new multi-step workstreams that don't fit a routing
domain will also exit via Option D. They appear in the output but require
manual task creation. Acceptable when the priority is preventing unexpected
tasks.

**Confirmed in production (Jun 2026):** Applied to the heartbeat watchdog
prompt. Removed "Other actionable → joy", added Step 0 gate, relaxed
Step B.2 to "task creation only for genuine multi-step obligations."
Next run succeeded with no unwanted tasks created.

## Decision Tree: Transient vs Trackable

```
Is this item a…
├─ Security/device alert (login, 2FA, password reset)?
│  → TRANSIENT. Output only, no task. Done.
├─ Automated notification (receipt, shipping, appointment reminder)?
│  → TRANSIENT. Output only, no task. Done.
├─ One-off enquiry (no commitment, no follow-up needed)?
│  → TRANSIENT. Output only, no task. Done.
├─ Bill / statement / invoice / legal notice?
│  → TRACKABLE. Create or update kanban task.
├─ Purchase confirmation / receipt for a new item?
│  → TRACKABLE. Log to inventory or create task.
├─ Home maintenance / repair / tradesman booking?
│  → TRACKABLE. Create or route to home-manager task.
├─ Family event / guest coordination?
│  → TRACKABLE. Create or route to family-manager task.
└─ Already matches an active workstream?
   → TRACKABLE. Update existing task with new context.
```

## Why Not "Output-Only" Label in Scoring?

The scoring system's "output-only" label is a **dead signal** if routing ignores
it. Three options, pick one:

| Option | What | Cost |
|--------|------|------|
| **Wire it** (recommended) | Add the pre-routing gate (Step 0 above) | ~100 chars |
| **Delete it** | Remove "output-only" from scoring — the +4 weight already conveys urgency | ~15 chars |
| **Ignore it** | Leave it as misleading noise | 0 chars, but causes future confusion |

## Related

- Pitfall #23 — Routing Flow Escape Hatch (Don't Mix B/C With D)
- `references/routing-table-authority.md`
- `references/routing-flow-bc-vs-d.md`
