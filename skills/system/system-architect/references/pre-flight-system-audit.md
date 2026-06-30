# Pre-Flight System Audit

> **Purpose:** Verify system integrity — QMD index health, cron skill validation, no_agent script paths.
> **Run this BEFORE any structural change.** Ensures the baseline you're building on is accurate.
> **Run this as a standalone diagnostic** when the user asks about system health, equilibrium, or integrity checks.
> **First used:** 11 May 2026 — discovered broken `wa-watchdog` cron due to script path mismatch.

---

## What This Catches

- A file documented in system-architecture.md §3.7 doesn't exist on disk
- A cron job references a skill name that doesn't exist (broken load)
- A no_agent cron references a script at the wrong path (silent failure)
- Skills list count mismatch (duplication or loss)
- Signal rules files missing or stale

---

## Audit Procedure

Run these checks in order. Each is independent — a fail in one doesn't block the others.

### Check 1 — QMD Index Health

**Goal:** Verify QMD has indexed all memory tree files. Query the memory-tree collection count and compare against disk.

```terminal
podman exec qmd qmd ls memory-tree | wc -l
```

Then check disk:

```python
import os
root = '/opt/data/memory/'  # canonical path (no expanduser)
files_on_disk = set()
for dirpath, dirnames, filenames in os.walk(root):
    for f in filenames:
        rel = os.path.relpath(os.path.join(dirpath, f), root)
        if f == 'life-tracking.db' or f.endswith('.md'):
            files_on_disk.add(rel)

print(f"Files on disk: {len(files_on_disk)}")
print(f"Compare against QMD `qmd ls memory-tree` output.")
print("If counts differ significantly, re-index with: podman exec qmd qmd embed")
```

### Check 2 — Cron Job Skill References

**Goal:** Every skill name in every cron job's `skills` array resolves to an actual skill.

```python
import json, os, subprocess

# Get cron jobs
with open('/opt/data/cron/jobs.json') as f:
    data = json.load(f)

jobs = data.get('jobs', [])

# Get all skill names from the skills system
result = subprocess.run(
    ['python3', '-c', '''
import json, sys
# Load skill index
idx_path = "/opt/data/skills/index.json"
try:
    with open(idx_path) as f:
        idx = json.load(f)
except FileNotFoundError:
    # Fallback: list SKILL.md files
    import os
    skills = set()
    for root, dirs, files in os.walk("/opt/data/skills"):
        if "SKILL.md" in files:
            # skill name = directory name under skills/
            rel = os.path.relpath(root, "/opt/data/skills")
            skills.add(rel)
    print(json.dumps(sorted(skills)))
    sys.exit(0)
print(json.dumps(sorted(idx.keys())))
'''],
    capture_output=True, text=True
)
all_skills = set(json.loads(result.stdout.strip()))

for job in jobs:
    name = job.get('name', 'unnamed')
    skills = job.get('skills', [])
    for s in skills:
        if s not in all_skills:
            # Try qualified name (category/name)
            if '/' in s:
                print(f"  ✗ {name}: skill '{s}' not found (qualified name)")
            else:
                print(f"  ✗ {name}: skill '{s}' not found")
```

### Check 3 — no_agent Cron Script Paths

**Goal:** Every no_agent cron job's script exists at the expected `<HERMES_HOME>/scripts/` path.

```python
import json, os

hermes_home = '/opt/data'

with open('/opt/data/cron/jobs.json') as f:
    data = json.load(f)

jobs = data.get('jobs', [])
issues = []

for job in jobs:
    if job.get('no_agent') and job.get('script'):
        script_name = job['script']
        expected_path = os.path.join(hermes_home, 'scripts', script_name)
        if os.path.exists(expected_path):
            print(f"  ✅ {job['name']}: {expected_path}")
        else:
            # Search for it in subdirectories
            found = False
            for root, dirs, files in os.walk(os.path.join(hermes_home, 'scripts')):
                if script_name in files:
                    actual = os.path.join(root, script_name)
                    print(f"  ⚠️ {job['name']}: script exists at {actual}")
                    print(f"     Expected at {expected_path}")
                    print(f"     Fix: ln -s {actual} {expected_path}")
                    found = True
                    break
            if not found:
                print(f"  ❌ {job['name']}: script '{script_name}' NOT FOUND anywhere under scripts/")
```

### Check 4 — Signal Rules Files

Quick sanity check that the signal rules files exist and aren't empty:

```python
import os
for f in ['life/whatsapp-signal-rules.md', 'life/email-signal-rules.md']:
    path = f'/opt/data/memory/{f}'
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"  ✅ {f} ({size} bytes)")
    else:
        print(f"  ❌ {f} MISSING")
```

---

## Quick One-Shot

For a fast audit without stepping through each check, bundle everything into a single Python script:

```python
import os, json, re, subprocess

root = '/opt/data/memory/'  # canonical path (no expanduser — $VAR not expanded by expanduser)
hermes_home = '/opt/data'
issues = []

# --- Check 1: QMD Index Health ---
files_on_disk = set()
for dirpath, dirnames, filenames in os.walk(root):
    for f in filenames:
        rel = os.path.relpath(os.path.join(dirpath, f), root)
        if f == 'life-tracking.db' or f.endswith('.md'):
            files_on_disk.add(rel)

print(f"Files on disk: {len(files_on_disk)}")
print("Manual verification: run 'podman exec qmd qmd ls memory-tree | wc -l' and compare.")

# --- Check 2: Cron skills ---
with open('/opt/data/cron/jobs.json') as f:
    jobs = json.load(f).get('jobs', [])
r = subprocess.run(['python3', '-c', '''
import json, os; skills = set()
for r,d,f in os.walk("/opt/data/skills"):
    if "SKILL.md" in f: skills.add(os.path.relpath(r, "/opt/data/skills"))
print(json.dumps(sorted(skills)))
'''], capture_output=True, text=True)
all_skills = set(json.loads(r.stdout.strip()))
for job in jobs:
    for s in job.get('skills', []):
        if s not in all_skills and '/' not in s:
            issues.append(f"Cron '{job['name']}' references unknown skill: {s}")

# --- Check 3: no_agent scripts ---
for job in jobs:
    if job.get('no_agent') and job.get('script'):
        sn = job['script']
        ep = os.path.join(hermes_home, 'scripts', sn)
        if not os.path.exists(ep):
            found = False
            for r2,d2,f2 in os.walk(os.path.join(hermes_home, 'scripts')):
                if sn in f2:
                    issues.append(f"Cron '{job['name']}': script at wrong path ({os.path.join(r2,sn)})")
                    found = True; break
            if not found:
                issues.append(f"Cron '{job['name']}': script '{sn}' not found")

# --- Report ---
if issues:
    print(f"🔴 {len(issues)} issue(s) found:")
    for i in issues:
        print(f"  • {i}")
else:
    print("✅ System audit clean — no issues found.")
```

---

## When to Run

| Scenario | Run It? |
|----------|---------|
| Before making a structural change | ✅ Yes — ensure baseline accuracy |
| User asks "check system health" | ✅ Yes — this is the first diagnostic |
| After restoring from backup | ✅ Yes — verify integrity |
| Weekly meta-review | ✅ Recommended — catches drift early |
| Routine daily work | ❌ No — only when structural context needed |

---

## See Also

- **`references/path-dependency-tracing.md`** — for deep investigation into a specific path, symlink, or directory. Use when the pre-flight audit finds a path issue and you need to trace all references across the full system before fixing them.
