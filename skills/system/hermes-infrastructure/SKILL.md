---
name: hermes-infrastructure
description: "Work on the hermes-agent.git repo: quadlet .container files, Containerfiles, browser-proxy, QMD vector store, and the build.sh pipeline that defines the entire Podman stack running the Hermes agent gateway."
annotation: "hermes-agent.git: quadlet containers, s6, infrastructure"
annotations:
  - quadlet
  - podman
  - containerfiles
  - hermes-stack
  - infrastructure-as-code
  - self-hosted
---

# Hermes Infrastructure Repo

## When to use this skill

The user says any of:
- "infrastructure" / "quadlet" / "container file" / "build pipeline"
- "browser proxy" / "qmd container" / "hermes container"
- "Podman stack" / "agent infra" / "image build"
- References the `hermes-agent` repo or `alps:babbarc/hermes-agent.git`

Do NOT use this skill for:
- The agent's runtime config (config.yaml, patches, skills, cron) — those live in `/opt/data/` (joy-brain repo)
- Upstream s6 services that ship with Hermes (main-hermes, dashboard, s6rc-fdholder) — those are at `nousresearch/hermes-agent`
- QMD query tuning, search configs, or MCP tool setup

CUSTOM s6 services (cupsd, vision-bridge, baileys-watch) ARE added via Containerfile.hermes — that's this skill's domain.

## Repo location and primer

Path: `/opt/data/home/hermes-agent/`
Remote: `alps:babbarc/hermes-agent.git`

Before working, always `git pull origin master` to avoid stale state. The repo is the single source of truth for how the containers are built and run — what you see here is what Podman runs.

## Structure map (load these to orient)

| File | What it defines |
|---|---|
| `hermes.container` | Main gateway container — mounts, volumes, network, entrypoint |
| `qmd.container` | Vector store container — GPU passthrough, volume layout |
| `browser-proxy.container` | Lazy on-demand CDP proxy container |
| `Containerfile.hermes` | Image build on top of upstream hermes-agent — apt packages, env vars |
| `Containerfile.qmd` | QMD image — Intel GPU drivers, Node, qmd npm install, CMD |
| `Containerfile.browser` | Chrome image — anti-fingerprint entrypoint |
| `Containerfile.browser-proxy` | Slim Python+podman image for the proxy |
| `browser-proxy.py` | Async TCP proxy — starts/stops Chrome on demand, idle timeout, SIGTERM |
| `docker-entrypoint-browser.sh` | Chrome startup — strips "HeadlessChrome" from UA |
| `99-hermes-patches.sh` | Boot-time patch injection into /opt/hermes |
| `build.sh` | Full pipeline: stop → build 4 images → push → deploy quadlets |
| `test-teardown.sh` | Integration tests for browser-proxy lifecycle |

## Adding custom s6 supervised services

When the user wants a daemon/bridge/background process that auto-starts at boot and restarts on crash, add it as an s6 `longrun` service via Containerfile.hermes. The pattern (used by cupsd, vision-bridge, and baileys-watch) is:

### Per-service setup (in Containerfile.hermes)

```dockerfile
# 1. Copy the run script from the build context
COPY <service>-run.sh /etc/s6-overlay/s6-rc.d/<service>/run

# 2. Set executable + declare type
RUN chmod +x /etc/s6-overlay/s6-rc.d/<service>/run && \
    echo "longrun" > /etc/s6-overlay/s6-rc.d/<service>/type && \
    mkdir -p /etc/s6-overlay/s6-rc.d/<service>/dependencies.d

# 3. Register in the user bundle so s6 auto-starts it at boot
RUN touch /etc/s6-overlay/s6-rc.d/user/contents.d/<service>
```

### Run script template

```sh
#!/command/with-contenv sh
# shellcheck shell=sh
# <Service name> — what it does.

# REQUIRED: with-contenv loads HOME from /run/s6/container_environment
# which is /root. Override so pass, node, python resolve ~ correctly.
export HOME=/opt/data/home

# Drop to hermes user for file ownership and pass store access.
# Always exec so s6-supervise tracks the real PID.
exec s6-setuidgid hermes <command>
```

### Key rules

