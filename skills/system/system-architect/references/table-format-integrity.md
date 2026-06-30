# Table Format Integrity — Detection & Rebuild

> **Purpose:** Detect and fix a specific corruption mode in the drift anchor's markdown tables, where category names get silently replaced by line numbers due to the patch tool's pipe-consumption bug.
> **Trigger:** Use during equilibrium check step 11a (Table format integrity) when surveying the anchor's skills taxonomy table (§3.6) or any other markdown table that was repeatedly patched.

## The Corruption Mode

The `patch` tool's fuzzy matching can consume pipe characters from adjacent rows. Over multiple patch operations on the same table, the first column's content degrades:

```
✅ Correct:
| Category | Key Skills |
|----------|------------|
| software-development | plan, tdd, ... |
| productivity | google-workspace, ... |

❌ Corrupted (line numbers replace names):
| Category | Key Skills |
|----------|------------|
| 299 | plan, tdd, ... |
| 300 | google-workspace, ... |
```

The numbers (299, 300, 301...) are the **original line numbers** from when the table was first created — they were never meant to be table content. Each patch consumed a pipe character, pushing the line number into the cell.

## Detection

### Spot-check (quick)

Read lines ~284-325 of `system-architecture.md`. Do the first column entries look like category names (`software-development`, `productivity`, `research`) or like bare numbers (`299`, `300`, `301`)?

If numbers: **corrupted. Do NOT patch.** See rebuild procedure below.

### Deterministic check (use this)

```python
import re

with open('/opt/data/memory/architecture/system-architecture.md') as f:
    lines = f.readlines()

# Find the skills taxonomy table (between "Category breakdown:" and "Management:")
in_table = False
for i, line in enumerate(lines):
    stripped = line.strip()
    if 'Category breakdown' in stripped:
        in_table = True
        continue
    if '**Management:**' in stripped:
        in_table = False
        continue
    if in_table and stripped.startswith('|') and not stripped.startswith('|--') and not stripped.startswith('| Category'):
        # Extract first column
        cols = stripped.split('|')
        if len(cols) >= 2:
            first_col = cols[1].strip()
            if re.match(r'^\d+$', first_col):
                print(f'CORRUPTED: line {i+1} has "{first_col}" instead of category name')
```

Run this in `execute_code`. If it prints any lines, the table is degraded.

## HOW NOT TO REBUILD

**Do NOT use `patch`** on the table — fuzzy matching is what caused the corruption in the first place. Patching a corrupted table embedded in a large file is how it got worse iteratively.

## Rebuild Procedure

1. **Read the full file** — `read_file` the entire system-architecture.md. Store the content as a Python variable.

2. **Query the live filesystem for the correct taxonomy:**

```python
import os, subprocess

sk_dir = '/opt/data/skills'
categories = []
for d in sorted(os.listdir(sk_dir)):
    dp = os.path.join(sk_dir, d)
    if os.path.isdir(dp) and not d.startswith('.'):
        skills = sorted([s for s in os.listdir(dp) if os.path.isdir(os.path.join(dp, s))])
        if skills:
            categories.append((d, ', '.join(skills)))
```

3. **Build the correct table string** using `write_file` (full replacement of the file):

```python
# Build just the table portion
table_lines = '| Category | Key Skills |\n|----------|------------|\n'
for cat, skills in categories:
    table_lines += f'| {cat} | {skills} |\n'
```

4. **Split the file on the old corrupted table** and join with the new one:

```python
before = full_content[:table_start]
after = full_content[table_end:]
new_content = before + table_lines + after
with open('/opt/data/memory/architecture/system-architecture.md', 'w') as f:
    f.write(new_content)
```

5. **Verify** — Re-run the detection script. It should print nothing.

## Prevention

- **Treat the skills taxonomy table as a write_file-only zone.** Never patch individual rows inside it. If it needs updating, rebuild the entire table from the filesystem.
- The same applies to any markdown table in the drift anchor that spans 10+ rows. Patch is safe for single-row tables. Multi-row tables get write_file.
- Update the table definition (the `| Category | Key Skills |` header + `|----------|------------|` separator) in the reference below whenever a new skill category is created.
