# Profile Identity Composition

## What Happened

**guards.md was planned as a companion identity file for profile composition but the patch was never implemented.** The file (now deleted) sat on disk unused from May-June 2026. Every agent — default or named profile — loads only `SOUL.md` via `load_soul_md()`.

This document exists to prevent future readers from reinventing this approach.

## The Original Design (Abandoned)

The concept was two-layer composition:

```
Root HERMES_HOME (/opt/data/)
  └── guards.md        ← Universal guard rails (planned, never loaded)

Profile HERMES_HOME (/opt/data/profiles/<name>/)
  └── SOUL.md          ← Persona-specific identity
```

`load_soul_md()` in `prompt_builder.py` would have:
1. Loaded `guards.md` from root `$HERMES_HOME`
2. Loaded `SOUL.md` from current `$HERMES_HOME`
3. Composed: `guards.md + "\n\n" + SOUL.md`

**Why it was abandoned:** The `prompt_builder.py.patch` file was created but the composition logic for guards.md was never added to it. Only the MEMORY_GUIDANCE, SKILLS_GUIDANCE, and WORKFLOW_GUIDANCE patches were applied. guards.md sat on disk for a full month before being deleted (June 2026).

## Current State

Every agent — default or named profile — loads only `SOUL.md` in identity slot #1:

- **Default profile** (`/opt/data/SOUL.md`): Joy's full identity (prime directive, execution discipline, storage routing, etc.)
- **Named profiles** (e.g., `/opt/data/profiles/fitness-coach/SOUL.md`): Profile-specific persona only

There is no universal guard layer shared across profiles. If a guardrail needs to apply everywhere, it must be explicitly written into each profile's `SOUL.md`.

## What This Means

| Property | Before (planned) | After (actual) |
|----------|-----------------|----------------|
| Universal rules shared across profiles | `guards.md` at root | N/A — each profile owns its SOUL.md |
| Profile persona | `SOUL.md` in profile dir | Same |
| Changes propagate to all profiles | Edit one `guards.md` | Must edit each SOUL.md |
| Risk of drift | Low (centralised) | High (per-profile maintenance required) |

## Implications

If you want to add a rule that applies to ALL profiles in the future, the options are:

1. **Add it to each profile's `SOUL.md`** — manual, drifts, but works today
2. **Add it to the memory tool store** (`MEMORY.md`) — injected into every agent every turn, but meant for behavioral re-anchor, not identity
3. **Revive the guards.md approach** — create a new `guards.md`, then patch `load_soul_md()` for real this time. The patch scaffolding (`99-hermes-patches`) already exists.

## Memory Isolation (Still Current)

Regardless of identity, each profile gets its own **memory tree** and **QMD collection**:

```
# Memory tree — profile's own writable storage
mkdir -p /opt/data/profiles/<name>/memory/
touch /opt/data/profiles/<name>/memory/.gitkeep

# QMD collection — makes the tree searchable
podman exec qmd qmd collection add "<name>" \
  --path "/opt/data/profiles/<name>/memory" \
  --pattern "**/*.md"
```

**Convention documented in each profile's SOUL.md:**
- `$HERMES_HOME/memory/` = profile's own writable tree (via file tools)
- Searchable via `mcp_qmd_query(searches=[...], collections=["<name>"])`
- Main memory at `/opt/data/memory/` is **read-only reference** — search via QMD, never write directly
- Auto-indexed by QMD every 10 minutes (same as the main tree)

### Current QMD Collections

| Collection | Path | Profile |
|------------|------|---------|
| `memory-tree` | `/opt/data/memory/` | Main agent |
| `contacts` | `/opt/data/contacts/` | Shared |
| `ca-expert` | `/opt/data/profiles/ca-expert/memory/` | Finance |
| `career-advisor` | `/opt/data/profiles/career-advisor/memory/` | Career |
| `family-organizer` | `/opt/data/profiles/family-organizer/memory/` | Family |
| `fitness-coach` | `/opt/data/profiles/fitness-coach/memory/` | Fitness |
| `health-tracker` | `/opt/data/profiles/health-tracker/memory/` | Health |
| `home-manager` | `/opt/data/profiles/home-manager/memory/` | Home |
| `inventory-manager` | `/opt/data/profiles/inventory-manager/memory/` | Inventory |
| `legal-expert` | `/opt/data/profiles/legal-expert/memory/` | Legal |
| `travel-planner` | `/opt/data/profiles/travel-planner/memory/` | Travel |
