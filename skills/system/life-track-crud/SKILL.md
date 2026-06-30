---
name: life-track-crud
description: CRUD wrapper around /opt/data/life/life-tracking.db — covers all 7 tables with consistent JSON output and parameterised queries. Replaces all raw sqlite3 calls in cron prompts.
annotation: "Life tracking DB: CRUD for /opt/data/life/tracking.db"
version: 1.0.0
---

# Life-Track CRUD

Validated wrapper around `/opt/data/life/life-tracking.db`. Prevents schema drift and enforces consistent access patterns.

## When to Load

Load this skill before any life-tracking DB operation. This is the **only** way to modify the DB — never use raw `sqlite3` in cron prompts.

## Script Location

`/opt/data/scripts/life-track.py`

## Commands

### Signals (`life_signals`)

| Command | Description |
|---------|-------------|
| `life-track.py signal add <domain> <metric> [value] [note]` | Insert signal (default value: ok) |
| `life-track.py signal delete [--date] [--domain] [--metric] [--note-pattern]` | Delete signals matching filters |
| `life-track.py signal list [--domain] [--metric] [--since N] [--limit N] [--json]` | Query signals |

### Goal Tracking (`goal_tracking`)

| Command | Description |
|---------|-------------|
| `life-track.py goal add <domain> <status> [note]` | Insert goal entry (status: on_track/at_risk/off_track/completed) |
| `life-track.py goal list [--domain] [--since N] [--limit N] [--json]` | Query goals |

#### Schema

`goal_tracking` is an append-only log table. Each weekly check-in adds a new row — there is no "update current status." To get the current pulse, query the latest entry per domain.

| Column | Type | Purpose |
|--------|------|---------|
| `id` | INTEGER | Auto-increment PK |
| `domain` | TEXT | Domain name (Career, Family, Social, Finance, Health, Home, Growth) |
| `check_date` | TEXT | ISO date of check-in (YYYY-MM-DD) |
| `status` | TEXT | on_track / at_risk / off_track / completed |
| `note` | TEXT | Free-text note with detail |
| `created_at` | TEXT | Auto-generated timestamp |

#### Latest-per-Domain Query Pattern

