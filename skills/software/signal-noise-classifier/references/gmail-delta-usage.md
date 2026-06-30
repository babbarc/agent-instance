# gmail_delta.py — Tool Reference

Standardised Gmail delta detection for cron jobs (heartbeat, weekly scans, etc.).
Cross-references against `finance.db` to skip already-processed statements.
Lives at `/opt/data/scripts/gmail_delta.py`.

## Key Parameter Behaviour

### `--query` replaces the entire search, including the time filter

When you pass `--query`, the script passes your string **verbatim** to the Gmail API.
It does NOT append `newer_than:` or `after:` — even though the `--since` flag is
present, that flag only affects the JSON output's metadata label when no `--query`
is given.

**WRONG** (no time filter — scans ALL time, hangs or times out):
```
--query "(in:inbox AND (category:primary OR category:updates))"
```

**CORRECT** (time filter included in the query string):
```
--query "(in:inbox AND (category:primary OR category:updates)) newer_than:2h"
```

### Time filter format
- Relative: `newer_than:2h`, `newer_than:7d`, `newer_than:2w`
- Absolute: `after:2026/06/01`

When building a cron data-collection script that uses a dynamic cursor, construct
the time filter in the shell and interpolate it into the query string.

### Dedup scope
`gmail_delta.py` only cross-references `finance.db` → `statements.gmail_message_id`.
It does NOT check `inventory.db → purchase_emails` or any other DB. This means a
purchase email that was already routed to inventory-manager will be re-injected
into the LLM's context on every subsequent scan unless the LLM itself skips it.
Dedup for purchase emails happens downstream (inventory-manager checks
`purchase_emails.gmail_message_id` before inserting).

### Default query (when `--query` is omitted)
```
in:inbox -category:promotions -category:social {time_filter}
```
Catches Primary, Updates, and Forums categories. Excludes marketing and social noise.
