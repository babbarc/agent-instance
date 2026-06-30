---
name: signal-noise-classifier
category: software
description: |
  A reusable decision framework for assessing importance and routing any incoming item — email, message, document, or notification. The LLM follows a structured process: load context → load criteria → assess → route → output
annotation: "Importance filter: urgency, impact, actionability assessment"
tags: [decision-making, intelligence, routing, triage]
related_skills: [document-ingestion-pipeline, ea-domain-routing]
---

**Routing gate principle:** The routing table IS the gate. The Intent classification already produces the item type — just check the table. Do not add a separate freeform LLM gate before the table; that duplicates authority and causes the LLM to re-derive what the table already encodes. See `references/routing-table-gate.md`.

# Decision Intelligence Framework

A generic, reusable process for assessing any incoming item and deciding what to do with it. Designed to work across domains (email, WhatsApp, local files, future sources) with the same LLM process — only the criteria and routing map change.

## Input Contract

Every item the framework processes must provide at minimum:

| Field | Required | Description |
|-------|----------|-------------|
| `content` | Yes | The text/content of the item (subject line, message body, document snippet) |
| `source` | Yes | Where it came from (`gmail`, `whatsapp`, `local_file`, etc.) |
| `sender` | Yes | Who sent it (email, phone number, JID, or filename) |
| `timestamp` | Yes | When it was created or received |
| `type` | No | Sub-type (`bill`, `statement`, `chat`, `photo`, `contract`, etc.) |
| `id` | No | Unique identifier (gmail_id, message key, file path) |
| `metadata` | No | Extra fields specific to the source (group name, file size, has_attachment) |

## The Decision Loop

For each item in a batch, run this 5-step process:

### Step 1: Load Context

Always load these before making any judgment — they change what "important" means moment-to-moment:

- **Active goals** — what is the user currently prioritising?
- **Active Kanban tasks** — what's in progress, what's due soon? (kanban.db)
- **Time horizon** — current time, upcoming deadlines, birthdays, scheduled events
- **Available specialists** — which specialist profiles exist for routing? (ca-expert, legal-expert, home-manager, etc.)

How this is done depends on the caller (heartbeat, weekly scan, etc.). The framework doesn't prescribe the method — just that context is gathered *before* judgment.

### Step 2: Load Criteria

Load the domain-specific signal rules file for this source type. The criteria file tells the LLM what to look for:

| Source type | Criteria file | How to load |
|-------------|--------------|-------------|
| `gmail` | references/email-signal-rules.md | `skill_view(name='signal-noise-classifier', file_path='references/email-signal-rules.md')` |
| `whatsapp` | references/whatsapp-signal-rules.md | `skill_view(name='signal-noise-classifier', file_path='references/whatsapp-signal-rules.md')` |
| `local_file` | references/document-signal-rules.md | `skill_view(name='signal-noise-classifier', file_path='references/document-signal-rules.md')` |
| `generic` | Fallback below | None needed |

**⚠️ Critical: criteria files are NOT automatically loaded into the agent's context by loading the skill.** The `signal-noise-classifier` skill's framework text (this SKILL.md) is loaded, but the individual reference files are not. The calling prompt MUST include explicit `skill_view` instructions for the agent to access them. Without this, the agent will triage based on general LLM ability rather than the domain-specific rules.

Each criteria file follows a standard format:
- **Signal categories** — conditions that make an item important
- **Noise categories** — conditions that make an item ignorable
- **Always-flag exceptions** — items to never ignore (security alerts, family emergencies)
- **Tiebreaker rule** — what to do when an item is ambiguous

If no criteria file exists for the source, fall back to: *"Flag if it relates to an active goal or a known person. Skip if it looks like advertising, automation, or casual chat."*

### Step 3: Assess

For each item, assess against the criteria:

