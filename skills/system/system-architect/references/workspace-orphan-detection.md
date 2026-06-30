# Workspace Orphan File Detection

> **Purpose:** Systematically find files in `/opt/data/` that have no active consumer — stale session logs, migration archives, backup zips, empty directory skeletons, temp config files, one-off scripts and their outputs.
> **First used:** 12 May 2026 — swept `/opt/data/` entirely and identified ~718 MB of orphaned/cleanable space.

---

## What This Catches

- Migration/backup artifacts that were used once and never cleaned
- Empty directory skeletons from abandoned organizational schemes
- One-off extraction/check scripts that did their job and never ran again
- Stale config backups (.bak files from pre-migration)
- Cache/build artifacts that aren't used anymore
- Duplicate directory trees (e.g., skills mirror at both HERMES_HOME and HOME)
- Temp files with random-suffix names (`.config_*.tmp`, `google_oauth_state.txt`)
- Old session logs that accumulate with no retention policy
- Profile subdirectories (cron, plans, sessions, workspace) created but never populated

---

## Detection Methodology

Run these stages in order. Each stage feeds the next.

### Stage 1 — Map the Full Tree

Start with a wide view, then narrow:

```bash
# Directory structure (depth-limited)
find /opt/data -maxdepth 3 -type d | sort

# All files at root level (often the worst offenders)
find /opt/data -maxdepth 1 -type f -exec ls -lh {} \; | awk '{print $5, $9}' | sort -rh

# Files deeper in specific suspect zones
find /opt/data/migration -type f | sort
find /opt/data/backups -type f | sort
find /opt/data/sessions -type f | sort | tail -20
find /opt/data/spawn-trees -type f | sort
```

### Stage 2 — Identify Active/Dependency Files

Build a reference set of files that ARE in use:

- **Config files:** `config.yaml`, `.env`, `SOUL.md`
- **Databases:** `kanban.db`, `state.db`, `hermes.db`, `inventory.db`, `life-tracking.db`
- **Active skills:** everything under `~/skills/` (HOME/skills/) — these are procedural memory
- **Active cron jobs:** use `cronjob list` — any `no_agent` scripts must be kept
- **Runtime state:** `gateway_state.json`, `processes.json`, lock files (may be needed at restart)
- **Active data storage:** `$HERMES_HOME/memory/` tree, `~/kanban/` workspaces, `~/contacts/`, `inventory/`, `statements/`

### Stage 3 — Cross-Reference Against Active State

For each suspicious file/directory, ask:

- **Is it referenced by any active cron job?** — check `cronjob list` output; scan SKILL.md files for hardcoded paths
- **Is it referenced by config.yaml?** — grep for the path in config
- **Is it a currently-active session or log?** — check `find ... -mtime -1` to see if it's being written today
- **Is it a duplicate of something in the active tree?** — use `diff -rq dirA dirB` to find divergences

### Stage 4 — Classify by Tier

**Tier 1 — Safe to remove:** Migration archives, empty dir skeletons, stale backup files, one-off scripts that ran once. No active process references them.

**Tier 2 — Needs retention policy:** Session logs. They ARE being actively written, but old ones (3+ days) have no consumer. Solution: create a cleanup cron similar to `cron-output-cleanup.sh`.

**Tier 3 — Needs review:** Duplicate directory trees where one copy is actively referenced by hardcoded paths. Removal requires updating those refs first.

### Stage 5 — Size-Prioritize Recommendations

```bash
# Get sizes for every suspect
du -sh /opt/data/backups/ /opt/data/migration/ /opt/data/sessions/ /opt/data/spawn-trees/ /opt/data/skills/ /opt/data/01-*/ /opt/data/02-*/ # etc.

# Evaluate cost/benefit: a 548 MB backup zip is worth more effort than 12 KB of scripts
```

---

## Common Orphan Categories (with examples from 12 May 2026 sweep)

