# Bash String Safety

## Vulnerability 1 — Apostrophes in Single-Quoted Strings
```bash
python3 life-track.py signal add daily_pulse briefing delivered '<summary>'
# If summary = "Pallav's briefing" → bash string closes at apostrophe
```
**Fix:** Paraphrase around apostrophes. Forbid them in summaries.

## Vulnerability 2 — Special Chars in Double-Quoted Strings
```bash
python3 life-track.py signal add daily_pulse briefing \
  delivered "<goal_note> | <kanban_note>"
# $ → variable expansion, ` → command substitution, " → terminates string
```
**Fix:** Use single quotes and forbid apostrophes in summaries.

## Combined Safe Pattern
```bash
# Safe — single-quoted, with apostrophe-restriction rule:
python3 /opt/data/scripts/life-track.py signal add <domain> <metric> <value> '<summary>'
```

**Prompt rule to add:** "Use single quotes in bash commands. Do NOT include apostrophes or special characters ($, `, \") inside summary text."
