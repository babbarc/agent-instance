# Brain Architecture Audit — Methodology

> A comprehensive, cross-layer health check of the entire Joy brain system. Goes deeper than the consistency audit (which checks doc-vs-reality alignment). This audit assesses **system health, design integrity, gaps, and deferred maintenance** across every layer.

## When to Run

- **Monthly** as part of the maintainer cycle
- **On suspicion of drift** (cron jobs failing, tasks getting lost, memory store filling up)
- **Before major system changes** (new profile creation, skill library overhaul)

## Dimensions to Check

### Dimension 1 — Memory Tree

**Do:** Walk the full tree, measure occupancy, verify tier integrity.

```python
import os, json
from pathlib import Path

mem_root = Path(os.path.expanduser("/opt/data/memory"))

# Full file listing
files = list(mem_root.rglob("*"))
print(f"Total files: {len(files)}")
for f in sorted(files):
    if f.is_file():
        rel = f.relative_to(mem_root)
        size = f.stat().st_size
        print(f"  {rel}  ({size:,} bytes)")
```

**What to check:**
- [ ] Tier 1 occupancy < 90% (entries + user store)
- [ ] All Tier 2 files exist (contacts/pallav-vasa.md, environment/profiles-crons.md)
- [ ] SOUL.md hardlink is intact (`stat -c "%i %h" /opt/data/SOUL.md $HERMES_HOME/memory/SOUL.md` — same inode, >= 2 links)
- [ ] Life tracking DB has tables (not empty schema)
- [ ] QMD index is not empty (check with `podman exec qmd qmd ls memory-tree | wc -l`)
- [ ] Memory evolution doc is accurate (doesn't claim patches are inactive when they're active, etc.)

### Dimension 2 — Skills Inventory

**Do:** Catalog all skills, check for phantom references, identify stale skills.

```python
import os
from pathlib import Path

skills_root = Path("/opt/data/skills")
skills = sorted(s.rstrip("/SKILL.md") for s in skills_root.rglob("SKILL.md"))
print(f"Total skills: {len(skills)}")

# Group by category
cats = {}
for s in skills:
    cat = s.relative_to(skills_root).parent.as_posix()
    cats.setdefault(cat, []).append(s.name)
for cat, names in sorted(cats.items()):
    print(f"  {cat}/ ({len(names)} skills)")
```

**Cross-reference against board config:** The `board-config.json` at `~/kanban/board-config.json` lists skills per specialist profile. Every skill listed there must exist.

```python
import json
board = json.loads(Path(os.path.expanduser("~/kanban/board-config.json")).read_text())
for specialist in board["specialists"]:
    for skill in specialist.get("skills", []):
        found = list(Path("/opt/data/skills").rglob(f"{skill}/SKILL.md"))
        status = "✅" if found else "❌ MISSING"
        print(f"  {status} {specialist['profile']}: {skill}")
```

