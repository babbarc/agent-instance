# Platform Consistency Audit Checklist

A reusable cross-layer audit for the Joy platform. Run during Phase 1c of the maintainer cycle. Each layer checks a different category of drift — documentation vs reality, stale references, orphaned files, and architectural consistency.

## Layer 1 — Tier 1 Memory (Live Store)

Check that the actual memory store content matches its documented frozen layout.

```
# Read the live store
cat /opt/data/memories/MEMORY.md

# Count entries (delimited by § on its own line)
# Verify against the documented layout in system-architecture.md §3.7
```

**Checks:**
- [ ] Entry count matches system-architecture.md §3.7 (currently 4)
- [ ] Order matches documented order exactly
- [ ] Each entry's content is current (not stale wording like "ZERO TOLERANCE" when the actual entry says "PROACTIVE GUARD")
- [ ] Usage < 90% (check via `memory` tool — entries show usage)
- [ ] USER.md at `/opt/data/memories/USER.md` has the correct entry matching `contacts/pallav-vasa.md` without duplication
- [ ] USER.md content is not stale (matches pallav-vasa.md)

## Layer 2 — Patched Source Files

The patched versions at `~/.hermes/patches/` must match current architecture.

**Files to check:**
- `~/.hermes/patches/memory_tool.py` — verify the tool description says "exactly N frozen" matching current count
- `~/.hermes/patches/prompt_builder.py` — verify MEMORY_GUIDANCE says "holds only N frozen" matching current count

**Checks:**
- [ ] Tool description count is current
- [ ] MEMORY_GUIDANCE count is current
- [ ] Module docstring (top of memory_tool.py) doesn't contradict the architecture (e.g., saying "agent's personal notes" when Tier 1 is strictly behavioral guardrails)

## Layer 3 — File vs QMD Index Cross-Reference

Verify files in `$HERMES_HOME/memory/` exist on disk and are indexed by QMD.

```
podman exec qmd qmd ls memory-tree | wc -l

for f in \
  $HERMES_HOME/memory/shared-facts.md \
  $HERMES_HOME/memory/environment/environment.md \
  $HERMES_HOME/memory/security/policy.md \
  $HERMES_HOME/memory/security/pass-cheatsheet.md \
  $HERMES_HOME/memory/tools/browser.md \
  $HERMES_HOME/memory/tools/contacts.md \
  $HERMES_HOME/memory/tools/knowledge-policy.md \
  $HERMES_HOME/memory/tasks/pending.md; do
  [ -f "$f" ] && echo "✅ $f" || echo "❌ MISSING: $f"
done
```

**Checks:**
- [ ] All documented paths exist
- [ ] QMD index count approximates disk file count (may differ slightly due to non-.md files)

## Layer 4 — Skills Stale Reference Scan

Search all SKILL.md files for stale architecture references. These accumulate when skills are written against one version of the architecture but the architecture evolves.

```
grep -r "4 frozen\|3 frozen\|ZERO TOLERANCE\|screenshot rule" /opt/data/skills/ --include="SKILL.md"
```

**Checks:**
- [ ] No skill references old entry count ("3 frozen", "4 frozen" — should match current)
- [ ] No skill references renamed entries ("SECURITY — ZERO TOLERANCE" — should be "PROACTIVE GUARD")
- [ ] No skill references deleted entries (e.g., "screenshot rule" if it was removed or renamed)

## Layer 5 — SOUL.md Path Verification

SOUL.md is auto-loaded by Hermes from `$HERMES_HOME/SOUL.md`. It should be hardlinked to `$HERMES_HOME/memory/SOUL.md`.

```
stat -c "%i %n %h (links)" /opt/data/SOUL.md $HERMES_HOME/memory/SOUL.md
find /opt -xdev -inum $(stat -c "%i" /opt/data/SOUL.md) 2>/dev/null
```

**Checks:**
- [ ] `/opt/data/SOUL.md` and `$HERMES_HOME/memory/SOUL.md` share the same inode (hardlinked)
- [ ] At least 2 links exist
- [ ] Content is identical between the two paths (no divergence)

## Layer 6 — Profile Count vs Documentation

`profiles-crons.md` documents N profiles; the filesystem may have M.

```
echo "Documented: N profiles"  # count from profiles-crons.md table
echo "Actual: $(ls /opt/data/profiles/ | wc -l) profiles"
ls /opt/data/profiles/ | grep -v -E '^<documented-names>$' | xargs -I{} echo "Undocumented: {}"
```

**Checks:**
- [ ] Documented count matches actual count
- [ ] No undocumented profile directories on disk
- [ ] All documented profiles have their directory on disk

## Layer 7 — Cron Job Health

```
cronjob(action='list')
```

**Checks:**
- [ ] All jobs have realistic next_run_at (not in the past unless they're running)
- [ ] No job has repeated `last_status` of "error" or "failed"
- [ ] Schedules are reasonable (not running every minute)
- [ ] Missing `last_run_at` is explained (never-run jobs for future-only schedules)

## Layer 8 — QMD Index Integrity

```
qmd list 2>/dev/null | head -20
# Then try embed to check for missing content
qmd embed 2>/dev/null
```

**Checks:**
- [ ] QMD index is not empty
- [ ] qmd embed completes without errors (or confirms all hashes are embedded)
- [ ] Recent changes to `$HERMES_HOME/memory/` files are reflected

## Common Fixes

| Finding | Fix |
|---------|-----|
| Stale count reference in system-architecture.md §3.7 | `patch` the line to correct number |
| Stale frozen layout in skill | `skill_manage(action='patch')` the SKILL.md |
| Orphan file not referenced by the memory tree | Remove after confirming truly stale. |
| Module docstring contradicts architecture | `patch` the docstring in `~/.hermes/patches/memory_tool.py` |
| Undocumented profile | Add row to `profiles-crons.md` or remove the directory |
| Broken SOUL.md hardlink | `ln -f $HERMES_HOME/memory/SOUL.md /opt/data/SOUL.md` (hardlink, not symlink) |