- **Shebang MUST be `#!/command/with-contenv sh`** — it loads env from `/run/s6/container_environment/` (PATH, HOSTNAME, etc.)
- **Override HOME** — `with-contenv` defaults it to `/root`. The hermes user's data lives under `/opt/data/home` (pass store, .hermes dirs, node_modules).
- **`s6-setuidgid hermes`** — drops privileges to the hermes user. No `sudo` available in the container; `/command/s6-setuidgid` is the correct tool.
- **Always `exec`** — the shell replaces itself with the daemon process so s6-supervise tracks the right PID for restart-on-crash.
- **One-time init**: use a `(...) &` subshell block (cupsd pattern) for setup that must run after the main process starts. Give the main process a few seconds with `sleep 3` first.

### When PID-level supervision is sufficient

Both the vision bridge (HTTP server) and baileys watch (WebSocket client) run at PID-level only — no companion health-check services. This works because:

- **Vision bridge**: Python HTTP server. If it can't bind port 9877 or the handler crashes, the process exits and s6 restarts it.
- **Baileys watch**: Node.js WebSocket client. Exits on logout (`process.exit(1)`), auto-reconnects on disconnect. If the main loop dies (unhandled rejection), Node.js ≥15 exits and s6 restarts.

Application-level probes (`/health` endpoint, deltas.ndjson freshness) are unnecessary when the process correctly exits on all unrecoverable errors. s6 catches the exit instantly, rather than polling every 3h.

### Services added this way

| Service | Type | Script | Port | User |
|---|---|---|---|---|
| cupsd | CUPS print spooler | `cupsd-run.sh` | 631 | root (cupsd requirement) |
| vision-bridge | Gemini/Claude vision proxy | `vision-bridge-run.sh` | 9877 | hermes |
| baileys-watch | WhatsApp WebSocket connection | `baileys-watch-run.sh` | — | hermes |

### Pitfall: Init-once guards create silent state drift

A common pattern in s6 run scripts is:

```sh
if ! /usr/bin/lpstat -p "SERVICE" 2>/dev/null; then
    # create resource on first boot
fi
```

This guards against re-creating state on every container restart. **But it also means a bug in the creation logic, once fixed in a later commit, never fixes the existing resource** — the guard skips re-creation because the resource already exists.

This is what happened with `cupsd-run.sh`:
- Original commit (Jun 10 21:29) used `find /usr/share/cups/model` to locate the ESC/P-R PPD, but printer-driver-escpr serves PPDs dynamically via a CUPS driver program — `find` returns nothing → falls back to `"everywhere"` (driverless IPP)
- Fix commit (Jun 10 21:45) switched to querying `/usr/lib/cups/driver/escpr list` directly — works correctly
- But the queue was already created with the broken logic on first boot. The guard (`if ! lpstat -p ET-2750`) sees it exists and skips. The fix is dead code on production.

**Mitigations:**
- **Version stamp**: Write a version marker alongside the resource (e.g. a comment in the PPD, or a separate stamp file at `/var/lib/cups/queue-version`). On each boot, compare the stamp. If stale, delete and recreate.
- **Forced re-add**: Remove the guard entirely and use `lpadmin -p ...` unconditionally (with `-x` to delete first if it exists). This is safe for s6 because `sleep 3` gives cupsd time to initialize, and the script runs in a subshell — the main `exec` isn't delayed.
- **Manual cleanup**: After fixing a setup script that has already created state on production, delete the resource manually (`lpadmin -x ET-2750`) so the next boot recreates it with the fix.

When adding any `if ! check; then create; fi` guard to an s6 run script, ask: "If this creation logic has a bug, how will I recover?"

### Pitfall: HOME must be explicit

`with-contenv` populates HOME from `/run/s6/container_environment/HOME` which is `/root` in the image. Without an explicit `export HOME=/opt/data/home`, pass and npm won't find their expected paths under the hermes user. The dashboard service (which runs as hermes) sets `export HOME=/opt/data` — for bridges that need the password store, it must be `/opt/data/home`.

### Pitfall: Run scripts live in the build context

