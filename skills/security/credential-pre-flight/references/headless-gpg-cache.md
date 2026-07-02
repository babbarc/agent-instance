# Headless GPG Cache — Cron / Background Failure Pattern

## Symptom

`pass` commands hang or return nothing in cron jobs / no_agent scripts / background processes, but work fine in interactive terminals.

Example: repeated errors like `ERROR: Could not find Garmin login email in pass` from a script that uses `pass show` internally, where the same command succeeds when run manually.

## Root Cause

GPG agent requires the key passphrase to decrypt. Default cache TTLs:

| Setting | Default | Meaning |
|---------|---------|---------|
| `default-cache-ttl` | 600 (10 min) | How long the passphrase stays cached after last use |
| `max-cache-ttl` | 7200 (2 hours) | Hard max the passphrase stays cached regardless of use |

When a headless process runs after the cache has expired, `gpg-agent` has no tty to prompt — it blocks or fails silently, causing `pass` commands to time out.

## Diagnostic Steps

1. Check current GPG agent config:
   ```bash
   cat ~/.gnupg/gpg-agent.conf 2>/dev/null || echo "NO CONFIG"
   ```

2. Check if key is cached — `C` = cached, `-` = not:
   ```bash
   gpg-connect-agent 'keyinfo --list' /bye 2>&1
   ```

3. Inspect the failing cron job's schedule vs last GPG use — if the gap exceeds `max-cache-ttl`, the cache is the cause.

## Permanent Fix

Create or update `~/.gnupg/gpg-agent.conf`:
```
default-cache-ttl 86400
max-cache-ttl 86400
```
Reload: `gpg-connect-agent reloadagent /bye`

This keeps the passphrase cached for 24h — covers any daily cron window.

## Short-Term Warm-up

```bash
PASSWORD_STORE_GPG_OPTS="--no-tty --batch --quiet" pass show <service>/<path> 2>&1 | head -1 | wc -c
```
Then immediately retry the actual `pass-to` command — cache is now warm.

## Edge Cases

- **Systemd user services / Docker** may have their own GPG agent scope. Test inside the actual execution context.
- **After reboot,** cache is always cold. First manual GPG use of the day re-warms it.
- **`no_agent` cron jobs** source their own shell — ensure `GPG_TTY` / `GPG_AGENT_INFO` aren't stale.
