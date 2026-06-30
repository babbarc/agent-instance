# Pipeline Failure Isolation in Data-Collection Scripts

When a data-collection script pipes multiple commands together, generic `||` fallback masks root cause.

## The Fix — Two Approaches

### Approach A — Isolate pipe segments (preferred)
```bash
# Step 1: Fetch raw data
RAW=$(python3 gmail_delta.py --since 2h 2>&1) \
  || { echo '{"status":"error","message":"gmail_delta failed"}'; exit 1; }
# Step 2: Enrich (optional — fail open with raw data)
echo "$RAW" | python3 resolve-email-senders.py \
  || echo '{"status":"warn","message":"resolve failed, using raw","data":'$RAW'}'
```

### Approach B — PIPESTATUS (lightweight, no pipe restructure)
```bash
python3 gmail_delta.py --since 2h | python3 resolve-email-senders.py
RC_GMAIL=${PIPESTATUS[0]}
RC_RESOLVE=${PIPESTATUS[1]}
```

## When to Use Which

| Scenario | Approach |
|----------|----------|
| Downstream is enrichment (skip-able) | A — fail open: deliver raw |
| Downstream is a filter (data depends on it) | A — fail closed: report specific failure |
| Minimum code change | B — PIPESTATUS gives segment-level diagnostics |
| Script has `set -eo pipefail` | A only — pipefail kills pipe before PIPESTATUS is useful |

## Diagnostic Pattern
```bash
python3 gmail_delta.py > /tmp/raw.json && echo "gmail_delta OK"
python3 resolve-email-senders.py < /tmp/raw.json > /tmp/enriched.json && echo "resolve OK"
```
Compare exit codes to find the broken link.