When a cron needs the **current pulse** across all domains, use this pattern (not `--since 1` which only catches today's entries):

```sql
SELECT gt.domain, gt.status, gt.note, gt.check_date
FROM goal_tracking gt
INNER JOIN (
  SELECT domain, MAX(check_date) as max_date
  FROM goal_tracking
  GROUP BY domain
) latest ON gt.domain = latest.domain AND gt.check_date = latest.max_date
ORDER BY gt.domain;
```

This is used by the morning briefing script to inject goal status into the LLM's context.

#### Two-Part Goal Data

**Life goals live in two places, and both are read by the morning briefing:**

| Source | What it holds | When to use |
|--------|--------------|-------------|
| `/opt/data/memory/reference/life-goals.md` | Compass — definitions, targets, baselines, how-I-help notes per domain | Context for what each domain means and what success looks like |
| `goal_tracking` table in `life-tracking.db` | Pulse — latest status per domain with check-in note | Current state: which domains are on_track, at_risk, off_track |

**Correct pattern (morning briefing data script):**

1. `cat /opt/data/memory/reference/life-goals.md` → inject compass
2. `goal_tracking latest-per-domain query` → inject pulse

**Wrong pattern:** Only reading one source. The reference file is stale between weekly check-ins; the DB alone lacks the "why this domain matters" context.

### Intervention Log (`intervention_log`)

| Command | Description |
|---------|-------------|
| `life-track.py intervention add <domain> <signal_type> <action> <outcome> [--learn]` | Insert intervention record |
| `life-track.py intervention list [--domain] [--signal-type] [--since N] [--limit N] [--json]` | Query interventions |

### Workout Log (`workout_log`)

| Command | Description |
|---------|-------------|
| `life-track.py workout add <date> <exercise> [--sets N] [--reps N] [--weight <kg>] [--notes]` | Log a set |
| `life-track.py workout list [--since N] [--exercise] [--limit N] [--json]` | Query workouts |

### Nutrition Log (`nutrition_log`)

| Command | Description |
|---------|-------------|
| `life-track.py nutrition add <date> <meal> <food> [--protein <g>] [--calories <kcal>] [--fat <g>] [--carbs <g>] [--fibre <g>] [--sugars <g>] [--notes]` | Log a meal entry with full macros |
| `life-track.py nutrition list [--since N] [--limit N] [--json]` | Query nutrition |

### Daily Summary (`daily_summary`)

| Command | Description |
|---------|-------------|
| `life-track.py summary add <date> [--protein] [--calories] [--fat] [--carbs] [--fibre] [--sugars] [--workout/--no-workout] [--sleep] [--steps] [--resting-hr] [--active-cal] [--stress] [--notes]` | Upsert daily summary with full macros |
| `life-track.py summary get <date> [--json]` | Get single day |
| `life-track.py summary list [--since N] [--limit N] [--json]` | List summaries |

### Relationship Recency (`relationship_recency`)

| Command | Description |
|---------|-------------|
| `life-track.py recency add <contact_name> [--tier 1-3] [--last-contact] [--action] [--note]` | Add contact recency entry |
| `life-track.py recency update <contact_name> [--tier] [--last-contact] [--action] [--note]` | Partial update by contact name |
| `life-track.py recency list [--tier N] [--stale Ndays] [--limit N] [--json]` | List with stale filter |

### Utilities

| Command | Description |
|---------|-------------|
| `life-track.py stats [--json]` | Row counts per table |
| `life-track.py batch` | Read JSON-line operations from stdin (drop-in for cron-persist.py) |

### Garmin Activities (`garmin_activities`)

Auto-created by `life-track.py activity add`. Populated by `garmin-daily-snapshot.py` cron.

| Command | Description |
|---------|-------------|
| `life-track.py activity add <date> <type> --name <text> --distance <km> --duration <min> [--avg-hr] [--max-hr] [--calories] [--elevation] [--pace] [--cadence] [--steps] [--activity-id]` | Log a Garmin activity (dedup via activity_id UNIQUE constraint) |
| `life-track.py activity list [--date <YYYY-MM-DD>] [--since N] [--type running\|cycling] [--limit N] [--json]` | Query activities |

## ⚠️ Pitfall — Stale Paths After Migration

When migrating cron prompts from raw `sqlite3 <path>` to `life-track.py`, the canonical path (`/opt/data/life/life-tracking.db`) is built into the wrapper — you cannot accidentally target the ghost copy at `/opt/data/memory/life/life-tracking.db`. But this only helps if you actually UPDATE the prompt.

**The migration trap:** You edit one cron's prompt (meta-review), declare victory, and move on. But 4 other crons had the same stale reference — the `DB=` variable pattern in fitness-coach crons and the `sqlite3 /opt/data/memory/...` queries in life-admin-radar. Each would waste LLM time on the next run discovering the same ghost DB.

**Protocol when touching life-tracking.db from any cron:**

1. Fix the prompt
2. Update the snapshot (if one exists)
3. **Scan ALL crons** for the same stale pattern:
   ```bash
   python3 -c "
   import json
   with open('/opt/data/cron/jobs.json') as f:
       jobs = json.load(f)
   for job in jobs.get('jobs', []):
       prompt = job.get('prompt', '') or ''
       if '/opt/data/memory/life/life-tracking.db' in prompt:
           print(f'STALE PATH: {job.get(\"name\")} ({job.get(\"id\")})')
       if 'cron-persist.py' in prompt:
           print(f'STALE Wrapper: {job.get(\"name\")} ({job.get(\"id\")})')
       for line in prompt.split(chr(10)):
           if 'sqlite3' in line and 'life-tracking' in line:
               print(f'RAW SQL: {job.get(\"name\")} ({job.get(\"id\")}): {line.strip()[:80]}')
   "
   ```
4. Fix every match. Zero hits before declaring done.

See `references/ghost-db-remediation.md` for the full context of why this path went stale.

## ⚠️ Raw SQL Boundary — Writes vs Reads

**Writes, updates, deletes, and single-table reads:** MUST use `life-track.py`, never raw `sqlite3`.

**Multi-table analytical reads** (joins across `life_signals + workout_log + nutrition_log + daily_summary`): raw `sqlite3` is acceptable — the wrapper can't express cross-table queries in one command. See `references/raw-sql-read-boundary.md` for the accepted query patterns and canonical path.

Raw SQL for writes creates these problems:
- Bypasses path validation (canonical DB is `/opt/data/life/life-tracking.db`, not `/opt/data/memory/life/life-tracking.db`)
- Produces fragile pipe-delimited text
- Creates inconsistent output formats across different cron jobs
- Defeats the single-purpose of life-track.py as the DB access layer

**Correct for writes / single-table reads:**
```bash
python3 /opt/data/scripts/life-track.py signal list --domain health --since 7
python3 /opt/data/scripts/life-track.py signal add system heartbeat ok "silent check"
python3 /opt/data/scripts/life-track.py goal list --json
```

**Wrong (write or single-table read with raw SQL):**
```bash
sqlite3 /opt/data/life/life-tracking.db "SELECT * FROM life_signals WHERE ..."
sqlite3 /opt/data/memory/life/life-tracking.db "SELECT ..."  # stale path!
```

**Acceptable (multi-table analytical read):**
```bash
sqlite3 /opt/data/life/life-tracking.db "SELECT date, metric, value FROM life_signals WHERE domain='health' AND date >= '2026-06-10' ORDER BY date, metric;"
```

See `references/raw-sql-read-boundary.md` for the full accepted pattern list.

## Batch Mode (cron-persist.py compatible)

The `batch` subcommand reads JSON-line operations from stdin, matching the existing `cron-persist.py` format:

```json
{"command":"life-signal","domain":"health","metric":"fitness_morning","value":"ok","note":"Active day"}
{"command":"goal-tracking","domain":"Health","status":"on_track","note":"3 workouts this week"}
{"command":"intervention","domain":"system","signal_type":"meta_review","action":"completed","outcome":"All checks passed"}
```

## DB Schema

Tables: `life_signals`, `goal_tracking`, `intervention_log`, `workout_log`, `nutrition_log`, `daily_summary`, `relationship_recency`, `garmin_activities`

All managed by life-track.py. The only valid path is `/opt/data/life/life-tracking.db`.

## Environment

`LIFE_TRACK_DB` — override DB path (default: `/opt/data/life/life-tracking.db`)

## References

- `references/cron-migration-pattern.md` — Migration guide: `cron-persist.py` → `life-track.py` across 8 crons, with before/after command mapping
- `references/ghost-db-remediation.md` — Recovery from stale 0-byte DB copies (`/opt/data/memory/life/` vs `/opt/data/life/`)
- `references/cron-query-patterns.md` — Quick-reference table: common SQL queries → life-track.py commands, with `--since N` semantics guide AND SQL→CLI query pattern reference (5 common query patterns with quirks)
- `references/raw-sql-read-boundary.md` — When raw SQL is acceptable for multi-table analytical reads vs when life-track.py must be used
