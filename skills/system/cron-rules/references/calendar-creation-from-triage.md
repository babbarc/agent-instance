# Calendar Event Actions from Cron Triage

**Pattern:** Adding calendar event creation, modification, and deletion as routing side-effects in a cron-driven triage agent (heartbeat-watchdog, Jun 2026). Handles create/modify/delete with dedup via lookup-before-action.

## Prerequisites

- `google_api.py` supports `calendar create` (`--summary`, `--start`, `--end`, `--location`, `--description`, `--attendees`, `--calendar`), `calendar list` (`--start`, `--end`), and `calendar delete` (`event_id`)
- Cron's `enabled_toolsets` includes `terminal` (all commands run via terminal)
- Data pipeline (pre-run script) already injects WhatsApp/email context that the LLM can scan for scheduling requests
- No `update`/`patch` endpoint available — modify = delete + recreate

## The Pattern

Add a new routing option E to the cron's ROUTING section, between existing routing options and OUTPUT RULES:

```
E) **Calendar event action** — create / modify / delete confirmed bookings (BST timezone)

   All dates and times must use BST (+01:00) in ISO8601 format.

   Before any action, run a targeted Lookup to check for existing events.

   **Lookup** (to find an existing event's id or check for conflicts):
   `python3 /opt/data/skills/productivity/google-workspace/scripts/google_api.py
       --account pallav calendar list --start "<ISO8601>" --end "<ISO8601>"`

   **Create** — confirmed new booking (date/time/purpose clear + Pallav agreed):
     1. Run Lookup for the proposed time window
     2. If an event with a matching title (same or contains key words)
        already exists in that window → skip (no duplicate)
     3. Otherwise: `calendar create --summary "..." --start "..." --end "..."
        [--attendees "..."]`

   **Delete** — confirmed cancellation ("cancel the X meeting"):
     1. Run Lookup with a window wide enough to catch the event
        (default 24h around inferred time, widen if unsure)
     2. `calendar delete <event_id>`

   **Modify** — confirmed reschedule ("move it to Thursday"):
     1. Delete the old event (find via Lookup, then delete)
     2. Create the new event with the updated date/time

   Never act on: speculative chat, vague intentions, unconfirmed suggestions.
   On success → report: "📅 <action>: <summary> at <time>" (treat as 🟡 priority)
   On failure → report: "📅 Failed: <summary>"
```

## Trigger Conditions

The LLM scans the pre-injected WhatsApp feed and email data (both sides of conversation). The trigger for routing to E instead of D (output-only):

| Required | Description |
|----------|-------------|
| Date | Explicit date or relative that resolves (tomorrow, Thursday, 8th June) |
| Time | Explicit time or clear inference (3pm, 11am, lunchtime ≈ 12:30) |
| Purpose | What the meeting is about |
| Confirmation | Pallav explicitly agreed ("yeah do it", "sure", "that works") |

**Do NOT act on:** speculative chat ("we should grab coffee"), vague intentions ("let's catch up next week"), unconfirmed suggestions ("does Thursday work?" — no reply yet).

## Additive Routing

Calendar actions run **alongside** the primary routing option (A/B/C/D), not instead of it. If a confirmed booking also needs a kanban task (e.g. "school tour Thursday 11am — also prep the forms"), the LLM picks the primary kanban option AND option E. Enrichment also runs alongside.

The ROUTING section header should state: "Calendar event creation (E) and enrichment run alongside other routing — a single item can create a kanban task AND a calendar event if both are needed."

## Dedup via Lookup

Before creating, the LLM runs a targeted `calendar list` query scoped to the proposed time window. If an event with a matching title exists, creation is skipped. This prevents re-creating events across cron ticks when the same conversation delta appears in multiple runs.

**Title matching:** same title or contains the same key words. "School meeting" matches "School meeting with teacher" but not "Dentist appointment."

## Reporting Priority

Calendar action reports (📅) slot into 🟡 priority in the output ordering. The OUTPUT section should list: "🔴 first, then 🟡 (including 📅 calendar actions), then 🔵. No preamble."

## Key Architecture Decisions

1. **No dedicated calendar triage section needed** — WhatsApp/email sections already detect and flag scheduling conversations. E adds the execution step, not a new detection layer.

2. **No confirmation gate requiring user response** — cron runs autonomously. Use conversation history as the confirmation signal (Pallav said "yes" in the thread).

3. **Tool has no update/patch** — modify is delete + recreate. Acceptable for a 2-hor cron but introduces a failure window: if delete succeeds and create fails, the event is lost. The failure report alerts the user.

4. **Timezone must be explicit** — BST (+01:00) in every ISO8601 date. Without it, the LLM may default to UTC, shifting events by an hour.

## Limitations

- **Latency.** Cron runs every 2h at best. Scheduling request at 11:30 won't fire until 12:00 tick. For same-day bookings, use a real-time handler or create manually.
- **Ambiguous dates.** "Next Thursday" resolves differently depending on day-of-week. LLM uses the injected TIMESTAMP. Unclear references are skipped.
- **No rollback on modify failure.** Delete succeeds, create fails → event lost. User is alerted via failure report.

## Cross-Reference

Covers all three calendar operations (create/modify/delete) with dedup lookup, additive routing, BST timezone enforcement, and 🟡 priority reporting.

## See Also

- `cron-rules` SKILL.md — consolidated output rules, instruction determinism, no forward references
- `cron-prompt-assessment.md` — systematic prompt auditing methodology
