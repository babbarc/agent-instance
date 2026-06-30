# User-Context Services Under s6 Supervision

## When to Use This Pattern

A process currently launched and health-checked by a **cron watchdog** (checks
if alive, restarts if dead) that should instead be supervised by s6. The
process runs as the `hermes` user, needs user-level environment (PATH, node,
venv, pass secrets), and should be auto-started at boot and restarted on crash.

## Class Definition: User-Context vs System s6 Services

| Aspect | System Service (e.g. cupsd) | User-Context Service (e.g. bridge daemon) |
|--------|---------------------------|------------------------------------------|
| User | root | hermes (via `s6-setuidgid hermes`) |
| Environment | Container-level | Needs venv PATH, node, pass, etc. |
| Crash handling | s6 restarts | s6 restarts (replaces cron watchdog) |
| Health check | PID-level (s6-supervise) | PID-level (s6-supervise) |
| Prior mechanism | daemonize at boot | cron every N minutes: "is it alive? restart if not" |

## The Pattern

### Service Directory Layout (identical for both classes)

```
/etc/s6-overlay/s6-rc.d/<service-name>/
├── run              ← executable, #!/command/with-contenv sh
├── type             ← contains "longrun"
└── dependencies.d/  ← empty directory
```

### Bundle Registration

Create an empty file in the `user` bundle to auto-start at boot:

```
/etc/s6-overlay/s6-rc.d/user/contents.d/<service-name>  ← empty, 0 bytes
```

### Run Script Structure

The key difference from system services: privilege drop via `s6-setuidgid hermes`.

```sh
#!/command/with-contenv sh
# shellcheck shell=sh
# <service-name> — supervised daemon bridge
#
# Runs as hermes user. s6-supervise restarts on crash.
# Replaces: cron watchdog that checked /health endpoint / PID file.

# Drop to hermes user
exec s6-setuidgid hermes \
    /opt/hermes/.venv/bin/python3 /opt/data/scripts/vision-bridge.py
```

**Important:** Use absolute paths for interpreters and scripts. `with-contenv`
loads container-level environment variables but does NOT source the hermes
user's shell profile. The `hermes` user's `$HOME` is `/opt/data` — reference
paths relative to that.

## Worked Examples

### Example 1: Python HTTP Bridge (replaces curl health-check watchdog)

The vision bridge: a Python HTTP server on 127.0.0.1:9877 that was previously
restarted by a cron watchdog every 3 hours.

**`/etc/s6-overlay/s6-rc.d/vision-bridge/run`:**
```sh
#!/command/with-contenv sh
# Vision Bridge — OpenAI-compatible vision server on port 9877
exec s6-setuidgid hermes \
    /opt/hermes/.venv/bin/python3 /opt/data/scripts/vision-bridge.py
```

**`/etc/s6-overlay/s6-rc.d/vision-bridge/type`:**
```
longrun
```

**Bundle registration:**
```sh
touch /etc/s6-overlay/s6-rc.d/user/contents.d/vision-bridge
```

### Example 2: Node.js Persistent Connection (replaces PID-file watchdog)

The baileys WhatsApp bridge: a Node.js process that maintains a persistent
WhatsApp Web socket and writes deltas.ndjson. Was previously watched by a
cron every 15 minutes checking PID file + file freshness.

**`/etc/s6-overlay/s6-rc.d/wa-bridge/run`:**
```sh
#!/command/with-contenv sh
# Baileys WhatsApp Bridge — persistent WebSocket connection
exec s6-setuidgid hermes \
    /usr/bin/node /opt/data/scripts/whatsapp-poll/baileys-watch.js
```

**`/etc/s6-overlay/s6-rc.d/wa-bridge/type`:**
```
longrun
```

**Bundle registration:**
```sh
touch /etc/s6-overlay/s6-rc.d/user/contents.d/wa-bridge
```

## What Changes When You Migrate from Cron Watchdog to s6

### Removed
- The cron job entry (remove via cronjob tool)
- The watchdog shell script (the health-check/restart loop) — s6-supervise handles PID liveness natively
- The PID file (/tmp/*.pid) — s6 tracks PID internally
- no_agent=true cron entries with script paths

### Preserved
- The bridge process itself (same command, same args)
- The log files (still written by the bridge)
- The user context (hermes, same as before)

### Changed
- Startup: at container boot (via bundle), no longer at cron interval
- Crash recovery: instant (s6 restarts on exit), no longer waits for next cron tick
- Health check: PID-level only (s6-supervise). If you need application-level
  health checks (/health endpoint responses, file freshness), add a separate
  s6 service with a `probe` or wire it into a separate cron that checks
  and reports — but the process itself is supervised.

## Pitfalls

### Environment context differs from cron

Cron jobs inherit `$HERMES_HOME` and `$PATH` from the cron scheduler's
environment. s6 services inherit from `/run/s6/container_environment/` via
`with-contenv`. If the bridge needs python/node venv bin on PATH, use an
absolute path (`/opt/hermes/.venv/bin/python3`, `/usr/bin/node`) rather than
relying on PATH resolution. Run scripts are POSIX `sh`, not bash — no `source`.

### Service persists across container restarts but NOT rebuilds

s6 service directories under `/etc/s6-overlay/s6-rc.d/` live on the
container's overlay filesystem. They survive `docker restart` but are lost
on `docker rm` + `docker run`. If you're using a deployment mechanism that
rebuilds the container (e.g. alps repo push → rebuild/restart), the s6
service files must be recreated by the deployment or baked into the image.

### User bundle registration requires a file on disk

Just creating the service directory is not enough — the service won't
auto-start. The `user/contents.d/` directory must contain an empty file
whose name matches the service directory name. Without it, the service
exists but s6-rc won't activate it.

### Privilege drop must use `exec`

The `run` script MUST use `exec` to replace itself with the target process.
Without `exec`, a shell stays resident as the supervised process, and s6
tracks the shell's PID — killing/restarting the shell, not the bridge.
This is standard s6 practice and applies to ALL longrun services, but it's
especially easy to miss when adapting a cron watchdog script that uses
`nohup ... &` to background processes. s6 runs the process in the
foreground — no backgrounding needed.
