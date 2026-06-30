# Debugging Missing Kanban Tasks

**Protocol:** When the user says a task exists in kanban but `kanban.py get <id>` or `kanban.py list` doesn't find it.

## Step 1 — Verify query, not assume gone

Run the exact ID the user mentioned, plus a pattern search:

```bash
python3 /opt/data/scripts/kanban.py get t_apply_priyanka_schengen
python3 /opt/data/scripts/kanban.py list --format json | python3 -c "
import sys,json
for t in json.load(sys.stdin):
    body = t.get('body','') or ''
    title = t.get('title','') or ''
    if 'schengen' in body.lower() or 'visa' in title.lower():
        print(t['id'], t['title'], t['status'])
"
sqlite3 /opt/data/kanban.db "SELECT id, title, status FROM tasks WHERE id LIKE '%schengen%' OR body LIKE '%TLScontact%'"
```

If still nothing → proceed.

## Step 2 — Check for DB corruption/recovery artifacts

Look for backup and recovery files alongside the DB:

```bash
ls -la /opt/data/kanban.db*
```

Common patterns:
- `kanban.db.corrupted_<timestamp>` — automatically created backup before recovery
- `kanban.db.rebuilt` — rebuilt version after corruption
- `kanban.db.corrupted` — current corrupt state

Check the rebuilt DB for the task — it may have been lost during recovery:

```bash
sqlite3 /opt/data/kanban.db.rebuilt "SELECT id, title, status FROM tasks WHERE id LIKE '%schengen%'"
```

**Known case (8 Jun 2026):** `t_apply_priyanka_schengen` existed and was actively heartbeated until 2 Jun 12:00. At 14:01 on 2 Jun, the kanban DB corrupted. The 4 Jun rebuild recovered only 12 of the original tasks — the Schengen task was in a corrupted page and never recovered. The user remembered it existing and was right.

## Step 3 — Find when it was last seen

Session search for the task ID:

```bash
session_search(query="t_apply_priyanka_schengen", limit=5, sort="newest")
```

The most recent session that successfully queried the task gives you the last-known-good timestamp. Sessions after that with no mention suggest the deletion window.

## Step 4 — Check git for kanban.db history

```bash
cd /opt/data && git log --all --oneline -p -S "t_apply_priyanka_schengen"
```

Note: `kanban.db` is a SQLite binary, not text-tracked in git. Git won't show the binary diff but may show references in scripts, cron prompts, or markdown files.

## Step 5 — Check cron outputs for the last reference

Heartbeat and briefing cron outputs may contain task body dumps showing the task existed at specific timestamps:

```bash
grep -rl "t_apply_priyanka_schengen" /opt/data/cron/output/ 2>/dev/null | tail -5
```

Read the most recent one to confirm last-known-good state.

## Step 6 — Cross-reference orphaned data in prose

If the task carried dates/appointments/deadlines, they may survive in prose notes (not as structured data). Check:

```bash
sqlite3 /opt/data/life/life-tracking.db "SELECT domain, status, note, check_date FROM goal_tracking WHERE note LIKE '%appt%' OR note LIKE '%visa%' OR note LIKE '%Jun%'" 2>/dev/null
```

Goal tracking notes sometimes carry prose like "French visa appt 16 Jun" — these are fragments, not structured calendar/kanban entries. If found:
1. Recreate the kanban task with the full body
2. Add the appointment to Google Calendar
3. Don't assume it's handled just because someone wrote a note a week ago

## Root Cause Classification

| Finding | Likely cause | Action |
|---------|-------------|--------|
| DB has corruption artifacts nearby | SQLite corruption ate the row | Recreate task from session history + goal tracking |
| Git shows explicit delete | Someone ran `kanban.py delete <id>` | Recreate if info still relevant, and check for orphaned dates (see pitfall in SKILL.md) |
| No trace found | Task may never have been in this kanban instance (e.g. different profile, different DB) | Ask the user for more context — where they expect to see it |
| Task exists in rebuilt DB but not current | DB was rebuilt and the task was added back later but not this one | Migrate from rebuilt if still relevant |

## Prevent Recurrence

After resolving a missing task:
1. Recreate the task with full body from session history / goal tracking notes
2. Add any appointment/event to Google Calendar so structured data pipelines pick it up
3. If the task was lost due to corruption, note that the DB needs backup/health monitoring
