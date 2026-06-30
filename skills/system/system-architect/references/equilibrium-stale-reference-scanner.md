# Equilibrium Stale-Reference Scanner

> Systematic search patterns for finding stale references after a drift fix.
> Use this during the equilibrium check's Second-pass stale-reference scan (step 11).

## When to Run This

After updating any of these in the drift anchor:
- Cron schedules (time changes)
- DB row counts (life_signals, intervention_log, Kanban tables)
- Skill counts
- Profile counts
- Memory tree structure (files added/removed)
- Cron job names or status (paused, removed, added)

The drift anchor is ONE file. The same data lives in profiles-crons.md and N skills.

## Search Strategy

### Step A: List what changed

From your drift list, extract the **OLD values** you replaced. Example:
- "7am BST" → "6am BST" → old = `7am`
- "16 rows" → "59 rows" → old = `16` (but narrow by context: `life_signals.*16`)
- "Removed" → "active" → old = `Removed`
- "138 skills" → "147 skills" → old = `138`

### Step B: Search by old value files

Search profiles-crons.md FIRST — it almost always stale too.

### Step C: Search all SKILL.md files

Use `search_files` with the old value strings. Run multiple searches per drift type.

## Search Patterns by Drift Type

### Cron Schedule Changes

When you shift cron schedules, search for the **OLD schedule times**:

Pattern: `daily [0-9]am BST` or `Sun [0-9]pm BST` or `[0-9]/[0-9]/[0-9]+ BST`

Common stale strings that show up in skills after a schedule fix:
```
"7am"        → morning-briefing, fitness-coach-morning
"9pm"        → fitness-coach-evening
"8pm"        → fitness-coach-weekly
"9am"        → hermes-maintainer, garmin-snapshot, life-admin-radar
"12pm"       → doc-sync-watchdog
"10am"       → life-admin-radar
"6/12/18"    → purchase scans (often with "UTC" not "BST")
"06-22"      → heartbeat watchdog range
"8am"        → rightmove-tracker (if it changed from 8am to 7am)
```

### DB Row Count Changes

Search for the OLD number in context of the table name:
```
"life_signals.*[0-9]+"      → find the row count in any skill/doc
"intervention_log.*[0-9]+"  → find the row count
"Main task records.*[0-9]+" → Kanban tasks count
```

### Skill Count Changes

Search by the old total number:
```
"138"    within 5 lines of "skills" or "Total:"
"139"    within 5 lines of "skills" or "Total:"
"141"    within 5 lines of "skills" or "Total:"
"31 categories"  (or whatever the old count was)
```

### Profile Count Changes

Search by old count:
```
"8 specialist profiles"
"8 profiles"
```

### Memory Tree Changes

When files are added/removed:
Search for `30 files` or whatever the old count was.
Also search for any files that were removed (their names may still be referenced).

### Table Format Integrity (New Drift Type)

The drift anchor's markdown tables can degrade when repeatedly patched — category names in the first column silently replaced by line numbers. This is NOT caught by value-based search. To detect:

```python
import re
with open('/opt/data/memory/architecture/system-architecture.md') as f:
    lines = f.readlines()
in_table = False
found = False
for i, line in enumerate(lines):
    s = line.strip()
    if 'Category breakdown' in s:
        in_table = True; continue
    if '**Management:**' in s:
        in_table = False; continue
    if in_table and s.startswith('|') and not s.startswith('|--') and 'Category' not in s:
        first = s.split('|')[1].strip()
        if re.match(r'^\d+$', first):
            print(f'CORRUPTED L{i+1}: "{first}" should be a category name')
            found = True
if not found:
    print('Skills taxonomy table: format OK')
```

**Search pattern:** Look for lines in the range ~284-325 of `system-architecture.md` where the first column is a bare number (299, 300, 301...) instead of a word.

**Fix:** Do NOT patch — rebuild the entire table from the filesystem. See `references/table-format-integrity.md`.

### Cron Job Status Changes

When a job is un-paused, revived from "Removed", or newly documented:

Search for the old status string:
```
"Removed"    within 5 lines of the job name
"Paused"     within 5 lines of the job name
"brain-sync" (old name for auto-sync)
```

## Step D: Check the Dual-Anchor Consistency

After fixing all references, verify that these two files ALL agree on the same numbers:

1. `system-architecture.md` (drift anchor)
2. `profiles-crons.md` (runtime reference)

Pick any 3 numbers (e.g. clock time for morning briefing, life_signals row count, skills total) and confirm the same value in both files. If they disagree, one file is still stale.

## Example: This Session's Scan Pattern

| Changed | Old Value | Search Pattern | Files Found Stale |
|---------|-----------|----------------|-------------------|
| Morning briefing | 7am BST | `7am` in SKILL.md | 3 skills |
| Fitness evening | 9pm BST | `9pm` in SKILL.md | 1 skill |
| Purchase scans | 6/12/18 UTC | `6/12/18` in SKILL.md | 1 skill |
| auto-sync | Removed | `Removed.*auto-sync\|Removed.*brain-sync` | profiles-crons.md |
| Skills total | 138/139/141 | `138.*skills\|139.*skills\|141.*skills` | profiles-crons.md |
| Profiles count | 8 | `8 specialist` | profiles-crons.md |
| Memory store chars | 1,747 | `1,747` | memory store |
| User store chars | 193 | `193 chars` | user store |
| Memory files | 30 | `30 files` | QMD collection |
