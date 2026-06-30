# Data Script JSON Output — Prompt Boundary

When a data script uses `life-track.py --json` (or any CLI tool outputting JSON), the injected context can contain `[]` (empty array) alongside the traditional `(no data)` text fallback.

## Problem

The short-circuit gate checks for `(no data)` but an empty JSON array `[]` is neither `(no data)` nor meaningful data. DeepSeek leaks reasoning tokens when it sees `[]` and tries to explain "no activities found" instead of skipping.

## Pattern

**Data script outputs:**
```bash
python3 /opt/data/scripts/life-track.py activity list --date "$DATE" --json 2>/dev/null || echo "(no activities)"
```

This can produce either:
- `[{"date":"2026-06-28","activity_type":"running",...}]` — has data
- `[]` — no data (empty array from the wrapper)
- `(no activities)` — subprocess failed entirely

**Prompt must handle all three in the short-circuit gate:**
```
2. If injected sections show "(no data)" or "[]" (empty JSON array), skip silently. No investigation, no fallback.
```

## DeepSeek-Specific Guard

DeepSeek V4 Flash treats an empty `[]` as an implicit "something to process" signal. If not explicitly handled in the short-circuit gate, it will:
- Comment on the empty array: "I see no activities were logged"
- Generate reasoning tokens about what `[]` means
- Fail to suppress output despite `[SILENT]` being the correct response

**Fix:** Always enumerate `[]` alongside `(no data)` in the short-circuit gate. Place the gate as the second rule (after the terminal() directive, before any data analysis) so it fires before decision-making logic.

## When Both Patterns Coexist

Some data script sections use JSON (`life-track.py ... --json`) while others use plain text (`|| echo "(no data)"`). The prompt gate must OR both conditions:

```
If ALL injected sections show "(no data)" or empty "[]", output [SILENT] and stop.
```

This handles the transition period where some sections have been migrated to JSON wrappers and others haven't.
