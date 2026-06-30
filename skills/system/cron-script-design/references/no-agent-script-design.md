# No-Agent Script Design — Pitfalls & Examples

## Common Pitfalls

### P1. Raw JSON on stdout
`print(json.dumps(result, indent=2))` at the end dumps machine data into the user's chat daily. Unreadable.
**Fix:** Replace with `format_summary()` producing a one-line human-readable string. Keep `--json` as debugging opt-in.

### P2. Writing garbage to DB
External APIs return garbage on unworn days — negative stress, zero active calories, null heart rate.
**Fix:** Add a validation pass before `write_to_life_db()`:
```python
def validate_snapshot(snapshot: dict) -> dict:
    cleaned = dict(snapshot)
    stress = cleaned.get("stress", {})
    if isinstance(stress, dict) and stress.get("avg") is not None and stress["avg"] < 0:
        del cleaned["stress"]
    cal = cleaned.get("active_calories")
    if cal is not None and cal <= 0:
        del cleaned["active_calories"]
    return cleaned
```
Also detect "not used today" state (all-zero metrics + no sleep) and skip writes.

### P3. Duplicate entries on re-run / backfill
**Fix:** Delete existing entries for the date before inserting — makes backfills idempotent.

### P4. Exit code != data quality
Exit non-zero marks cron as errored in scheduler.
**Fix:** Exit 0 always. Reserve non-zero for real infrastructure failures.

### P5. `--json` redundancy with no_agent
Default (no flag) is the production path. `--json` is debugging override.

## Real Example — Garmin Daily Snapshot
📊 Garmin • Jun 18  •  5,793 steps  •  RHR 55  •  Stress 44  •  🔥199 cal
Silent on unworn days (empty stdout). `--json` for debugging. DELETE before INSERT. Validation pass strips negative stress.