1. Does it match any **always-flag** exception? → Important immediately
2. Does it match any **signal** category? → Assess degree of importance
3. Does it match any **noise** category? → Likely ignorable
4. Does it relate to an **active goal** from Step 1? → Elevate importance
5. Does it relate to an **active Kanban task** from Step 1? → Elevate importance
6. Ambiguous? Apply **tiebreaker rule** from criteria file

### Step 4: Determine Routing

Once importance is assessed, map to an action using the routing table. The routing table is **also parameterized per use case** — the caller provides it.

Structure:
```
Item judgment → Pipeline to invoke → Specialist to notify (optional)
```

Common routing patterns:

| Judgment | Default action | Notify |
|----------|---------------|--------|
| Statement/bill needing ingestion | `ingest_document.py <path> --subject "..." --sender "...\" \| notify_ca.py` | ca-expert via Kanban (auto) |
| Contract/legal document | `ingest_document.py <path>` | legal-expert via Kanban |
| Security alert | Flag in immediate output format | None (user sees it directly) |
| Requires a reply | Draft reply, flag for approval | None |
| Informational but worth noting | Include in briefing | None |
| Noise | Skip entirely | None |
| Ambiguous but potentially important | Flag with low priority | None |

### Step 5: Output Structured Decision

For each judged item, produce a structured output (internal — not necessarily sent to the user):

```
Item: <id or preview>
  Source: <gmail/whatsapp/file>
  Judgment: <important / noise / ambiguous>
  Reason: <which criterion triggered>
  Routing: <pipeline command or skip>
  Notify: <specialist or none>
```

This allows:
- Post-hoc verification ("did the framework judge correctly?")
- Debugging ("why did this noise item get flagged?")
- Learning ("this criterion is causing false positives")

## Alternative Pattern — Three-Gate Triage

For rapid sequential triage where you want early exits (fail fast at each gate rather than processing every item through a full assessment). Best for cron-style change detectors (heartbeat, pulse checks) and any real-time triage where most items should be filtered out quickly.

```
Item enters
    ↓
Gate 1 — Categorical Relevance → ❌ Stay silent
    ↓ Pass
Gate 2 — State Assessment → ⏭ Already handled (stay silent)
    ↓ Fresh/unhandled
Gate 3 — Urgency Calibration → ⏭ Routine (stay silent)
    ↓ Urgent / Action needed
→ Route / Flag / Surface
```

### Gate 1 — Categorical Relevance
Does this item belong to a category that could warrant the user's attention?

**Decision flow — one pass is enough:**
1. Does this match an **active kanban goal**? → Pass immediately (goals override categories)
2. Does it belong to one of the defined signal categories below? → Check the category table
3. Ambiguous? Apply the tiebreaker

**Category table pattern** (customise per domain):

| Category | What to look for | Pass example | Fail example |
|---|---|---|---|
| **Family** | Direct ask or decision needed. Not passive updates. | \"Can you review this form?\" | \"Good morning!\" |
| **Financial** | Transactions, bills, statements, direct debit changes. | Credit charge >threshold ✅ | Same monthly bill as always ❌ |
| **Legal/tax/visa** | Solicitor, HMRC, Home Office, property correspondence. | Visa update ✅ | Newsletter from estate agent ❌ |
| **Career** | Specific role outreach, interview logistics. | \"Interview Thursday 2pm\" ✅ | \"You appeared in 5 searches\" ❌ |
| **Security** | Account-recovery alert from any service. Always pass. | \"New sign-in from Chrome\" ✅ | Marketing email about 2FA ❌ |
| **Calendar** | Events needing prep. Events >7 days away → brief mention. | ID documents needed tomorrow ✅ | Recurring reminder in 2 weeks ❌ |
| **Life event** | Confirmations for appointments, bookings, registrations. | Baby shower booking ✅ | |
| **Newsletter / mailing list** | Automated content from a publication, Substack, Medium, Beehiiv, or mailing list. Has no direct ask or decision for the user. | — | Any newsletter or mailing list email ❌ |

