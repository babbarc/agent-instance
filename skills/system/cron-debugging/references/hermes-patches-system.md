# Hermes Patches System

## Patch Location
Patches live at `~/.hermes/patches/`. Each has three files:
- `<module>.patch` — the actual diff
- `<module>.original` — backup of upstream file
- `status.json` — verification map of all applied patches

## Boot-Time Application
Patches are applied via `99-hermes-patches.sh` on gateway start:
```bash
for patch in ~/.hermes/patches/*.patch; do
    name=$(basename "$patch" .patch)
    patch -N -p1 < "$patch" && echo "$name: ok"
done
```

## Current Patches on This System
- `scheduler.py.patch` — ContextVar-only cron profile override (see v0.17.0-profile-removal.md)

## Verification
```bash
cat ~/.hermes/patches/status.json | grep scheduler
```

## Safety Rules
- Never modify patches while the gateway is running
- Always create a `.original` backup before applying new patches
- Verify after each gateway restart: `cat ~/.hermes/patches/status.json`