| Category | Example | Telltale Signs |
|----------|---------|--------------|
| **Migration archives** | `/opt/data/migration/` | Dated subdirectory (`20260508T063130`), contains `MIGRATION_NOTES.md`, old configs |
| **Pre-migration backups** | `/opt/data/backups/pre-migration-*.zip` | Large zip, dated just before migration, contains `SOUL.md`, old `.env` |
| **Empty directory skeletons** | `/opt/data/01-*/` through `/opt/data/09-*/` | 0 files, directory names with trailing commas (`Passports,/`, `Citi,/`) |
| **One-off scripts** | `/opt/data/check_*.py`, `/opt/data/extract_*.py` | No cron references, not in any skill, named after a single operation |
| **One-off outputs** | `/opt/data/extracted_tax_data.txt`, `*.bak.*` | Text files with extracted data, temp-looking names |
| **Stale build caches** | `/opt/data/.skills_prompt_snapshot.json` | JSON snapshot, not referenced by any config |
| **Spawn tree artifacts** | `/opt/data/spawn-trees/` | `_index.jsonl` + dated `.json`, no active reference |
| **Temp config files** | `*.tmp`, `google_oauth_state.txt` | Random-suffix names, small files at root |
| **Empty profile subdirs** | `profiles/*/cron/`, `profiles/*/sessions/` | Created by profile scaffolding, never populated |
| **Duplicate skills dirs** | `/opt/data/skills/` vs `/opt/data/home/skills/` | Same structure, same files. Check which one SKILL.md references point to |

---

## Discernment: Duplicate vs Complementary vs Bind Mount vs Symlink

Two paths with similar content are NOT always duplicates. Before deleting:

1. **Check for hardcoded references** — `grep -rl '/opt/data/oldpath' ~/skills/` — the old path might be the one all the SKILL.md files point to
2. **Check SKILL.md files** — if SKILL.md in one location references scripts at the other, they're complementary, not duplicates
3. **Check .usage.json and .bundled_manifest** — if the hub tracks both, removal may break the hub
4. **Plan the migration:** update references → verify → remove old copy

### 🧬 Inode Comparison Technique

The most authoritative way to determine if two paths are the same directory is inode comparison:

```bash
# Check if two directories are the same filesystem entry
stat -c "%i %h %n" /path/A /path/B
# Same inode (%i) = same directory, even if reached via different paths
# Links (%h) > 1 and same inode = hardlinked or bind-mounted

# Check if a path is a symlink
ls -la /path/to | grep suspect-dir
# lrwxrwxrwx ... scripts -> /opt/data/scripts   <-- this is a symlink

# Deep comparison: are the contents identical?
diff -rq /path/A /path/B | head -20
# If nothing differs (or only metadata like .bundled_manifest, .usage.json), they're duplicates
```

**Real-world example (12 May 2026):**
`/opt/data/home/scripts` and `/opt/data/scripts` had the **same inode** (72001769) for the directory AND the same inode for every file inside — because `/opt/data/home/scripts` was a **symlink** → `/opt/data/scripts`, not a separate copy. The diff returned nothing, and the inode check confirmed they were the same entity. Only `stat` could confirm this definitively.

**Why this matters:** If you assume they're separate copies (both look like real directories with files), you might waste effort patching files in the wrong place, or worse, delete the real directory. The inode check prevents this.

---

## Reporting Format

Present findings in a structured report:

```
## Tier 1 — Safe to Remove (XXX MB reclaim)
| Orphan | Size | Why |
|--------|------|-----|

## Tier 2 — Needs Policy (up to XXX MB)
---

## Tier 3 — Needs Review (XXX MB)
---
```

Each entry in Tier 1 should have: path, size, and a one-line justification. High-impact items first (largest size).

---

## See Also

- **`references/pre-flight-system-audit.md`** — checks system integrity (broken refs, missing skills). Run this AFTER cleanup to ensure nothing broke.
- **`references/path-dependency-tracing.md`** — for deep trace of specific path references before deleting anything with hardcoded dependents.
