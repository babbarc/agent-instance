# System Survey Pattern

> When the user asks "document the system", "what do we have?", "review the architecture", or the drift anchor needs updating — run this survey methodology.

## Problem

Standard tools (`read_file`, `search_files`, `terminal`) often fail in restricted environments because they depend on `head`/`cat`/`find`/`wc` being on PATH. You need a reliable workaround.

## Methodology

### Layer 1 — Filesystem Discovery (Use Python, not shell tools)

```python
import os

# Explore the codebase
for root, dirs, files in os.walk('/opt/hermes'):
    depth = root.replace('/opt/hermes', '').count(os.sep)
    if depth > 2: continue  # Max depth
    py_files = [f for f in files if f.endswith('.py')]
    print(f"{'  '*depth}{os.path.basename(root)}/ ({len(py_files)} .py files)")

# Explore home directory
home = os.environ.get('HOME', '/opt/data/home')
for f in os.listdir(home):
    print(f)

# Check file sizes
sz = os.path.getsize('/opt/data/config.yaml')
```

### Layer 2 — Config Parsing

Read key config files with Python's native `open()`:

```python
with open('/opt/data/config.yaml') as f:
    content = f.read()
```

Key configs to survey:
| Path | What it contains |
|------|-----------------|
| `/opt/data/config.yaml` | Main Hermes configuration |
| `/opt/data/SOUL.md` | Joy's identity document |
| `/opt/data/cron/jobs.json` | All cron job definitions |
| `/opt/data/gateway_state.json` | Gateway/platform connection status |
| `/opt/data/auth.json` | Connected platform auth tokens (keys only, not secrets) |

### Layer 3 — Database Schema Inspection

SQLite databases are self-describing — query their schema directly:

```python
import sqlite3
conn = sqlite3.connect('/opt/data/kanban.db')
c = conn.cursor()
for row in c.execute("SELECT name, sql FROM sqlite_master WHERE type='table'"):
    print(f"Table: {row[0]}")
    print(f"  Schema: {row[1][:200]}")
    count = c.execute(f"SELECT COUNT(*) FROM {row[0]}").fetchone()[0]
    print(f"  Rows: {count}")
conn.close()
```

Key databases:
| Path | Purpose |
|------|---------|
| `/opt/data/kanban.db` | Work queue — 7 tables |
| `/opt/data/life/life-tracking.db` | Adaptive feedback — 4 tables |
| `/opt/data/inventory/inventory.db` | Family inventory — 3 tables |

### Layer 4 — Profile & Cron Survey

Profiles: `os.listdir('/opt/data/profiles/')` — each has a SOUL.md and config.yaml. Read them.

Cron jobs: parse `jobs.json` — extract name, schedule, skills, deliver target, prompt (first 100 chars).

### Layer 5 — Skill Catalog

Use `skills_list()` to get all skill names and descriptions. Cross-reference against what exists on disk at `/opt/data/skills/` if you need file sizes or timestamps.

### Layer 6 — Cross-Reference & Synthesize

Build a dependency map by asking:
- What does each cron job depend on? (skills, API auth, database access)
- What profiles are loaded? What pattern do they follow? (kanban-pull vs cron-push)
- What platform integrations are active vs dormant?
- What config settings are customized vs defaults?

### Layer 7 — Document with Drift Awareness

The output document should have:
- **Edition number and date** — so future readers know how current it is
- **Known drift points** — areas that have needed correction before
- **Change log** — track editions
- **Maintenance note** — explicit instruction to update the doc when the system changes

## Pitfalls

- **HOME path discrepancy:** Session says `/opt/data` but subprocesses get `/opt/data/home`. Use `os.environ.get('HOME')` to get the real home. Never hardcode paths.
- **qmd embed timeout after index update:** Running `qmd embed` after `qmd update` may time out (120s) if GPU vector embedding is slow. The BM25 keyword search (`qmd search`) works immediately without vectors. Vector search needs `qmd embed` to complete.
- **`read_file` may claim "File not found"** for existing files — this is a tool execution issue (missing `head`/`cat` on PATH), not a real missing file. Fall back to Python `open()`.
- **`search_files` with `target='files'` may error** with "head: command not found". Use Python `os.walk()` instead.

## When to Run This

| Trigger | Action |
|---------|--------|
| "Document the system" | Full survey (all 7 layers) |
| "What do we have?" | Layers 1-5 (discovery + inventory) |
| Update drift anchor | Layers 1-6 + update system-architecture.md |
| System feels broken | Layer 3 (DB schema check) + Layer 6 (dependency map) |
| New cron/profile added | Sections 3.3 and 3.4 update |