Each run script is a standalone file in the repo root (e.g. `cupsd-run.sh`, `vision-bridge-run.sh`) because `COPY` in Containerfile can't inline content. They must be executable (`chmod +x`) and use the `#!/command/with-contenv` shebang. Keep them small — the run script is just env setup + exec. Any init logic goes in a `(...) &` subshell or a separate script.

## References

- `references/container-restart.md` — How to cleanly restart the container, verify patches applied, and regenerate a failed patch against the correct base.
- `references/browser-proxy-cookie-persistence.md` — Why browser cookies are lost (idle timeout, Chrome scoped_dir), how to diagnose, the `--user-data-dir` fix, and the UID namespace permission issue with shared volumes.
- `references/custom-s6-services.md` — Detailed session notes about replacing cron watchdogs with s6 services, including the full reasoning for PID-level vs application-level health checks and the pass store setup for the hermes user.

Read the `.container` files first when the user asks about how something runs — they're the entry point. Read `Containerfile.*` when the question is about what's in the image. Read `browser-proxy.py` when debugging browser behaviour.

## Workflow

1. **Pull** — `cd /opt/data/home/hermes-agent && git pull origin master` (always start here)
2. **Read current state** — load the relevant file(s) from the structure map above
3. **Change** — edit the file(s) with patch/write_file. One logical change per commit.
4. **Commit** — `git add -A && git commit -m "scope: description"`
5. **Push** — `git push origin master` (the server pulls from the same remote)

No `build.sh --deploy` — the running stack is outside this session's network. Pushing to `alps` makes changes available when the server rebuilds.

### Pitfall: User Deploys Infrastructure Changes

**Do NOT attempt to rebuild or restart containers locally** without explicit user request. The user deploys infrastructure changes themselves. When blocked on `podman build` or `systemctl restart`:

1. Push to `alps` first — that's your deliverable
2. Tell the user what was changed and what they need to run
3. Let them execute the build/restart

This applies to all podman operations that affect running infrastructure (build, stop, restart, rm, run). Read-only operations (ps, inspect, logs) are fine.

### Pitfall: Investigate Before Assuming Session Loss

When the user reports cookies disappearing, session expiring, or browser state being lost:

1. **Check actual state first** — `podman ps` to see if containers are running, `podman inspect` for args, check Chrome process flags
2. **Look for accumulated scoped directories** — `podman exec hermes-browser sh -c 'ls -ld /tmp/com.google.Chrome.scoped_dir.* | wc -l'` reveals restart count
3. **Check proxy config** — `podman exec browser-proxy sh -c 'cat /proc/1/environ | tr "\\0" "\\n" | grep IDLE_TIMEOUT'`
4. **Verify cookies exist** — CDP `Network.enable` + `Network.getAllCookies` (Network.enable is REQUIRED first — without it, getAllCookies returns empty silently)
5. **Never assume expiry** — Google session cookies last hours to weeks. If they're gone, trace the actual cause (tab navigation, container restart, scoped_dir creation)

The most common root causes (in order): idle timeout stop/start creating new scoped_dir, proxy startup deleting/recreating container, scripts navigating the tab away from the session. Each has a different fix.

### Shared Volume Permission — UID Namespace Pitfall (June 2026)

The `hermes-browser-data` volume is mounted in the hermes container at `~/chrome-downloads/` so the agent can read browser downloads. Chrome creates its profile with `0700` owned by uid 999. The hermes agent runs as uid 1003 — permission denied.

**The naive fix (setfacl) doesn't work** because both containers use rootless podman with **different UID namespace mappings**. When `setfacl -m u:1003:rx` runs inside the browser container, the kernel stores the ACL for browser-namespace-uid-1003 (→ host UID ~363146). When the hermes agent accesses the file, it runs as hermes-namespace-uid-1003 (→ host UID 0). ACL UID ≠ process UID → silently ignored.

**Correct fix:** Create a world-accessible download directory separate from the profile, so no namespace crossing is needed:

```
# docker-entrypoint-browser.sh (before exec google-chrome-stable):
mkdir -p /home/chrome/devtools-profile/downloads
chmod 0777 /home/chrome/devtools-profile/downloads
```

Chrome flag in `browser-proxy.py`:
```
--download-default-dir=/home/chrome/devtools-profile/downloads
```

