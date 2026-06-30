# Windowing Buffer Overlap — Duplicate Triage

When a cron's data-collection script uses a `+ 1` buffer in the window calculation,
consecutive runs produce overlapping time windows. Messages near the end of one
window fall into the next window too, causing the LLM to re-triage the same items
on consecutive ticks.

## The `+ 1` Buffer

```bash
# heartbeat-data.sh pattern
ELAPSED=$(( (NOW_SECS - CURSOR_SECS) / 3600 + 1 ))
EMAIL_SINCE="${ELAPSED}h"
```

If the cursor advances to 16:00 and the next run fires at 18:00:

```
ELAPSED = (18:00 - 16:00) / 3600 + 1 = 3h
Window: 15:00–18:00
```

The 16:00 run used a 3h window (13:00–16:00), so messages at 15:06 appear in both.

## Why the Buffer Exists

The `+ 1` prevents data loss when a run is slightly delayed. Without it:

- Run at 18:02 with cursor at 16:00 → `ELAPSED = 2h` (no buffer, truncated to floor)
- Window: 16:00–18:02 → gaps the 15:06 messages
- With `+ 1` → `ELAPSED = 3h` → window 15:00–18:02 → no gap

The buffer is intentional. The cost is that the last 1-2 hours of the previous window
overlap with the start of the next window, causing duplicate triage for items in the
overlap zone.

## When It Matters

Duplicate triage is harmless in most cases — the LLM re-sees the same WhatsApp
or email and produces the same 🔵 output. The user sees the same item twice,
which is mildly annoying but not wrong.

It becomes a real problem when:

- **Duplicate kanban task creation** — if an item's routing decision is
  non-deterministic, the overlap could cause two identical tasks.
- **Duplicate contact enrichment** — same observation written twice.
- **High-frequency crons** — every-2h heartbeat overlaps 1 hour of each
  window, so overlapping items can persist for multiple cycles.

## Mitigations

### 1. Accept the overlap (current approach)

The `+ 1` buffer is small (~1 hour on a 2h schedule). Duplicate triage for
routine messages is acceptable. The cost (occasional duplicate 🔵 output) is
lower than the cost of missed data from gapped windows.

### 2. Deduplicate in the prompt

Add a rule: "If a message was already triaged in a previous run and nothing
has changed, don't re-output it." This relies on the LLM noticing it's seen
the message before — unreliable without cross-run memory.

### 3. Deduplicate in the data script

Track a second timestamp per source (`last_seen_message_ts`) and filter out
messages older than it. Adds complexity and another state file, but eliminates
LLM-level duplication entirely.

### 4. Remove the buffer (not recommended)

```bash
ELAPSED=$(( (NOW_SECS - CURSOR_SECS) / 3600 ))   # no + 1
```

Saves the overlap but risks gapping on delayed runs. Only safe if the cron
schedule has slack or the data sources don't update faster than the gap.

## How to Detect

Compare the injected data's timestamps across two consecutive cron runs.
If the same message (same sender, same timestamp, same content) appears
in both, it's overlapping. Check `heartbeat-data.sh`'s `ELAPSED` calculation
and compare it to the actual gap between runs.