**Tiebreaker when uncertain:**
- Sender is known close contact? → Lean toward Pass
- Mentions a specific project or deadline? → Lean toward Pass
- **Looks automated or from a mailing list? → Hard fail** (do NOT pass to Gate 2)
- **Default:** Pass to Gate 2. Gates 2-3 are the real filters — better to over-include at Gate 1 and let the state/urgency gates do the heavy lifting.

### Design Principle: Filter at the Decision Gate, Not at Data-Fetch Time

When building a cron or scanner that processes multiple sources, there is a strong reflex to narrow data collection at the source level (e.g. restrict the Gmail query to only known senders, or filter WhatsApp deltas to only certain chat types). **Resist this reflex.** Prefer broad data collection paired with a sharp decision gate for these reasons:

- **Future-proofing:** A sender you don't know today might be important tomorrow. Narrowing at fetch time creates a blind spot you won't notice until something breaks.
- **Auditability:** It's always visible what Gate 1 passes and what it discards. A narrowed fetch is silent — you can't tell if an item was never fetched or was correctly discarded.
- **Simplicity:** One decision framework (the three-gate triage) applies uniformly to all sources. Source-level filters mean maintaining N separate filter rules for N sources, each with its own blind spots.

**The exception:** Source-level exclusions that have no chance of ever being relevant (e.g. `-category:promotions -category:social` in Gmail — marketing and social noise have zero decision value for any triage). Even then, the rule is: *exclude if you can prove the category will NEVER produce a signal. Otherwise, let Gate 1 handle it.*

### Gate 2 — State Assessment
Has this already been handled or is it still live?

Check against:
- **Kanban** — is there already a task covering this item?
- **Previous processor run** — was this flagged before? Has anything changed?
- **Specialist processing** — has a specialist already processed this (finance handled the bill, legal reviewed the document)?
- **Own prior action** — did the previous heartbeat/cron already route this?

| State | Decision |
|---|---|
| Already tracked in kanban | ⏭ Stay silent (already visible) |
| Already processed by specialist | ⏭ Stay silent (handled) |
| Already surfaced, no change | ⏭ Stay silent (already seen) |
| Fresh — untouched | → Proceed to Gate 3 |

### Gate 3 — Urgency Calibration
If the user does nothing, what happens?

| Threshold | Level | Surface treatment |
|---|---|---|
| Expires within 48h | **Urgent** | 🔴 Flag prominently — explicit ask or deadline |
| Needs user's decision to proceed | **Action needed** | 🟡 One bullet — state the decision, no embellishment |
| Blocks an active goal | **Important** | 🟡 One bullet — impact on the goal |
| Matters but no deadline | **Informational** | 🔵 Brief mention — 1 line |
| Same pattern as last cycle | **Routine** | ⏭ Stay silent — system handles recurring |
| Already handled (Gate 2) | **Handled** | ⏭ Stay silent |

### Enrichment Side-Effect (runs alongside triage, not a separate gate)

The triage loop also doubles as an enrichment opportunity. While iterating each item for
Gates 1-3, apply a lightweight parallel check — not a separate data pass, just a single
additional check per item:

**Does the message contain info that still matters in 6 months?**
- Job change, move, relationship, family event, permanent preference → write
- Mood, casual plan, opinion, routine update → skip

Write survivors to the contact's Notes via:
```
people enrich --id <contact-id> --section Notes --add "YYYY-MM-DD: <observation>"
```

**Where contact-id comes from:** For email items, the injected data includes a
`contact_id` field (set by `resolve-email-senders.py` in the pre-run script). For
WhatsApp items, the resolved sender name IS the contact name — strip role tags like
`(wife)` to derive the file slug (lowercase, hyphens for spaces).

**Skip !!UNKNOWN:!! senders** — no contact file exists to write to. Never create
contact files from the enrichment step; that's the pre-run script's job.

