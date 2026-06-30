---
name: distill-memory
category: system
description: "Procedure for distilling all memory layers: tree-wide assessment, tool store distillation, and reference file cleanup."
annotation: "Distill memory tiers: tree-wide assess, consolidate, prune"
---

# Distill Memory

Run this when asked to distill memory or periodically as maintenance. Covers all three layers: memory tree, tool store, and reference files.

---

## Layer Reference

| Layer | Location | Contents |
|-------|----------|----------|
| **Tool store** | `memory` tool (MEMORY.md + USER.md) | 2-4 behavioral re-anchor rules, user preferences |
| **Memory tree** | `/opt/data/memory/` (git-tracked) | Durable facts — architecture, life trackers, reference files |
| **Reference files** | Skill `references/` dirs | Incident logs, architecture docs, detailed research |

---

## Phase 1 — Tree-Wide Assessment

1. **Git status** — `git status /opt/data/memory/` to find modified files. These are active areas of change — investigate first.

2. **Categorize every file** with `find /opt/data/memory/ -type f | sort`:
   - **Active reference** — user profile, shared facts, environment, architecture docs, active life trackers, skill triggers, DB schemas → keep
   - **Stale/completed** — finished processes, abandoned research → remove or archive
   - **Prompt snapshots** — point-in-time copies of cron prompts from jobs.json → remove (live source is canonical)
   - **Raw data** — OCR statements, DB files → leave untouched
   - **Bug/incident logs** — distill to 3-4 bullet lessons, remove verbose narrative

3. **For each stale candidate**, verify against active kanban tasks and life-goals.md milestones before deleting.

4. **Remove stale files** with `git rm <path>`. Commit each removal separately.

---

## Phase 2 — Tool Store Distillation

1. Read both store files — `MEMORY.md` (your notes) and `USER.md` (user profile).

2. **Evaluate each entry:**
   - Still true? Would it fire correctly next session?
   - References a specific date, migration, or one-time incident that's passed?
   - Duplication between entries (same theme expressed twice)?
   - **Explains what a tool/skill does?** → Tool and skill descriptions handle explanations. Strip to bare routing: `"Trigger" → action.`

3. **Rewrite** — Merge redundant entries, strip dated specifics, tighten language. Aim for 40-60% reduction.
   - Cap entries at one routing line per trigger. If it explains *how* something works, it's redundant.
   - Example of too long: `"Ask claude" → use the claude_code tool. The tool wraps Claude Code CLI with proper timeout, session resume, budget caps, and effort control.`
   - Example of correct: `"Ask claude" → claude_code tool.`

4. **Commit each logical change** — `git add memories/<file> && git commit -m "distill: ..." && git push origin main`

5. **Sync the in-session store** — `memory(action='replace/remove/add', target='memory'/'user')` to match the file. Then `git add && git commit -m "sync: memory tool store matches file"`

---

## Phase 3 — Reference File Distillation

For verbose reference files (incident logs, architecture docs, detailed research):

1. **Is it an active reference?** — If consulted regularly, it should be scannable in 30 seconds.
2. **Distill to essentials** — Remove "Root cause:", "Fix:" narrative. Keep only the actionable lesson as a bullet.
3. **Remove story** — Dates, filenames, debugging journeys are noise. The lesson is the signal.
4. **Commit** — `git add && git commit -m "distill: <file>: <old>-><new> chars, retain only actionable lessons" && git push`

---

## Memory Tool § Pitfall

The `memory` tool interprets `§` as an **entry delimiter**, not literal text. This fragments combined entries and causes duplicate blocks on replace.

**Fix:** Always store entries individually — one `memory(add/remove)` call per entry. Never use `§` as a separator inside a single entry.

**Detection:** If `MEMORY.md` or `USER.md` shows duplicate content blocks, the § pitfall has struck. Patch the file to remove duplicates, then rebuild the tool store entry-by-entry.
