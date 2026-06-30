# Checklist Scoring Pattern

> Alternative to Gate 1's categorical pass/fail. Uses binary yes/no checks across 4 dimensions to produce a continuous priority score. More deterministic than fuzzy category matching because LLMs are significantly more consistent at binary decisions than multi-class classification.
>
> **Status: Implemented in heartbeat-watchdog (v15). Uses semantic binary checks at +1 each.**

## The Core Idea

Replace the category table (which forces each email into exactly one bucket) with a set of independent binary checks. Each "yes" adds +1. The total score maps to an urgency level.

Key design principle: **each check is a semantic concept the LLM recognizes naturally**, not a keyword list. "Please sign by Friday" is clearly time-sensitive without containing the word "deadline."

## Scoring Dimensions

### Sender (0-4, pick one)
- Close family/spouse → 4
- Known professional (solicitor, doctor, active project contact) → 3
- Known friend/colleague → 2
- Emailed recently or unknown person → 1
- Newsletter/mailing list/bulk → 0 (stop — skip remaining dimensions)

### Content (0-6, add all that apply)
- Expresses urgency or a deadline → +1
- Requires the user to take an action → +1
- Requires a decision or approval → +1
- Has financial relevance (payment, amount, transaction) → +1
- Reports a change in status (accepted, confirmed, completed, cancelled) → +1
- Shares personal news or an update from a known person → +1

Max 6 (vs 10 in old weighted system). Each check is +1 — a single keyword doesn't cross score boundaries.

### Relevance (0-4, pick highest)
- Matches an active kanban workstream → 4
- Security/account alert → 4
- Known life goal (property, baby, visa, health, travel) → 3
- Upcoming event → 2
- None of the above → 0

### Context (0-2, add if applies)
- Calendar event in next 7 days relates to sender/topic → +2
- No context match → 0

## Thresholds

Max total: 16 (vs 20 in old system).

| Score | Level | Action |
|-------|-------|--------|
| 10-16 | 🔴 Urgent | 1 bullet with explicit ask/deadline |
| 7-9 | 🟡 Important | 1 bullet with decision/state |
| 4-6 | 🔵 Informational | 1 line |
| 0-3 | ⏭ Silent | Skip entirely |

## WhatsApp — Separate Path (no scoring)

WhatsApp uses a **sender-only Gate 1** and **content-based Gate 3** — not the 4-dimension email rubric. Rationale: WhatsApp messages are short, conversational (no structured data). Fitting them through the full email rubric over-scores casual messages.

**Gate 1 — Sender filter (script already dedups groups and broadcasts):**
- Known contact → proceed
- Bulk/group → silent

**Gate 3 — Content-based (read the message, choose output):**
- Spouse/immediate family: health/emergency→🔴 | decision/time-sensitive→🟡 | casual/logistics→🔵
- Known contacts: important news/ask→🟡 | casual update→🔵 | routine→⏭
- Unknown contacts: any→🔵

## Two-Tier Routing

Items flagged at 🟡 or 🔴 need a routing decision — but not all flagged items need a new kanban task:

| Condition | Action |
|-----------|--------|
| Relates to an active kanban workstream | Update the existing task body with the new information (no new task) |
| New standalone action (new bill, new purchase, new contract) | Create a new kanban task assigned to the relevant specialist |
| Needs user's personal decision first | Create task with status "pending" and note "waiting on user" |
| Informational, already tracked, or security alert | Output only — no task |
| Calendar item needing prep (documents, guests, travel) | Create a named task for the action |

This avoids flooding kanban with redundant tasks for existing workstreams while ensuring new standalone actions don't get lost.

## Preamble Script Pattern

The data-collection script runs *before* the LLM prompt, injecting state into context. This eliminates procedural instructions from the prompt itself:

```
heartbeat-data.sh (preamble)
  → collects: WhatsApp, email (both accounts), calendar, kanban with staleness
  → outputs structured sections with === HEADERS ===
  → stdout is injected ABOVE the LLM prompt

LLM prompt (reads injected data, no terminal calls for data gathering)
  → triages items
  → formats output
```

Benefits:
- Script handles all mechanical data collection (API calls, DB queries)
- LLM only reasons about what's already in context
- Zero "run this command then parse the output" instructions in the prompt
- Date math done by script, not LLM (eliminates off-by-one errors)

Use when: the cron needs to fetch the same data every cycle and the data-gathering instructions would add 500+ tokens to the prompt.

Don't use when: the data changes structure each cycle (ad-hoc queries, user-specified lookups).

## Email Cursor Pattern

For recurring email checks, track the last successful check time in a cursor file instead of hardcoding a window:

```
CURSOR_FILE=/opt/data/tmp/email-cursor
if [ -f "$CURSOR_FILE" ]; then
    LAST_TS=$(cat "$CURSOR_FILE")
    ELAPSED=$(( (now - last) / 3600 + 1 ))  # +1h overlap safety
    EMAIL_SINCE="${ELAPSED}h"
fi

gmail_delta.py --since "$EMAIL_SINCE"
date +%s > "$CURSOR_FILE"  # only on success
```

Properties:
- Covers overnight gaps automatically (no hardcoded 3h window)
- Missed runs widen the next window (self-healing)
- Only advances on successful gmail_delta.py calls (both account checks must succeed)
- Clean after restarts — defaults to 24h if cursor missing

## Dedicated CRUD CLI for Structured Data

For operations that modify structured files (contact enrichment, document metadata, etc.), prefer a dedicated CLI over the LLM doing `read_file` + `patch` directly:

| Approach | Risk |
|----------|------|
| LLM `read_file` + `patch` | Regex errors, section boundary mistakes, corrupting YAML frontmatter |
| Dedicated CLI (e.g. `people enrich --id <id> --section Notes --add "text"`) | Deterministic — script handles section parsing and formatting |

The CLI pattern:
- One atomic operation per call
- Invalid input → error message, no partial write
- Reads the file, modifies surgically, writes back
- Rebuilds dependent indexes (e.g. JID map) after each change

## Comparison to Categorical Pass/Fail

| Email | Old 8-category table | Checklist Score |
|-------|----------------------|----------------|
| Google security alert | Security → ✅ Pass | Sender(1) + Content(1) + Relevance(4) + Context(0) = **6 → 🔵** |
| Solicitor "sign by Friday, EWS1 attached" | Legal → ✅ Pass (tiebreaker) | Sender(3) + Content(3) + Relevance(4) + Context(0) = **10 → 🔴** |
| Octopus monthly bill | Financial — >£500? No → ❌ Fail? | Sender(1) + Content(1) + Relevance(0) + Context(0) = **2 → ⏭** |
| Friend "dinner tomorrow?" | No category fits → depends on tiebreaker | Sender(2) + Content(1) + Relevance(0) + Context(0) = **3 → ⏭** |

## Properties

- **Additive, not exclusive** — an email can score on multiple dimensions simultaneously (no forced single category)
- **Binary checks, not weighted** — each check is +1. No 3-point jumps from a single keyword.
- **Semantic, not keyword-based** — patterns like "urgent/action required/decision/payment due" are replaced with natural-language concepts
- **Transparent** — the breakdown shows exactly which checks fired
- **Graceful** — borderline emails produce a score rather than flipping pass/fail
- **Adjustable** — threshold can be tuned without rewriting the logic
- **LLM-friendly** — binary yes/no on semantic concepts is more consistent than multi-class classification
