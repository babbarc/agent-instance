# Container Restart Procedure

## When to restart

- After creating or updating `.patch` files in `~/.hermes/patches/` — `99-hermes-patches.sh` runs at container init and applies them
- After rebuilding a container image (e.g. `podman build -f Containerfile.hermes -t localhost/hermes:latest .`)
- After modifying quadlet `.container` files

## How to identify the container

The Hermes gateway runs as a **Podman quadlet** — systemd user service.

```
Container name: hermes
Service name:   hermes.service
Quadlet file:   ~/.config/containers/systemd/hermes.container
Source repo:    <infra-repo>/hermes.container
```

Check with:

```bash
systemctl --user status hermes.service
```

The quadlet has `Restart=always` — any stop triggers an automatic restart within 5 seconds.

## Restart command

```bash
systemctl --user stop hermes.service
```

Do NOT use `start` or `restart` — `stop` is sufficient because `Restart=always` brings it back. The s6-overlay init inside handles graceful shutdown of all services before exit.

## Safety checks before restart

| Concern | Why safe |
|---------|----------|
| **Data persistence** | `/opt/data` is on a named volume (`hermes-data`). All files, kanban DB, memory, patches survive. |
| **Image integrity** | The image is local (`localhost/hermes:latest`). No dependency on external registry. |
| **Service recovery** | `Restart=always` + `RestartSec=5s` — comes back in seconds. |
| **Patch application** | `99-hermes-patches.sh` runs at cont-init.d (before services start) as root, so it can write to `/opt/hermes/` owned by uid 10000. |

## Verify patches applied after restart

Check the status file written by `99-hermes-patches.sh`:

```bash
cat /opt/data/home/.hermes/patches/status.json
```

Example output:
```json
{
  "approval.py": "ok",
  "clarify_tool.py": "ok",
  "memory_tool.py": "ok",
  "prompt_builder.py": "ok",
  "skill_manager_tool.py": "ok"
}
```

Any `"failed"` entry means the patch was skipped — upstream Hermes changed the same area and the context no longer matches.

## If a patch failed

1. Regenerate the patch against the **clean upstream file** from the installed image, not an already-patched copy:

   ```bash
   cp /opt/hermes/agent/prompt_builder.py /tmp/clean.py
   cp /opt/hermes/agent/prompt_builder.py /tmp/patched.py
   # edit /tmp/patched.py with the desired changes
   diff -u /tmp/clean.py /tmp/patched.py > ~/.hermes/patches/prompt_builder.py.patch
   ```

2. Fix the headers to use install-relative paths
3. Verify with `patch --dry-run -p0 -d /opt/hermes < ~/.hermes/patches/prompt_builder.py.patch`
4. Commit the `.patch` to `joy-brain` repo
5. Restart the container

## Common pitfalls

- **Don't create patches against an already-patched file.** The diff context won't match the clean upstream on the next boot. Always diff against `/opt/hermes/<file>` (the installed original), not a modified copy you made last session.
- **Running user can't apply patches at runtime.** `/opt/hermes/` is owned by uid 10000; you're uid 1003. Patches only apply at container init via `99-hermes-patches.sh` (runs as root).
- **`uptime -s` shows host boot time, not container start time.** Use `stat /proc/1/` or check the `status.json` modification time instead.