The volume root is 755 world-readable. A `777` subdirectory is accessible from any container regardless of namespace. See `references/browser-proxy-cookie-persistence.md` for the full diagnosis recipe and comparison of approaches.

**Key insight:** Google auth cookies all have `session: false` and multi-year expiry — they are written to Chrome's `Default/Cookies` SQLite database on the volume. The volume alone is sufficient for session persistence. Script-level cookie save/restore (`save_cookies()` / `try_cookie_restore()`) is redundant and unnecessary.

### Browser-Proxy Fix (June 2026, commits d4e190b + 6abaf66 + bfc8a55)

The `browser-proxy.py` was patched to fix cookie loss on idle timeout and container restart:

| Layer | Fix | What it solves |
|---|---|---|
| Code | `IDLE_TIMEOUT` 300s → 3600s (1h) | Browser doesn't stop after 5 min idle |
| Code | `--user-data-dir=/home/chrome/devtools-profile` | Chrome uses fixed non-default profile, not fresh `scoped_dir.*` on each start |
| Code | `--download-default-directory` points to profile subfolder | Downloads land on the volume |
| Volume | `hermes-browser-data` mounted at profile path | Profile survives `rm → run` (full container recreation) |
| Volume | Same volume on hermes at `~chrome-downloads/` | Agent can access browser downloads |

**Persistence guarantee:** After one login, profile (cookies, sessions, downloads) survives stop, start, rm, run, proxy restart, server reboot. The volume is one-time infrastructure — never create it inside the proxy script.

### Pitfall: Chrome 148+ Blocks Default Profile for Remote Debugging

Chrome ≥148 refuses to start the DevTools server (`--remote-debugging-port`) when `--user-data-dir` points to the **default profile path** (`~/.config/google-chrome`). It prints:

```
DevTools remote debugging requires a non-default data directory. Specify this using --user-data-dir.
```

Even though you ARE passing `--user-data-dir`, if the resolved path matches the default, Chrome detects it as the default profile and blocks remote debugging. **Always use a path that differs from Chrome's default.** For Hermes: `/home/chrome/devtools-profile`.

**Symptom:** Browser container is up, Chrome process is running, port 3334 shows no LISTEN. Proxy returns empty replies because it connects to Chrome but Chrome isn't serving DevTools.

## Allowed podman operations

- `podman image exists <name>` — check what's built
- `podman ps` — list running containers
- `podman inspect <container>` — examine runtime config
- `podman logs <container>` — read logs
- `podman build -f Containerfile.X -t tag .` — build images (verify Dockerfile path and context first)
- `podman run --rm <image> <command>` — test a container in isolation
- `systemctl --user stop <quadlet-service>` — restart a local container (Restart=always brings it back). See `references/container-restart.md` for the full procedure.

No `podman push`, no registry operations. Do NOT deploy quadlets to remote machines from this session.

## Adding a new runtime patch

Patches are applied via unified diff (`.patch`) files with dry-run safety — if upstream Hermes changed a patched area, the patch is skipped and the system boots with the upstream version intact.

To add a new patched file:

1. **Determine the diff base.** See `patch-hermes-files` skill for the critical distinction between "first-time/replacing" patches (diff from `.original`) vs "incremental on live" patches (diff from current installed file). In most cases — first-time patch, or replacing a stale combined patch — use `.original` as the base since the container resets to clean upstream at every boot.

2. **Generate the patch:**
   ```bash
   # For first-time or replacing: diff from .original
   cp ~/.hermes/patches/<file>.py.original /tmp/<file>.base 2>/dev/null || \
     cp /opt/hermes/<relative-path>/<file> /tmp/<file>.base
   cp /tmp/<file>.base /tmp/<file>.patched
   # edit /tmp/<file>.patched with your changes
   diff -u /tmp/<file>.base /tmp/<file>.patched > ~/.hermes/patches/<file>.patch
   ```
2. **Fix patch headers** — replace absolute paths with install-relative ones so `patch -p0` resolves them from `/opt/hermes/`:
   ```bash
   sed -i "1s|/opt/hermes/<relative-path>/<file>|<relative-path>/<file>|" ~/.hermes/patches/<file>.patch
   sed -i "2s|/tmp/<file>.patched|<relative-path>/<file>|" ~/.hermes/patches/<file>.patch
   ```
