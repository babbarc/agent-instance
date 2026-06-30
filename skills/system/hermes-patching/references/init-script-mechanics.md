# Init Script Mechanics

## Where it lives
Source (writable): `/opt/data/home/hermes-agent/99-hermes-patches.sh`
Mount (read-only inside container): `/etc/cont-init.d/99-hermes-patches:ro,Z`
Changes take effect on next container start.

## Adding a new tracked file
1. Edit `/opt/data/home/hermes-agent/99-hermes-patches.sh`
2. Add backup line: `cp "$INSTALL_DIR/<path>/<file>.py" "$PATCHES_DIR/<file>.py.original" 2>/dev/null || true`
3. Add `<file>` to the `for f in` loop
4. Create `.original` and `.patch` in `~/.hermes/patches/`
5. Restart container

## Apply logic
```
for f in <list>:
  if $f.patch exists && patch --dry-run succeeds:
    patch -p0 -d /opt/hermes < $f.patch  →  status "ok"
  else:
    status "failed"  (patch skipped, no partial apply)
```

## Status
`cat ~/.hermes/patches/status.json` — "ok" = applied, "failed" = dry-run failed at boot.
