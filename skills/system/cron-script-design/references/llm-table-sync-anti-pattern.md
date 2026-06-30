# LLM Table Sync Anti-Pattern

**Never let the LLM copy data between tables.** If a cron prompt's terminal() step reads from `life_signals` and writes to `daily_summary`, it's wasting tokens on a mechanical copy that adds no judgment value.

## When it looks useful but isn't

- The LLM has already read and parsed the values from the injected data script
- Step 2 writes those same values to a different table via a CLI tool
- The only "judgment" the LLM adds is deciding which flags to pass — a deterministic script could do this in one line
- Risk: the LLM may skip the step entirely, leaving the target table stale

## Where the write belongs

1. **In the collector cron** (if the source is an external API like Garmin) — the no_agent snapshot that writes to `life_signals` should also write to any secondary tables that need the same data. One data source, one writer, multiple readers.
2. **In the data script** (if the source is already in the DB) — a deterministic Python or bash snippet reads from the source table and writes to the target, with no LLM involvement.

## Test

If a cron prompt has a terminal() step that reads existing DB values and writes them to another DB table, flag it:
- Does the step involve any LLM judgment (comparison, triage, classification)? → Keep in prompt
- Is the step a pure data copy with optional flags? → Move to data script or collector