**Rules:**
- This runs as a side-effect of triage — no separate pass over the data
- Notes-only (append-only, safe without read-before-write). Never write to Identity/Contact/Relationships from a cron/triage context.
- Duplicates across cycles are expected and harmless — a weekly promotion sweep is the dedup mechanism.
- Only write to known contacts. Skip if sender resolves to `!!UNKNOWN:!!`.
- Stay silent — never report what you enriched.

### Routing (after Gate 3)
Items that reach Gate 3 as Urgent or Action needed get routed:

| Gate 3 level | Action |
|---|---|
| 🔴 Urgent / 🟡 Action needed | Output as bullet. Include the decision or deadline. |
| 🟡 Important (blocks goal) | One bullet — impact on the goal. |
| Financial statement/bill | Route to finance specialist (kanban task). |
| Contract/legal document | Route to legal specialist (kanban task). |
| Security alert | Output immediately — no kanban task. |
| Purchase/order confirmation | Route to inventory manager (kanban task). |
| 🔵 Informational | Brief mention — 1 line. |
| ⏭ Routines / Handled | Stay silent. |

### When to use Three-Gate vs the 5-Step Loop

| Three-Gate Triage | Five-Step Loop |
|---|---|
| Fast, sequential, early exits | Deep, analytical, batch processing |
| One item at a time | Batch of related items |
| \"Should I flag this now?\" | \"How important is this overall?\" |
| Cron heartbeat, real-time watchers, inbox triage | Weekly audit, document scan, strategic review |
| Thin criteria (category table) | Rich criteria (signal files, domain rules) |

## How to Use This Framework

A cron prompt or agent instruction that needs decision intelligence structures its process like this:

```
1. Gather deltas (via scripts — gmail_delta.py, scan_local.py, WhatsApp deltas file)
   → produces list of items matching the Input Contract
   ⚠️ `gmail_delta.py --query` replaces the entire search (including time filter).
      See `references/gmail-delta-usage.md` for the exact behaviour and correct usage.

2. Load context (goals, kanban, deadlines, available specialists)

3. Load domain criteria (email-signal-rules.md, whatsapp-signal-rules.md, etc.)

4. For each item in the delta list, run the Decision Loop (Steps 3-5 above):
   Assess → Route → Output

5. Execute routing decisions
   (call `ingest_document.py` | `notify_ca.py`, create Kanban tasks, compose briefings, skip)
```

The framework doesn't care what the items are or where they come from. It only cares that they arrive in the Input Contract format and that criteria + routing are available.

## Why This Is Reusable

| Use case | Items come from | Criteria file | Routing map |
|----------|----------------|---------------|-------------|
| Heartbeat | gmail_delta.py + whatsapp deltas | email-signal-rules.md, whatsapp-signal-rules.md | Statements → ingest + CA; security → alert; noise → skip |
| Weekly local scan | scan_local.py | document-signal-rules.md | Documents → ingest + appropriate specialist |
| Future: Contract inbox | gmail scan with legal filter | contract-signal-rules.md | Contracts → ingest + legal-expert |
| Future: Social monitoring | Social API | social-signal-rules.md | Brand mentions → flag; spam → skip |

The LLM never re-invents the decision process. It follows the loop. The only things that change between use cases are:
- **How items are acquired** (different scripts)
- **Which criteria file is loaded** (different rules)
- **Which routing table is applied** (different actions)

## Reference Files

| File | Purpose |
|------|---------|
| `references/email-signal-rules.md` | Email importance criteria (always-flag → signal → noise → tiebreaker) |
| `references/whatsapp-signal-rules.md` | WhatsApp-specific signal rules |
| `references/document-signal-rules.md` | Document/file signal rules |
| `references/routing-table.md` | Routing destinations per item type |
| `references/checklist-scoring-pattern.md` | Alternative triage: binary checklist scoring across 4 dimensions replaces categorical pass/fail at Gate 1 |
