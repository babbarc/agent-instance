# Heartbeat Cursor Migration

June 2026 — WhatsApp cursor moved from internal watermark to stateless `--since` filtering.
Unified cursor at `/opt/data/.cache/heartbeat-last-ok`, managed by `heartbeat-data.sh`.
Script renamed from `whatsapp-feed.py` → `whatsapp_delta.py` to match `gmail_delta.py` naming.
Cursor advances only when previous heartbeat run `last_status == "ok"` — no LLM involvement.

Old files deleted:
- /opt/data/scripts/whatsapp-feed.py
- /opt/data/tmp/heartbeat-email-cursor
- /opt/data/.cache/whatsapp-last-ts.txt

13 doc references renamed across skills. cron-rules pitfall 16 marked RESOLVED.
