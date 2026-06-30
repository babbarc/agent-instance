# Approval Regex Pitfalls

## `\\/` trap — matches literal `\/`, not plain `/`
In Python `r'...'`, `\\\\/` matches `\/` (backslash + slash), not `/`. Use just `/` or `\\/`.

## `\b` word boundary → 0x08 (backspace) corruption
`\b` in `r'...\b...'` must be bytes `0x5C 0x62`. If corrupted to `0x08`, regex compiles but silently never matches.
**Prevention:** Always use Hermes `patch` tool to edit — never Python strings, heredocs, or `write_file` with `\b`.

Detection:
```
python3 -c "c=open('/opt/hermes/tools/approval.py','rb').read(); assert b'\x08' not in c"
```

## `\b` before CLI flag dash never matches
`\b` before `-d`, `--send`, etc. can never fire — space (before flag) and `-` are both `\W`. No word boundary exists.
**Fix:** Drop the leading `\b`. Use flag directly: `-d\s+\bPRINTER\b` not `\b-d\b.*\bPRINTER\b`.

## Common approval patterns (Gmail / Outlook / WhatsApp / Print)

```
(r'python[23]?.*/google_api\.py\b.*\bgmail (send|reply)\b', "description")
(r'python3.*mail_api\.py\b.*\b(send|reply)\b', "description")
(r'node.*(?:baileys\.js\b.*--send|whatsapp-send(?:-image)?\.js)\b', "description")
(r'\blp\b.*-d\s+\bET-2750\b', "description")
```

Always test the compiled regex against a real command string before deploying:
```
python3 -c "import re; assert re.search(r'<pattern>', '<actual-command>')"
```
