# Custom s6 Services — replacing cron watchdogs (June 2026)

## Context

Two watchdog crons were replaced with s6 `longrun` services:

| Old cron | Schedule | Script | New s6 service |
|---|---|---|---|
| Vision Bridge Watchdog | every 3h | `vision-bridge-watchdog.sh` | `vision-bridge` |
| wa-watchdog | every 15m | `wa-watchdog.sh` | `baileys-watch` |

## Why swap cron → s6

- Cron polls on a timer (3h / 15m). s6 provides instant restart-on-crash.
- The old watchdogs checked application-level liveness (HTTP /health endpoint, deltas.ndjson freshness). These were workarounds for cron's polling latency — the processes themselves correctly exit on all unrecoverable errors, so PID-level s6 supervision is sufficient.
- s6 is zero-config for this use case: `longrun` type + user bundle registration = auto-start at boot, auto-restart on crash.

## The two bridges

### Vision Bridge

`/opt/data/scripts/vision-bridge.py` — Python HTTP server on `127.0.0.1:9877`

- OpenAI-compatible endpoint for image analysis
- Tries Claude Code CLI first, falls back to Gemini API
- Gemini API key loaded via `pass show pallav/gemini.key`
- Has a built-in `/health` endpoint returning `{"status": "ok"}`
- All stdlib dependencies — no venv activation needed

### Baileys Watch

`/opt/data/scripts/whatsapp-poll/baileys-watch.js` — Node.js WebSocket client

- Uses `@whiskeysockets/baileys` for WhatsApp Web connection
- Writes to `~/.hermes/platforms/whatsapp/deltas.ndjson`
- Heartbeat every 30s written to deltas.ndjson
- Auto-reconnects on disconnect with exponential backoff (2s → 60s)
- Exits with `process.exit(1)` on logout or session not found
- Node modules at `/opt/data/scripts/whatsapp-poll/node_modules/`
- Does NOT use `pass` — only the vision bridge needs it

## Pass store setup

- Store location: `/opt/data/home/.password-store/` owned by hermes:hermes
- GPG key at `/opt/data/home/.password-store/.gpg-id`
- The vision bridge runs `pass show pallav/gemini.key` to get GEMINI_API_KEY
- `pass` resolves via `$HOME/.password-store` — no `PASSWORD_STORE_DIR` env var set
- In s6 run scripts: `export HOME=/opt/data/home` makes `~/.password-store` resolve correctly

## Deployment

All changes go in the `hermes-agent` repo:

- `Containerfile.hermes` — s6 service setup (COPY run, chmod, type, register in bundle)
- `vision-bridge-run.sh` — s6 run script in repo root
- `baileys-watch-run.sh` — s6 run script in repo root

Push to `alps:babbarc/hermes-agent.git`. User rebuilds and restarts the container.

## Verification

After rebuild and restart:

```bash
# Check services are up
ls /etc/s6-overlay/s6-rc.d/user/contents.d/
# Should list: vision-bridge, baileys-watch, cupsd, dashboard, main-hermes

# Check process status
s6-svstat /run/s6/db/servicedirs/vision-bridge/ 2>/dev/null || \
  s6-svstat /run/service/vision-bridge/ 2>/dev/null

s6-svstat /run/s6/db/servicedirs/baileys-watch/ 2>/dev/null || \
  s6-svstat /run/service/baileys-watch/ 2>/dev/null

# Vision bridge health check
curl http://127.0.0.1:9877/health

# WA bridge check
cat /opt/data/home/.hermes/platforms/whatsapp/deltas.ndjson | tail -5
```

## Notes

- The old watchdog crons can stay registered — they fire harmlessly since s6 already manages the process. Remove them after confirming the s6 services work.
- The dashboard service uses `export HOME=/opt/data` (not `/opt/data/home`). That's because the dashboard doesn't use `pass`. Bridges that need the password store must use `/opt/data/home`.
