# Cron Query Patterns — Raw SQL → life-track.py

Common SQL query patterns found across cron prompts, mapped to equivalent `life-track.py` commands.

## Signal Queries

| Raw SQL | life-track.py equivalent |
|---------|-------------------------|
| `SELECT date, value, note FROM life_signals WHERE metric='X' AND date>=date('now','-N days') ORDER BY rowid` | `life-track.py signal list --metric X --since N` |
| `SELECT date, note FROM life_signals WHERE domain='X' AND metric LIKE 'Y%' AND date>=date('now','-N days')` | `life-track.py signal list --domain X --metric Y --since N` |
| `SELECT COUNT(*) as cnt, domain FROM life_signals GROUP BY domain` | `life-track.py stats` (per-table counts) + pipe through Counter for domain breakdown |
| `SELECT date, note FROM life_signals WHERE domain='system' AND metric LIKE 'heartbeat%' AND date>=date('now','-2 days')` | `life-track.py signal list --domain system --metric heartbeat --since 2` |

## Goal Tracking Queries

| Raw SQL | life-track.py equivalent |
|---------|-------------------------|
| `SELECT domain, status, note FROM goal_tracking WHERE check_date=date('now')` | `life-track.py goal list --since 1` |
| `SELECT COUNT(*) FROM goal_tracking` | `life-track.py stats` |
| `SELECT domain, status, COUNT(*) FROM goal_tracking WHERE check_date > date('now', '-30 days') GROUP BY domain, status` | `life-track.py goal list --since 30 --json` (parse client-side) |
| `SELECT gt.domain, gt.status, gt.note, gt.check_date FROM goal_tracking gt INNER JOIN (SELECT domain, MAX(check_date) as max_date FROM goal_tracking GROUP BY domain) latest ON gt.domain = latest.domain AND gt.check_date = latest.max_date` | **No direct CLI equivalent** — use raw SQL via `life-track.py` cli `--raw` or cron data script. This is the canonical "latest pulse per domain" query. |

## Intervention Log Queries

| Raw SQL | life-track.py equivalent |
|---------|-------------------------|
| `SELECT date, outcome FROM intervention_log WHERE signal_type='X' ORDER BY rowid DESC LIMIT 1` | `life-track.py intervention list --signal-type X --limit 1` |
| `SELECT COUNT(*) FROM intervention_log WHERE signal_type='X' AND learn='Y'` | `life-track.py intervention list --signal-type X --json` (count client-side) |

## Workout Log Queries

| Raw SQL | life-track.py equivalent |
|---------|-------------------------|
| `SELECT exercise, reps, weight_kg, notes FROM workout_log WHERE date='YYYY-MM-DD'` | `life-track.py workout list --since 1` (covers yesterday) |
| `SELECT MAX(date) FROM workout_log` | `life-track.py workout list --limit 1` (most recent date in first result) |
| `SELECT COUNT(*) || ' exercises' FROM workout_log WHERE date='YYYY-MM-DD'` | `life-track.py workout list --since 1` (read the output) |
| `SELECT date, COUNT(DISTINCT exercise) FROM workout_log WHERE date >= date('now', '-7 days') GROUP BY date` | `life-track.py workout list --since 7 --json` (deduplicate client-side) |

## Nutrition Log Queries

| Raw SQL | life-track.py equivalent |
|---------|-------------------------|
| `SELECT meal, food, protein_g FROM nutrition_log WHERE date='YYYY-MM-DD'` | `life-track.py nutrition list --since 1` |
| `SELECT COALESCE(SUM(protein_g), 0) FROM nutrition_log WHERE date='YYYY-MM-DD'` | `life-track.py nutrition list --since 1 --json` (sum protein_g from output) |
| `SELECT date, SUM(protein_g) FROM nutrition_log WHERE date >= date('now', '-7 days') GROUP BY date` | `life-track.py nutrition list --since 7 --json` (aggregate client-side) |

## Daily Summary Queries

| Raw SQL | life-track.py equivalent |
|---------|-------------------------|
| `SELECT steps, resting_hr, sleep_hours, ... FROM daily_summary WHERE date='YYYY-MM-DD'` | `life-track.py summary get YYYY-MM-DD` |
| `SELECT date, steps, sleep_hours, workout_yn FROM daily_summary WHERE date >= date('now', '-7 days') ORDER BY date` | `life-track.py summary list --since 7` |

## Batch Mode (Replacements for cron-persist.py)

| Old | New |
|-----|-----|
| `cron-persist.py life-signal domain metric value note` | `life-track.py signal add domain metric value note` |
| `cron-persist.py goal-tracking domain status note` | `life-track.py goal add domain status note` |
| `cron-persist.py intervention domain signal_type action outcome [--learn]` | `life-track.py intervention add domain signal_type action outcome [--learn]` |
| `cron-persist.py batch << 'EOF'` | `life-track.py batch << 'EOF'` (identical JSON format) |

## `--since N` Semantics

The `--since N` flag filters for records where `date >= today - N days`. It is an inclusive lower bound:

| `--since` | Effective date filter | Use for |
|-----------|----------------------|---------|
| `--since 1` | Today only | Daily check-in goals, yesterday's logs |
| `--since 2` | Today + yesterday | Heartbeat flags (48h window) |
| `--since 7` | Last 7 days | Weekly summary, weekly patterns |
| `--since 28` | Last 28 days | Monthly trajectory |
| `--since 30` | Last 30 days | Monthly goal status breakdown |
| `--since 90` | Last ~3 months | Intervention history |

## Output Format Decisions

- **Table output** (default) — human-readable, good for cron prompts where the LLM reads the data and makes decisions
- **`--json`** — structured, good for pipe-to-commands or when the LLM needs to aggregate/sum values programmatically
- **Never pipe json through `grep` or `awk`** — use `python3 -c "import sys,json; ..."` for reliable JSON parsing
