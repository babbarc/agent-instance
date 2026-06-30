# Path & Symlink Dependency Tracing

> **Purpose:** Systematically find ALL references to a filesystem path, symlink, or directory across the full system — files, cron, memory tree, skills, source code, configs, environment variables.
>
> **When to use:** Before changing a path, removing a symlink, or standardizing a directory convention. Ensures you find every reference before acting.
>
> **First used:** 12 May 2026 — traced all `~/scripts` symlink references across the Joy system (memory files, cron jobs, shell scripts, Hermes source code) to prepare a standardization plan.

---

## The Technique (7-Phase Scan)

This is a **full-system sweep**. Each phase is independent — run all of them. Do not stop after phase 1.

### Phase 1 — Identify the Entity

```python
from pathlib import Path
import os

target = os.path.expanduser('~/scripts')  # or whatever the user asked about
print(f"Is symlink: {Path(target).is_symlink()}")
if Path(target).is_symlink():
    print(f"Symlink: {target} → {os.readlink(target)}")
print(f"Resolved: {Path(target).resolve()}")
```

**Output:** Know the literal string, the resolved path, and any symlink target.

### Phase 2 — Literal String Search

Search for all variants of the path:

```python
paths_to_search = [
    '~/scripts',                    # home-relative (with tilde)
    '/opt/data/home/scripts',       # full home path
    '/opt/data/scripts',            # resolved target
    '~/./scripts',                  # quirky variant with ./
    'scripts/',                     # relative (in path context)
]
```

For each, use `search_files` across:
- `/opt/data/memory/` — memory tree docs
- `~/skills/` — skill files (both SKILL.md and references/)
- `~/kanban/` — kanban board artifacts
- `~/scripts/` — the scripts themselves (they may self-reference)
- `~/.hermes/` — Hermes config and patches
- `/opt/hermes/` — Hermes source code (for resolution logic)

Also search config files:
```python
import os, subprocess
r = subprocess.run(['grep', '-rn', 'HERMES_HOME', '/opt/data/'], capture_output=True, text=True)
```

### Phase 3 — Cron Job Script Audit

List all cron jobs and check which reference the path:

```python
import json
with open('/opt/data/home/.hermes/cron/jobs.json') as f:  # canonical (no expanduser)
    jobs = json.load(f).get('jobs', [])

for job in jobs:
    script = job.get('script')
    prompt = job.get('prompt', '')
    name = job.get('name', 'unnamed')
    
    # Check script field
    if script and (target in script or resolved in script):
        print(f"  CRON script field: {name} -> {script}")
    
    # Check prompt for path references
    for variant in path_variants:
        if variant in prompt:
            print(f"  CRON prompt: {name} references {variant}")
```

### Phase 4 — Memory Tree Scan

Search every `.md` file in `/opt/data/memory/` for all path variants:

```python
import os, re
root = os.path.expanduser('/opt/data/memory/')
variants = ['$HERMES_HOME/scripts', '/opt/data/scripts']
for dirpath, dirnames, filenames in os.walk(root):
    for f in filenames:
        if f.endswith('.md'):
            path = os.path.join(dirpath, f)
            with open(path) as fh:
                content = fh.read()
            for v in variants:
                if v in content:
                    rel = os.path.relpath(path, root)
                    print(f"  MEMORY {rel}: references {v}")
```

### Phase 5 — Skills Scan

Search every skill file (SKILL.md and references/) for path variants:

```python
import os
variants = ['~/scripts', '/opt/data/scripts', '/opt/data/home/scripts', '~/./scripts']
root = os.path.expanduser('~/skills/')
for dirpath, dirnames, filenames in os.walk(root):
    for f in filenames:
        if f.endswith('.md'):
            path = os.path.join(dirpath, f)
            with open(path) as fh:
                content = fh.read()
            for v in variants:
                if v in content:
                    rel = os.path.relpath(path, root)
                    print(f"  SKILL {rel}: references {v}")
```

### Phase 6 — Hermes Source Code Resolution

**Critical:** The cron scheduler resolves script paths at runtime. You must check:

1. **`HERMES_HOME` env var** — what does it resolve to?
   ```python
   import os
   print(f"HERMES_HOME: {os.environ.get('HERMES_HOME', 'NOT SET (defaults to ~/.hermes)')}")
   ```

2. **Scheduler source** — how does it resolve script paths?
   ```python
   # In cron/scheduler.py: _run_job_script()
   # scripts_dir = _get_hermes_home() / "scripts"
   # path = (scripts_dir / raw).resolve()
   ```

