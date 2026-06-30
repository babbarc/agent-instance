# API Collector Pattern — Garmin Case Study

## Principle

Only the designated collector cron calls the external API. Every other cron reads the data from the life-tracking DB. This prevents redundant API calls, rate-limit contention, and maintains a single source of truth.

## Architecture

```
garmin-daily-snapshot (no_agent, 06:45)
  └── calls garmin-connect.py stats/sleep/hrv
  └── writes compact metrics to life_signals (domain='health')
       │
       ├── morning-briefing (07:00)
       │     └── reads life_signals via sqlite3
       │
       ├── fitness-coach-morning (07:15)
       │     └── reads life_signals via sqlite3
       │
       ├── fitness-coach-weekly (Sun 17:00)
       │     └── reads life_signals via sqlite3 (7-day window)
       │
       └── fitness-coach-evening (20:00)
             └── reads life_signals via sqlite3
```

## Implementation pattern

**Collector cron** (no_agent, runs silently):
- Calls external API
- Extracts compact metrics (not raw JSON dumps)
- Writes structured rows to `life_signals` with domain='health' and canonical metric names

**Reader cron** (data script):
- Queries `life_signals` using sqlite3 with `|| echo "(no data)"` fallback
- No knowledge of the external API — only knows the DB schema

**Query template:**
```bash
sqlite3 "$DB" "SELECT metric, value FROM life_signals
  WHERE date='$TARGET_DATE' AND domain='health'
  AND metric IN ('steps','resting_hr','sleep_seconds','deep_sleep_seconds',
                 'hrv_last_night','stress_avg','active_calories');" \
  2>/dev/null || echo "(no data)"
```

## Canonical metric names in life_signals

| Metric | Source field | Example value |
|--------|-------------|---------------|
| `steps` | totalSteps | "7997" |
| `resting_hr` | restingHeartRate | "51" |
| `sleep_seconds` | sleepTimeSeconds | "28380" |
| `deep_sleep_seconds` | deepSleepSeconds | "4080" |
| `hrv_last_night` | lastNightAvg | "49" |
| `stress_avg` | averageStressLevel | "26" |
| `active_calories` | activeKilocalories | "229" |

## Handling no-data gracefully

Reader scripts use `|| echo "(no data)"` for DB queries. The LLM prompt's short-circuit gate should include the health signals in its quiet-day check. If the collector cron didn't write data (watch not worn, API down), the reader gets "(no data)" gracefully without failing the run.

## Why not just inline the API call

- **Rate limits:** Garmin API rate-limits aggressively. 7 API calls per cron × multiple crons = guaranteed contention.
- **Latency:** Each API call takes 3-15s. 7 calls × 2 crons = 42-210s of wall-clock time spent on data gathering.
- **Token cost:** Raw Garmin JSON dumps are ~5-15KB each. The compact DB metrics are ~200 bytes.
- **Single source of truth:** If the API schema changes, only the collector cron needs updating. Reader crons are unaffected.