3. **Register in the loop** — add the filename to the `for f in ...` list in `99-hermes-patches.sh`
4. **Commit both repos** — commit the `.patch` file to `joy-brain` (`~/.hermes/patches/`), commit the `99-hermes-patches.sh` update to `hermes-agent`
5. **Restart the container** — patches apply at boot. On conflict, a warning is logged to stderr and the system runs the upstream version unmodified.
6. **Verify** — after restart, check `~/.hermes/patches/status.json` to confirm all patches applied cleanly.

**Critical pitfall — patch base:** Always diff against `~/.hermes/patches/<file>.py.original` (the boot-time backup of clean upstream), NOT against `/opt/hermes/<file>` (the installed file) — the installed file may already have patches applied from a previous boot. Creating a patch from an already-patched file produces context lines that won't match the clean upstream on the next boot, causing `patch --dry-run` to fail and the patch to be silently skipped. See `patch-hermes-files` skill for the full diff base decision tree (Scenario A vs B).

Existing patches: `approval.py`, `clarify_tool.py`, `memory_tool.py`, `prompt_builder.py`, `skill_manager_tool.py`, `system_prompt.py`. All live in `~/.hermes/patches/` as `.patch` files with corresponding `.original` copies saved at boot for diff reference against upstream. A `status.json` is written alongside them after each boot, recording `"ok"` or `"failed"` per patch.

## Setting env vars for all services via cont-init.d

When a binary or env var needs to reach ALL supervised services (gateway, dashboard, cron, custom s6 services) without rebuilding the container image, write it to `/run/s6/container_environment/` from a cont-init.d script. The `with-contenv` shebang in every service's `run` script reads this directory at startup.

1. **Choose the injection point:**
   - Existing cont-init.d script already volume-mounted (e.g. `99-hermes-patches.sh`) — append the write there
   - No suitable script — create a new script file and mount it (see step 4)

2. **Write a scalar env var:**
   ```bash
   mkdir -p /run/s6/container_environment
   printf '%s' "VALUE" > /run/s6/container_environment/VARNAME
   ```

3. **For PATH specifically** — read current PATH, prepend new entry, avoid duplicates:
   ```bash
   NPM_BIN="/opt/data/home/.npm-global/bin"
   if [ -d "$NPM_BIN" ]; then
       mkdir -p /run/s6/container_environment
       CURRENT_PATH=$(cat /run/s6/container_environment/PATH 2>/dev/null)
       case ":$CURRENT_PATH:" in
           *":$NPM_BIN:"*) ;;
           *) printf '%s' "$NPM_BIN:$CURRENT_PATH" > /run/s6/container_environment/PATH ;;
       esac
   fi
   ```

4. **Mount a new cont-init.d script** (no image rebuild):
   - Add a bind mount in the `.container` file:
     ```
     Volume=/host/path/to/script.sh:/etc/cont-init.d/XX-script-name:ro,Z
     ```
   - `%h` expands to the host user's HOME at mount time
   - Numeric prefix (`XX-`) sets execution order — lower runs first
   - No `.sh` extension needed — cont-init.d runs anything executable
   - Example: the `99-hermes-patches.sh` mount on line 29 of `hermes.container`

5. **Verify after container restart:**
   ```bash
   podman exec hermes cat /run/s6/container_environment/VARNAME
   podman exec hermes sh -c 'echo "$PATH"'
   ```

## Key conventions

- Containerfile names are `Containerfile.<role>` (not `Dockerfile`)
- `.container` files deploy to `~/.config/containers/systemd/` on the target
- All containers use `Network=host` for podman socket and GPU access
- `hermes-data` named volume is shared between hermes and qmd containers
- `hermes-browser-data` named volume — Chrome profile persistence (cookies, sessions, downloads). One-time infra setup, never create inside proxy script.
- `browser-proxy.py` manages `hermes-browser` container lifecycle independently (not via quadlet)
- Registry is `alps:5000` (internal, not accessible from here)