**What to check:**
- [ ] No phantom skills (board config references skills that don't exist)
- [ ] No orphan skills (skills exist but no profile references them — may be OK for utility skills)
- [ ] Skill descriptions are accurate (spot-check 3-5 that were recently used)
- [ ] Skill versions are current (any with old architecture references)

### Dimension 3 — Cron Jobs

**Do:** List all cron jobs, check health, assess coverage.

```bash
cronjob(action='list')
```

**What to check:**
| Signal | Meaning |
|--------|---------|
| `last_status: error/failed` | Repeated failures mean broken cron |
| `last_run_at: null` | Never run — investigate if schedule has passed |
| `last_run_at` > 48h ago | Likely not running despite active schedule |
| Schedule overlap | Two jobs running at same time doing conflicting work |
| Missing `last_delivery_error` | Silent failures — cron job thinks it ran but delivered nothing |
| `enabled: false` | Deliberately paused — check if it should be re-enabled or removed |

**Delivery pattern check:**
- `telegram:8083437806` = delivers to the Home channel
- `origin` = delivers back to the creating chat
- Inconsistent delivery expected? Check if cron was created from different chats

### Dimension 4 — Kanban Board

**Do:** Check board config, task state, profile existence.

```bash
# Board config
cat ~/kanban/board-config.json | python3 -m json.tool | head -30

# Kanban DB task state
python3 -c "
import sqlite3
db = sqlite3.connect('/opt/data/kanban.db')
for row in db.execute(\"SELECT id, title, assignee, status, created_at FROM tasks ORDER BY created_at DESC LIMIT 20\"):
    print(f'  {row}')
db.close()
"

# Profile existence
ls /opt/data/profiles/
```

**What to check:**
- [ ] Board config → profiles directory: every specialist listed has a profile at `/opt/data/profiles/<name>/`
- [ ] Board config → skills: every skill listed for a specialist exists (cross-ref Dimension 2)
- [ ] Task flow: tasks progress from backlog → ready → in_progress → done (not stuck in one column)
- [ ] Blocked tasks: any blocked for >7 days needs investigation
- [ ] Empty board with configured profiles = dormant delegation system

### Dimension 5 — Infrastructure Health

**Do:** Check system resources, git state, credentials, scripts.

```bash
# Disk & memory
df -h / | tail -1
free -h | tail -2

# Git state
cd ~ && git status --short | head -20
git log --oneline -5
git remote -v

# GPG/pass
gpg --list-keys 2>/dev/null | head -10
pass ls 2>/dev/null | head -20

# Bin scripts
ls ~/bin/ 2>/dev/null
ls $HERMES_HOME/scripts/ 2>/dev/null

# Config
cat ~/.hermes/config.yaml
```

**What to check:**
- [ ] Disk free > 20%
- [ ] Memory free > 10%
- [ ] Git is clean (no staged but uncommitted changes) or changes are expected
- [ ] GPG key is valid (not expired)
- [ ] pass store has entries (not empty)
- [ ] Config is minimal (no secrets in plaintext)
- [ ] QMD daemon is running (`curl -s http://localhost:8181/health`)

### Dimension 6 — Patch State

**Do:** Verify all `.patch` files apply cleanly against the current upstream and no patch is silently stale.

```bash
# List all patches and originals
ls /opt/data/home/.hermes/patches/*.patch /opt/data/home/.hermes/patches/*.original 2>/dev/null

# Check cont-init script that applies patches at boot
cat /etc/cont-init.d/99-hermes-patches

# Dry-run each patch to verify it still applies cleanly
for f in /opt/data/home/.hermes/patches/*.patch; do
    name=$(basename "$f" .patch)
    if patch --dry-run -p0 -d /opt/hermes < "$f" 2>/dev/null; then
        echo "✅ $name — applies cleanly"
    else
        echo "❌ $name — FAILS dry-run (upstream changed patched area)"
    fi
done
```

**What to check:**
- [ ] All patches apply cleanly (dry-run passes)
- [ ] Each `.patch` has a corresponding `.original` (snapshot from last boot)
- [ ] `99-hermes-patches` cont-init script exists with correct shebang and loop covers all `.patch` files
- [ ] No stray full-copy files in patches dir (only `.patch` and `.original`)
- [ ] Diffs are minimal and targeted (check with `diff -u original patched`)

**Regenerating patches when upstream Hermes updates:**

When a Hermes update (new container image, pip upgrade) overwrites installed files, patches that fail dry-run must be regenerated:

1. Save the new upstream: `cp /opt/hermes/<relative-path>/<file> /tmp/<file>.new`
2. Copy the new upstream to a working copy: `cp /tmp/<file>.new /tmp/<file>.patched`
3. Apply your targeted changes to `/tmp/<file>.patched`
4. Generate the patch: `diff -u /tmp/<file>.new /tmp/<file>.patched > ~/.hermes/patches/<file>.patch`
5. Fix headers for `patch -p0` resolution:
   ```bash
   sed -i "1s|/tmp/<file>.new|<relative-path>/<file>|" ~/.hermes/patches/<file>.patch
   sed -i "2s|/tmp/<file>.patched|<relative-path>/<file>|" ~/.hermes/patches/<file>.patch
   ```
6. Verify dry-run: `patch --dry-run -p0 -d /opt/hermes < ~/.hermes/patches/<file>.patch`
7. Commit and restart — the `.original` will be refreshed at next boot

Never copy old patch files over new upstream — if the dry-run fails, the patch is silently skipped and the upstream version runs instead. That's the safe fallback, not a reason to force the old patch.

## Scoring

After all 6 dimensions, produce an overall health score and prioritied action list.

### Scoring Rubric

| Score | Meaning |
|-------|---------|
| 10-9 | All systems healthy. Minor cosmetic issues at most. |
| 8-7 | Design is sound, but implementation has gaps. Some deferred maintenance. |
| 6-5 | Structural issues. Multiple dimensions have medium-severity problems. |
| 4-0 | Critical systemic failures. Core operations are impaired. |

### Severity Classification

| Severity | Label | Response |
|----------|-------|----------|
| 🔴 Critical | Must fix now | Blocks operation or is actively losing data |
| 🟡 High | Should fix soon | Impacts reliability or efficiency |
| 🟢 Low | Nice to fix | Cosmetic, minor duplication, optional optimization |

### Report Template

```markdown
## Brain Architecture Audit — [Date]

### Overall Score: X/10

### Dimension Scores
| Dimension | Score | Key Finding |
|-----------|-------|-------------|
| Memory Tree | N/10 | ... |
| Skills | N/10 | ... |
| Cron Jobs | N/10 | ... |
| Kanban | N/10 | ... |
| Infrastructure | N/10 | ... |
| Patches | N/10 | ... |

### 🔴 Critical
1. Issue — why it matters

### 🟡 High
1. Issue — why it matters

### 🟢 Low
1. Issue — why it matters
```

## Pitfalls & Workarounds

- **`sqlite3` CLI binary may not be installed.** Use `python3 -c "import sqlite3; ..."` instead. Python's sqlite3 module is always available on Python 3.13+.
- **`file` command may not be available** in bare containers. Use Python for content inspection instead.
- **`sudo` not available** — container runs as non-root. Can't chown/chmod files owned by UID 10000 or write to `/opt/hermes/`. The `99-hermes-patches` cont-init script runs as root at boot and applies patches to the install dir. Patch verification and regeneration must be done from the patch file on the persistent volume — actual application only happens on restart.
- **`hermes --version` not available** — can't check Hermes version via CLI. Check `/opt/hermes/VERSION` or equivalent if it exists.
- **Patches skip on conflict, not silently downgrade.** When upstream Hermes updates (new container image), `99-hermes-patches` runs `patch --dry-run` first. If the patch doesn't apply cleanly, it's skipped and the upstream version runs unmodified — a warning goes to stderr, no silent degradation. Check with `for f in ~/.hermes/patches/*.patch; do patch --dry-run -p0 -d /opt/hermes < "$f" 2>/dev/null || echo "FAILS: $f"; done`.
- **Life tracking DB may have a richer schema than documented** — previous sessions or subagents may have added extra tables (relationship_recency, goal_tracking, intervention_log). Don't assume the schema is empty or minimal.
- **Kanban DB at `/opt/data/kanban.db`**, not `~/kanban/kanban.db`. The kanban-orchestrator skill hardcodes the `/opt/data/` path.
