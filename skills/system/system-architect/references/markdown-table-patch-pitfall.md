# Patch Tool Pitfall — Pipe & Bullet Consumption

> Documented: 11 May 2026 | Updated: 14 May 2026
> Source: `patch` on `system-architecture.md` category breakdown table consumed leading pipes. Later observed consuming pipes into **bullet lists** too.

## The Problem

When `patch(old_string, new_string)` touches a markdown table **or** bullet list row, the tool's fuzzy matching can consume trailing or leading `|` pipe characters from **adjacent** rows. This silently corrupts both tables and bullet lists.

**How it happens:**

You have a table like:
```
|| devops | 6 | ... |
|| github | 6 | ... |
|| health | 6 | ... |
```

You patch to insert a new row between `health` and the next row. The patch matches `|| health | 6 | ... |\n|| next-row | ...` but the fuzzy match algorithm includes the trailing `|` from the line before `health` and the leading `|` from the line after, consuming them. Result:

```
|| devops | 6 | ... |     ← still correct (wasn't in patch range)
| github | 6 | ... |       ← lost leading pipe (was adjacent to health)
| health | 6 | ... |       ← lost leading pipe (was the match target)
```

## The Same Bug Affects Bullet Lists

When `patch` touches a bullet list item (a `- ` line), the same fuzzy matching can consume a leading `|` from an adjacent line, producing `|- ` instead of `- `. This happened **multiple times** in the 14 May 2026 session.

**How it looks:**

```diff
-# Before: clean bullet list
+|- After: stray pipe consumed from adjacent line
```

**Where it hits:** Any bullet list near pipe characters — most commonly:
- Vertical bar in the editor gutter
- Vertical bar in adjacent lines within the same patch scope
- List items in `.hermes.md` (which has `|---` separators)
- List items in `SKILL.md` files

**Fix:** Same as table fix — patch again with the extra `|` removed:

```
old_string: "|- Your bullet text"
new_string: "- Your bullet text"
```

## Diagnosis

Use `execute_code` to read raw bytes — `read_file`'s display is unreliable because it renders formatting:

```python
with open('/path/to/file.md') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if line.startswith('|') or line.startswith('-'):
        print(f"L{i+1}: {repr(line.rstrip())}")
```

Look for:
- **Tables:** A row starting with `|` (single pipe) instead of `||` (double pipe) has been corrupted. A row starting with `|||` (triple pipe) was concatenated with an adjacent row.
- **Bullets:** A line starting with `|- ` instead of `- ` has a stray pipe.

## Fix Strategy

### Minimal fix (1-2 affected rows)
Patch just the broken rows:
```
old_string: "| github | 6 | ..."
new_string: "|| github | 6 | ..."
```

### Bulk fix (5+ adjacent rows affected)
Read the affected block, fix all at once in a single patch:

1. `execute_code` to get exact line content for 10-15 lines around the corruption
2. Build a `patch` old_string covering **all** the broken rows plus the first good row after them
3. Replace with corrected `||` prefixes

Example:
```python
old_string = """| devops | 6 | ...
| github | 6 | ...
| health | 6 | ...
|| architecture | 1 | ..."""
new_string = """|| devops | 6 | ...
|| github | 6 | ...
|| health | 6 | ...
|| architecture | 1 | ..."""
```

**Key insight:** Include the first correctly-formatted row after the broken block in your old_string — this pins the replacement boundary and prevents the patch from consuming more pipes.

## Prevention

- After every `patch` that touches a markdown table, verify ALL rows in that table (not just the ones you changed). Pipes can domino.
- Read the file with `execute_code` (raw repr) not `read_file` (rendered output).
- If you're inserting a row into the middle of a table, consider whether a single `patch` of the entire table block (from header to last row) is safer than targeted row replacement.
