# Profile SOUL.md Structure — Kanban Workers

## When to Use

When creating or restructuring a specialist profile's SOUL.md — especially for kanban worker profiles that process dispatched tasks (not user-facing gateways).

## The Pattern

A kanban worker profile's SOUL.md follows a linear read: Identity → Domain → Principles → Facts → Memory → Processing Protocol. Each section serves exactly one purpose. No overlap, no fluff.

```
# Profile Name (one-line identity)
Domain → Principles → Facts → Memory → Processing Protocol
```

### Identity (line 1–3)

One-line statement of who the profile is and how it's dispatched. No "organised, meticulous, proactive" aspirational adjectives — state the role and the source of work.

**Good:** `You are the inventory and purchase coordinator. Dispatched by the heartbeat-watchdog cron to process purchase emails.`

**Bad:** `You are Pallav's inventory and purchase coordinator. Organised, meticulous, proactive.`

### Domain (bullet list)

What the profile owns. Concrete categories of work. No fluff, no example queries, no triggers (the worker never sees user messages). Each bullet is one thing it tracks.

**Good:**
```
- Purchase receipts and order confirmations
- Warranties, return windows, expiry dates
- Consumables and restock thresholds
```

**Bad:** `Inventory — purchases, warranties, consumables, clothing sizes, return windows, baby products, and 15+ tracked categories.`

### Principles (numbered or bullet, 3–5 rules)

Actionable rules that govern HOW the profile does its job. Not aspirational goals. Each rule must guide a decision the profile will face. Only include rules that are non-obvious or easy to get wrong.

**Good:**
```
- Log first — every purchase gets a record immediately. When uncertain, use safe defaults (category=home, price=0) and note it.
- Prefer add-order — it inserts items AND marks the source email processed in one atomic command. Use add-item only for manual one-offs.
- Records are truth — item data lives in the DB. Memory holds patterns, not records.
```

**Bad (aspirational, not actionable):** `Watch windows — return deadlines, warranty expirations, consumable reorder points. Flag before they lapse.` (A kanban worker can't proactively monitor — it processes what's dispatched.)

### Facts (bullet list)

Operational facts the profile needs to do its job. Paths, account names, task source, CLI path. Fixed truths that don't change between tasks.

```
- DB: `/opt/data/inventory/inventory.db`
- CLI: `python3 /opt/data/scripts/inventory.py`
- Gmail accounts for email re-fetch: `pallav`, `priyanka`
- Task source: heartbeat-watchdog cron creates kanban tasks with `assignee: inventory-manager`
```

### Memory (2–3 lines)

Where the profile stores cross-session learnings. What goes there vs what stays in the DB. QMD collection name.

### Processing Protocol (decision tree + numbered flows + fallback)

The core operational procedure. Start with a decision tree that maps task types to flows. Each flow is a numbered sequence of commands. End with a fallback that tells the profile to use the CLI's built-in help.

**Decision tree:**
```
  New purchase from email (kanban task with gmail_message_id)
    → Flow A — add-order (preferred, marks source processed)
  Manual one-off (cash, gift, found, no email)
    → Flow B — add-item
  Change item details (warranty, room, size, colour, price, brand, notes)
    → Flow C — update
  Remove item (returned, cancelled, sold, wrong item, duplicate)
    → Flow D — delete
  Check / flag (view, search, mark email processed)
    → Flow E — query
```

**Each flow** gives the exact command with placeholders. Don't describe — show the command that runs.

**Flow A example:**
```
1. Fetch email — try pallav then priyanka:
   python3 .../google_api.py --account <name> gmail get <gmail_message_id>

2. Log items — inventory.py add-order --email-id <id> --items '[...]' --retailer <R> --order <ORD>
   Default category: home. Missing price → 0. Email unavailable → note it.

3. Complete — kanban_complete(summary="Logged N items from <retailer>")
```

**Fallback:**
```
For anything not covered: <CLI> --help shows every command and flag. Run it before guessing.
```

## What NOT to include

- **Triggers section** — a kanban worker never sees a user message. Triggers are routing instructions for the dispatching system, not for the profile. Delete them.
- **Aspirational principles** — "proactive", "watch windows", "stay ahead". A kanban worker can't be proactive; it responds to dispatched tasks. Principles must be actionable.
- **Hardcoded lists of discoverable things** — "15+ categories: electronics, furniture, kitchen..." → replace with "categories are discoverable via `inventory.py categories`"
- **Memory Scope + Memory Tree as separate sections** — they're the same concept. Merge into one `## Memory` section.
- **Postmortems or bug histories** — "This bug was found and fixed on YYYY-MM-DD" belongs in a changelog or commit message, not in a profile's identity document. The code works now.
- **"Ask later" or "check with the user"** — a kanban worker can't ask questions. It blocks. Rules should say "use safe defaults and note it" not "ask the user."

## Design Properties

| Property | How |
|----------|-----|
| **Each section has exactly one purpose** | No overlap between Domain/Principles/Facts |
| **Every line is actionable** | No aspirational content |
| **Procedures are show-not-tell** | Exact commands, not descriptions |
| **CLI is self-documenting fallback** | --help for anything not covered |
| **Only owned scope is listed** | No routing table, no triggers |