3. **Validation source** — what paths does the API accept?
   ```python
   # In tools/cronjob_tools.py: _validate_cron_script_path()
   # Blocks absolute and ~-prefixed paths at the API boundary
   # Only relative paths within HERMES_HOME/scripts/ allowed
   ```

**This is critical.** The cron job stores bare script names (`script: "sync-docs.sh"`), but at runtime the scheduler resolves them against `$HERMES_HOME/scripts/`. The actual files live at the resolved path. If the file isn't at `$HERMES_HOME/scripts/<name>`, the job silently fails.

### Phase 7 — Compile Findings & Plan

Group findings into a table:

| Path Variant | Locations | Status |
|-------------|-----------|--------|
| `$HERMES_HOME/scripts/` | wa-watchdog.sh, garmin-snapshot.sh, system-architecture.md | ✅ Correct |
| `~/scripts` or `~/./scripts/` | pending.md | ❌ Fix |
| `/opt/data/home/scripts/` | start-browser-proxy.sh | ❌ Fix |
| Symlink itself | Filesystem root | ⚠️ Decide |

Then create a phased plan.

---

## Phase 8 — Remediation (Mass Path Refactoring)

### 8.0 — Directory Tree Relocation (Physical Move + References)

When the task is to **physically move files** from one directory to another (not just change how they're referenced), follow this expanded sequence:

**Step 0 — Backup:** Before any file move, ensure the source is backed up:
```bash
cp -a /old/path /tmp/path-backup  # safety copy before migration
```

**Step 1 — Physical copy:** Copy (not move) the tree to the target, merging with any existing content:
```bash
cp -a /old/path/* /new/path/
```

Keep the source intact until verification passes — this gives you a clean rollback path.

**Step 2 — Hardlink recreation:** If any files in the source tree are hardlinked to external locations (e.g., `SOUL.md` hardlinked between `$HERMES_HOME/SOUL.md` and `~/memory/SOUL.md`), recreate the hardlink at the new location:
```bash
ln /external/path/SOUL.md /new/path/SOUL.md
```
Verify: `stat -c "%i" /external/path/SOUL.md /new/path/SOUL.md` — same inode, link count ≥2.

**Step 3 — Text reference replacement:** Run the full Phase 8a-8d text replacement steps below. **Order matters when replacing multiple path variants that share a common prefix:** replace more-specific variants first, then less-specific. For example, `~/./memory/` contains `~/memory/` as a substring — if you replace `~/memory/` first, then `~/./memory/` won't match. The safe ordering is:
1. Absolute paths (`/opt/data/home/memory/`) — most specific, no tilde ambiguity
2. Tilde-with-CWD (`~/./memory/`) — more specific than plain tilde
3. Plain tilde (`~/memory/`) — least specific, catches remaining matches

Test ordering with a dry run: `grep -r '~/memory/' ... | head -3` to confirm patterns match expectations.

**Step 4 — Service/index reconfiguration:** If any service indexes the moved directory, update its collection path and re-index:
- **QMD:** Remove old collection → add new collection → update → embed
- **Any other search/cache service:** Same pattern — update root, re-index, verify doc count matches expected

**Step 5 — Cron prompt sync:** The cron scheduler has its own in-memory copy of job prompts that is NOT automatically synced from `jobs.json`. After updating `jobs.json` via sed/replace, push each affected prompt to the live scheduler:
```python
# For each affected job, read the updated prompt from jobs.json and call cronjob update
for job_id in affected_job_ids:
    cronjob(action='update', job_id=job_id, prompt=updated_prompt)
```
**Common mistake:** Updating `jobs.json` only and assuming cron workers will see the new paths. They won't — the scheduler reads from its in-memory store, not the JSON file.

**Step 6 — Verification sweep:** After ALL replacements and service reconfigs:
- Grep for ALL old path variants — zero matches expected across all skill, memory, config, and cron files
- Test the hardlink: same inode, expected link count
- Test the DB (if one was moved): `sqlite3 /new/path/life/life-tracking.db "SELECT COUNT(*) FROM sqlite_master;"` — should return expected table count
- Verify the service index is re-built with expected doc count

**Step 7 — Fallback cleanup:** Only after full verification passes, optionally clean up the old source:
```bash
# Keep as backup initially; remove after user confirms all-clear
rm -rf /old/path
```

### 8a — Categorize Findings

Group every match into one of these types — they have different fix methods and different risk profiles:

| Type | Examples | Fix Method | Risk |
|------|----------|-----------|------|
| **Executables** | `.sh`, `.py`, `.js` files | Shell script: use `$HERMES_HOME` variable. Python/JS: use `os.environ['HERMES_HOME']` or `process.env.HERMES_HOME` | High — a typo here breaks runtime |
| **Skill docs** | `SKILL.md`, `references/*.md` | Use `$HERMES_HOME/...` or `$HERMES_HOME/...` in prose and code examples | Low — documentation only |
| **Memory docs** | `/opt/data/memory/*.md` | Same as skill docs | Low |
| **Cron prompts** | Cron job `prompt` field | Edit via `cronjob update` — prompts act as agent instructions | Medium — wrong path in a prompt sends agent down wrong path |
| **Symlink itself** | Filesystem entry | `unlink <path>` | None — only if all dependents are already migrated |

### 8b — Fix Executables First

These are the ones that can actually break at runtime. Fix them before touching docs:

```bash
# Batch 1: Shell scripts — replace hardcoded path with $HERMES_HOME
# Use patch with unique context strings to avoid ambiguity
patch /opt/data/scripts/wa-watchdog.sh \
  'SCRIPT_DIR="/opt/data/scripts/whatsapp-poll"' \
  'SCRIPT_DIR="$HERMES_HOME/scripts/whatsapp-poll"'
```

**Key rules:**
- In `.sh` files, use `$HERMES_HOME` (shell variable expansion)
- Quote the variable: `"$HERMES_HOME/scripts/foo.py"` — unquoted breaks on paths with spaces
- In `.py` files, use `os.environ['HERMES_HOME']` or `os.environ.get('HERMES_HOME', os.path.expanduser('~/.hermes'))`
- In `.js` files, use `process.env.HERMES_HOME`
- **Do NOT hardcode the resolved value** (`/opt/data`) — the whole point is using the env var

### 8c — Fix Skill & Memory Docs (Batch Operations)

For SKILL.md and reference files, use `patch` with `replace_all=true` for bulk operations:

```python
# Strategy: handle each distinct path pattern as a single replace_all patch
patterns = {
    'python3 /opt/data/scripts/garmin-connect.py': 'python3 $HERMES_HOME/scripts/garmin-connect.py',
    '/opt/data/scripts/garmin-daily-snapshot.py': '$HERMES_HOME/scripts/garmin-daily-snapshot.py',
    '/opt/data/scripts/whatsapp-poll/': '$HERMES_HOME/scripts/whatsapp-poll/',
    '/opt/data/home/scripts/mail-inbox-since.py': '$HERMES_HOME/scripts/mail-inbox-since.py',
}
```

`replace_all=true` applies to every occurrence across one file in a single call — much faster than per-line patches.

**Watch out for non-unique matches:** `cp ~/scripts/foo.sh /opt/data/scripts/foo.sh` appears twice in agent-backup docs. Either provide more context or use `replace_all=true`.

### 8d — Verify After Every Batch

After fixing each category, run a sweep to confirm no remaining old-path references:

```bash
grep -rn '/opt/data/scripts/' ~/skills/ 2>/dev/null | grep -v 'scripts-consolidation-plan' | head -20
grep -rn '/opt/data/home/scripts/' /opt/data/memory/ ~/skills/ 2>/dev/null | head -20
grep -rn '~/scripts/' /opt/data/memory/ ~/skills/ 2>/dev/null | head -20
```

**Critical:** The old path will still appear in `scripts-consolidation-plan.md` (the plan doc itself) — exclude it with `grep -v`. Also exclude historical skill reference docs like `path-dependency-tracing.md` which intentionally lists old paths as search examples.

### 8e — Remove the Symlink

Only after ALL references have been updated:

```bash
unlink /opt/data/home/scripts   # remove the convenience symlink
```

Verify: `ls -la /opt/data/home/scripts` should show `No such file or directory`.

### 8f — Update Documentation That Described the Old State

There will always be a few files that explicitly document the symlink/hardcoded path pattern. These need prose updates:

- Executive-assistant SKILL.md — the `~/scripts` symlink reference in the path-context table
- Cron-environment.md — the symlink verification block (`ls -la ~/scripts`)
- Path-dependency-tracing.md Phase 7 — update the findings table status to ✅ Fixed

**Don't miss the `ls ~/scripts` and `readlink -f ~/scripts` verification commands** in cron-environment.md — they'll fail after symlink removal. Replace with `echo $HERMES_HOME` and `ls $HERMES_HOME/scripts/`.

### 8g — Final Verification

1. All `.sh`, `.py`, `.js` files in `$HERMES_HOME/scripts/` use `$HERMES_HOME` for self-references ✅
2. No skill or memory file has a backtick-wrapped `/opt/data/scripts/` reference (bare mentions in code examples are fine) ✅
3. The symlink is gone ✅
4. All docs that described the symlink now say "symlink removed — use `$HERMES_HOME/scripts/`" ✅

### 8h — Common Refactoring Patterns (from 12 May 2026 session)

| Original | Replacement | Tool | Occurrences |
|----------|------------|------|-------------|
| `python3 /opt/data/scripts/<script>.py` | `python3 $HERMES_HOME/scripts/<script>.py` | `patch replace_all` | ~30 across garmin skill files |
| `node /opt/data/scripts/whatsapp-poll/<file>.js` | `node $HERMES_HOME/scripts/whatsapp-poll/<file>.js` | `patch` | ~6 across whatsapp + heartbeat |
| `cd /opt/data/home/scripts` | `cd "$HERMES_HOME/scripts"` | `patch` | 1 (start-browser-proxy.sh) |
| `SCRIPT_DIR="/opt/data/scripts/..."` | `SCRIPT_DIR="$HERMES_HOME/scripts/..."` | `patch` | 1 (wa-watchdog.sh) |
| `~/./scripts/<script>.py` | `$HERMES_HOME/scripts/<script>.py` | `patch` | 1 (pending.md) |
| `/opt/data/home/scripts/mail-inbox-since.py` | `$HERMES_HOME/scripts/mail-inbox-since.py` | `patch replace_all` | 5 (microsoft-email SKILL.md) |
| `ls ~/scripts/` | `ls $HERMES_HOME/scripts/` | `patch` | 2 (brain-architecture-audit.md, cron-environment.md) |

### 8i — Pitfalls

- **Don't update "scripts-consolidation-plan.md"** — the plan doc itself documents what the old paths were. Exclude it from verification sweeps.
- **Don't update "path-dependency-tracing.md" search examples** — the Phase 2 `paths_to_search` list intentionally includes old paths as examples of what to search for. Only update the Phase 7 findings table status.
- **$HERMES_HOME in Python cron agents:** The cron scheduler injects `$HERMES_HOME` into the agent's environment, but Python's `os.environ['HERMES_HOME']` is reliable. For shell scripts launched by cron, the env var propagates from the Docker container → gateway → scheduler → subprocess. Verified working 12 May 2026.
- **Verify HERMES_HOME propagation before relying on it:** If a no_agent cron job fails after refactoring, the env var may not be set in that context. Test with a simple echo-first script. The canonical test: `/proc/1/environ | grep HERMES_HOME` should show the value. If it doesn't, the container-level env var was removed.
- **`diff -rq` for duplicate detection:** When two directories appear to have the same content, use `diff -rq dirA dirB` to find actual differences. If only metadata files differ (.bundled_manifest, .usage.json), they're duplicates. If SKILL.md files reference opposite paths, they're complementary.

---

## Common Pitfalls

### 🚩 Stopping after literal string search
The literal string `~/scripts` may not appear anywhere. You must also search for the resolved path (`/opt/data/scripts`) and the full home path (`/opt/data/home/scripts`). The symlink is an alias — references use its target, not the symlink itself.

### 🚩 Not checking Hermes source code
The cron jobs appear to work even when `~/.hermes/scripts/` doesn't exist — because `HERMES_HOME` overrides the default, and the scheduler resolves against `$HERMES_HOME/scripts/`. Always check the env var and the scheduler source to understand actual resolution.

### 🚩 Not checking cron job prompts
Agent-based cron jobs (not no_agent) use a `prompt` field that may reference script paths. The prompt runs as the LLM instruction and may contain path references that need updating. List all jobs and grep through prompts.

### 🚩 Confusing `HERMES_HOME` default vs actual value
Default: `~/.hermes`. Actual on this system: `/opt/data` (set via env var). Scripts go in `$HERMES_HOME/scripts/` which is `/opt/data/scripts/`, not `~/.hermes/scripts/`. Always print the actual `HERMES_HOME` value.

---

## When to Run

| Scenario | Run It? |
|----------|---------|
| User asks "find all references to X path" | ✅ Yes — full sweep |
| Before removing or relocating a symlink | ✅ Yes — find all dependents |
| Before standardizing a path convention | ✅ Yes — establish baseline |
| After finding one reference, looking for more | ✅ Yes — don't assume phase 1 is exhaustive |
| Routine daily work | ❌ No — only on explicit trace requests |
