# Cron Migration: cron-persist.py → life-track.py

Migrated 8 cron prompts on 7 Jun 2026 to replace `cron-persist.py` and raw `sqlite3` against life-tracking.db.

## The Pattern

| Before | After |
|--------|-------|
| `cron-persist.py life-signal domain metric value note` | `life-track.py signal add domain metric value note` |
| `cron-persist.py goal-tracking domain status note` | `life-track.py goal add domain status note` |
| `cron-persist.py intervention domain signal_type action outcome [--learn]` | `life-track.py intervention add domain signal_type action outcome [--learn]` |
| `cron-persist.py batch << 'EOF'` | `life-track.py batch << 'EOF'` (identical format) |
| `DB=/opt/data/life/life-tracking.db` then `sqlite3 $DB "..."` | `life-track.py <table> <action> [--filters]` |
| `sqlite3 /opt/data/life/life-tracking.db "SELECT ..."` | `life-track.py <table> list [--filters]` |
| `sqlite3 /opt/data/memory/life/life-tracking.db "..."` (stale path) | `life-track.py <table> <action>` (correct path built-in) |

## Batch Format Compatibility

The `life-track.py batch` command accepts the exact same JSON-line format as `cron-persist.py batch`. No change needed to the JSON payloads:

```json
{"command":"life-signal","domain":"health","metric":"workout","value":"ok","note":"3 sessions"}
{"command":"goal-tracking","domain":"Health","status":"on_track","note":"Improving"}
{"command":"intervention","domain":"system","signal_type":"meta_review","action":"completed","outcome":"All clean"}
```

## SQL → CLI Query Pattern Reference

These are the most common query patterns from cron prompts. Each maps a concrete SQL SELECT to the equivalent `life-track.py` command. Verified against real data on 7 Jun 2026.

### Pattern 1: Recent signals from a specific metric

```sql
-- SQL: Last N entries of a metric
SELECT date, value, note
FROM life_signals
WHERE metric='fitness_weekly'
  AND date >= date('now','-28 days')
ORDER BY rowid;
```

```bash
# life-track.py
life-track.py signal list --metric fitness_weekly --since 28
```

`--since N` filters to the last N days. Works on the `date` column. Returns sorted by date descending. The `--metric` filter uses SQL `LIKE '%value%'` internally — it's a fuzzy substring match, NOT exact. `--metric fitness_weekly` matches `fitness_weekly`, `fitness_weekly_summary`, etc. Use the core metric name without wildcards.

### Pattern 2: Today's goal check-in entries

```sql
-- SQL: Goals set for today
SELECT domain, status, note
FROM goal_tracking
WHERE check_date = date('now');
```

```bash
# life-track.py (correct — last 24h window)
life-track.py goal list --since 1
```

`--since N` filters the `check_date` column to `date >= today - N days`. `--since 1` returns entries from the last 24 hours — which captures today's weekly check-in goals if set within that window. The output is sorted by date descending, so today's entries appear first.

**⚠️ Do NOT use `--since 0`** — it adds no date filter and returns ALL goal entries across all dates, which is almost certainly wrong for any cron context.

### Pattern 3: System heartbeat signals (last N hours)

```sql
-- SQL: Heartbeat flags, last 48 hours
SELECT date, note
FROM life_signals
WHERE domain='system'
  AND metric LIKE 'heartbeat%'
  AND date >= date('now','-2 days');
```

```bash
# life-track.py
life-track.py signal list --domain system --metric heartbeat --since 2
```

**⚠️ `--metric` uses SQL `LIKE '%value%'` (fuzzy substring match), NOT exact equality.** `--metric heartbeat` matches `heartbeat`, `heartbeat_watchdog`, `daily_heartbeat` — anything containing `heartbeat` as a substring. This is correct for the cron's original `LIKE 'heartbeat%'` pattern (the wrapper is slightly broader since it matches suffixes too, but in practice metric names don't share ambiguous substrings).

Returns empty with exit code 0 when there's no recent data — that's correct behaviour, not an error.

### Pattern 4: Previous intervention outcome

```sql
-- SQL: Latest meta-review outcome
SELECT date, outcome
FROM intervention_log
WHERE signal_type='meta_review'
ORDER BY rowid DESC
LIMIT 1;
```

```bash
# life-track.py
life-track.py intervention list --signal-type meta_review --limit 1
```

Use `--json` flag for structured output: `--limit 1 --json`. The `--signal-type` filter is exact match.

### Pattern 5: Persist intervention record

```sql
-- SQL: INSERT into intervention_log
INSERT INTO intervention_log (domain, signal_type, action, outcome, date)
VALUES ('system', 'meta_review', 'completed', '<findings> → <action>', date('now'));
```

```bash
# life-track.py
life-track.py intervention add system meta_review completed \
  "<findings> → <action>" \
  [--date YYYY-MM-DD]    # omit for today
```

The `--date` parameter is optional — omit it to auto-use today. Convention for `outcome`: `<finding> → <action>` format for analyzable notes.

### Quick-Reference Table

| What you need | SQL pattern | life-track.py command |
|---------------|-------------|----------------------|
| Recent metric values | `SELECT date, value FROM life_signals WHERE metric='X' AND date >= date('now','-N days')` | `signal list --metric X --since N` |
| Today's goals | `SELECT domain, status FROM goal_tracking WHERE check_date = date('now')` | `goal list --since 1` (last 24h) |
| System domain signals | `SELECT date, note FROM life_signals WHERE domain='system' AND metric LIKE 'X%' AND date >= date('now','-N days')` | `signal list --domain system --metric X --since N` (fuzzy `LIKE '%X%'` match) |
| Latest intervention | `SELECT date, outcome FROM intervention_log WHERE signal_type='X' ORDER BY rowid DESC LIMIT 1` | `intervention list --signal-type X --limit 1` |
| Insert intervention | `INSERT INTO intervention_log (domain, signal_type, action, outcome) VALUES ('X', 'Y', 'Z', 'W')` | `intervention add X Y Z "W"` |

## Crons Migrated

| Cron | ID | Key Change |
|------|----|-----------|
| meta-review | ac93cdf9465c | Step 2: 4 raw SQL → `life-track.py` calls. Step 9 persist updated |
| life-admin-radar | 84365a8f4b27 | DB Population: 4 aggregate SQL → `stats` + piped domain breakdown |
| fitness-coach-weekly | ecd66419e2ba | 7-day loop replaced with `--since 7` calls |
| fitness-coach-morning | 1bdb9f81d0a0 | Yesterday queries via `--since 1` + `summary get` |
| weekly-checkin | 5c5300a6c4e1 | Batch persist: `life-track.py batch` |
| morning-briefing | 60b5b1b122d8 | Persist: `signal add` |
| fitness-coach-evening | fcea357947f1 | Persist: `signal add` |
| rightmove-tracker | 6bc227a3a83c | Persist: `signal add` |
