# Stateless Cursor Migration Pattern

Template for migrating a data-collection cron from internal watermarks to
stateless `--since` filtering with `last_status`-gated advancement.

## Before

Script has internal watermark/cursor management:
```
CURSOR=/tmp/<source>-cursor
python3 <script.py>  # internally reads/writes CURSOR
```

Problems: /tmp cleared on reboot, watermark gets lost, script re-reads
entire data source. Separate cursor per source = drift between them.

## After

1. Script becomes stateless — accepts `--since <N>h` (same format as `gmail_delta.py`)
2. Orchestrator script (`heartbeat-data.sh`) manages a single cursor at `/opt/data/.cache/heartbeat-last-ok`
3. Cursor advances only when previous run `last_status == "ok"`:

```bash
# Read job state from jobs.json
LAST_STATUS=$(python3 -c "...")
LAST_RUN_AT=$(python3 -c "...")

# Advance cursor if previous run succeeded
if [ "$LAST_STATUS" = "ok" ] && [ -n "$LAST_RUN_AT" ]; then
    date -d "$LAST_RUN_AT" +%s > "$CURSOR_FILE"
fi

# Calculate window from cursor
if [ -f "$CURSOR_FILE" ]; then
    ELAPSED=$(( (NOW - $(cat "$CURSOR_FILE")) / 3600 + 1 ))
    SINCE="${ELAPSED}h"
fi

# Both scripts stateless
python3 whatsapp_delta.py --since "$SINCE"
python3 gmail_delta.py --account x --since "$SINCE"
```

## Why This Works

- **Cursor persists across reboots** — `/opt/data/.cache/` is on persistent storage
- **No LLM involvement** — advancement is mechanical, happens in data-collection script
- **Natural gap coverage** — if a run fails, cursor stays put; next run widens window
- **Unified cursor** — one timestamp for all sources, no drift between email and WhatsApp cursors
- **No data loss on failure**:
  - Run A succeeds → cursor advances to A's time
  - Run B fails → cursor stays at A's time
  - Run C checks `last_status=error` → doesn't advance → window = (C - A) covers missed window
