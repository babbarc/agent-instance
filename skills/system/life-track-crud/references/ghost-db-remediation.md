# Ghost DB Remediation — life-tracking.db

Two copies of `life-tracking.db` existed after a file-relocation event:

| Path | Size | Status |
|------|------|--------|
| `/opt/data/life/life-tracking.db` | 196 KB | Live — holds all data |
| `/opt/data/memory/life/life-tracking.db` | 0 bytes | Ghost — stale copy, no tables |

## How It Happened

The canonical DB was moved from `/opt/data/memory/life/` to `/opt/data/life/` during a data-layout restructuring. The old path was not cleaned up because some scripts still referenced it. Cron prompts that hardcoded `/opt/data/memory/life/life-tracking.db` silently read from the 0-byte ghost instead of the live DB — producing empty query results without errors.

## Detection

The ghost surfaced during a meta-review cron run. Step 5 (DB integrity — `find /opt/data -name "life-tracking.db"`) returned 2 matches instead of the expected 1. The agent spent 6+ tool calls investigating: opened both DBs, checked `.tables`, ran `ls -la`, compared schemas.

**Symptoms of a ghost DB in the wild:**
- `find` returns multiple matches for a singleton path
- SQL queries return 0 rows when data should exist
- One copy is 0 bytes or significantly smaller than expected
- `ls -la` shows different modification times on the two copies
- `sqlite3 <path> ".tables"` returns nothing on the ghost

## Fix

```bash
# 1. Identify which copy has data
ls -la /opt/data/life/life-tracking.db /opt/data/memory/life/life-tracking.db
sqlite3 /opt/data/life/life-tracking.db ".tables"      # has tables
sqlite3 /opt/data/memory/life/life-tracking.db ".tables" # empty

# 2. Remove the ghost
rm /opt/data/memory/life/life-tracking.db
```

## Prevention

1. **After any file-relocation event** that moves a canonical DB or data file, run:
   ```bash
   find /opt/data -name "<filename>" 2>/dev/null
   ```
   If more than one match, identify the correct copy and remove ghosts.

2. **Cron prompts** must use `life-track.py` which hardcodes the canonical path (`/opt/data/life/life-tracking.db`). Raw `sqlite3` with inline paths bypasses this safety net.

3. **Cross-cron sweep** — when you fix a stale path in one cron, scan all crons for the same pattern. The ghost DB path was found in 5 prompts, not just one.

4. **Self-prompt audit** (meta-review Step 7) should verify file sizes, not just existence:
   ```bash
   for f in /opt/data/life/life-tracking.db /opt/data/memory/life/life-tracking.db /opt/data/kanban.db; do
     size=$(stat --format=%s "$f" 2>/dev/null || echo "missing")
     echo "$f: $size bytes"
   done
   ```
