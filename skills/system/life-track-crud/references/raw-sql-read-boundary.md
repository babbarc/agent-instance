# Raw SQL Read Boundary

The `life-track.py` wrapper covers single-table writes, reads by domain/metric, and summary upserts. But some cron jobs need multi-table joins that the wrapper can't express in one command — e.g. a fitness coach reading `life_signals + workout_log + nutrition_log + daily_summary` for a single date.

## Rule

- **Writes** (INSERT, UPDATE, DELETE) — MUST use `life-track.py`. Never raw SQL.
- **Single-table reads** with simple filters (by domain, metric, date range) — MUST use `life-track.py signal list`, `summary get`, `nutrition list`, etc.
- **Multi-table reads / analytical queries** (joins, aggregations across tables, `MAX(date) FROM workout_log`, date-range scans across several metrics) — raw `sqlite3` is acceptable **for reads only**, using the canonical path `/opt/data/life/life-tracking.db`.

## Accepted Raw SQL Patterns

These are the specific read-only queries that multiple cron jobs (fitness-coach, health-audit) use. Keep this list current — if a cron adds a new analytical query, add it here.

### 1. Full health signals for a date

```sql
SELECT * FROM life_signals WHERE date = '<YYYY-MM-DD>' AND domain='health' ORDER BY metric;
```

### 2. Nutrition entries for a date

```sql
SELECT * FROM nutrition_log WHERE date = '<YYYY-MM-DD>' ORDER BY meal;
```

### 3. Workout entries for a date

```sql
SELECT * FROM workout_log WHERE date = '<YYYY-MM-DD>' ORDER BY exercise, set_number;
```

### 4. Most recent workout date

```sql
SELECT MAX(date) FROM workout_log;
```

### 5. Daily summary for a date

```sql
SELECT * FROM daily_summary WHERE date = '<YYYY-MM-DD>';
```

### 6. Health signal range scan

```sql
SELECT date, metric, value FROM life_signals WHERE domain='health' AND date >= '<YYYY-MM-DD>' ORDER BY date, metric;
```

### 7. Life goals latest-per-domain pulse

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

> Pattern 7 is already documented in the main SKILL.md under `#### Latest-per-Domain Query Pattern` — this reference is the consolidation point for ALL accepted raw SQL patterns.

## Implementation Note

When calling raw SQL from a cron prompt, always use the canonical path:

```bash
sqlite3 /opt/data/life/life-tracking.db "<query>"
```

Never the ghost path `/opt/data/memory/life/life-tracking.db` (see `references/ghost-db-remediation.md`).

## Future

If `life-track.py` ever gains a `snapshot <date>` command that returns all metrics + nutrition + workouts + summary for a given date in one JSON call, this reference becomes obsolete and should be deleted.
