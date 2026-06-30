# Deduplication Protocol — Single Source of Truth Convention

> **Created:** 13 May 2026 after Phase 1 deduplication found 30+ stale references across 7 files
> **Updated:** 14 May 2026 — added post-consolidation duplication check
> **Applies to:** Any structural change that touches system configuration data

## Why This Exists

The system had cron schedules, profile metadata, and config values replicated across ~15 locations. Every time a schedule changed, 7+ files needed manual updates — and someone always forgot. This protocol eliminates that failure mode.

## The One-Location Rule

**Every system property lives in exactly one documented place.** Everything else either:
- Points there with a pointer note
- References by name only
- Queries at runtime

## Convention Reference

### 1. Name-Only References (for skills)

Skills reference system components by **name only** — never by schedule, path, or config value:

```
✅ Correct: "Load the morning-briefing cron prompt"
❌ Wrong:   "Load the morning-briefing cron prompt (daily 6am BST)"

✅ Correct: "Deploy to the ca-expert profile"
❌ Wrong:   "Deploy to the ca-expert profile (Finance & Tax, at /opt/data/profiles/ca-expert/)"
```

### 2. Pointer-Doc Pattern (for supporting docs)

When a doc needs to reference data that lives in the drift anchor:

```
## Cron Schedule

> **ℹ️ Single source of truth:** All cron job schedules, skills, delivery targets,
> and purposes are documented in `architecture/system-architecture.md §3.4`.
> Update schedules there, not here.
```

Followed by a brief summary (categories of jobs, count) — not a full table.

### 3. Reference-Doc Header Note (for historical/pattern docs)

When a reference doc contains config data that may be stale:

```
> **ℹ️ Schedule source of truth:** Cron fire times are documented in
> `architecture/system-architecture.md §3.4`. This doc covers setup pattern only —
> verify current schedule against the drift anchor before making changes.
```

### 4. Dynamic Data Rule

**Never document inherently dynamic data** (DB row counts, file counts, skill counts) in the drift anchor. These change every session and the documented number is always wrong. Instead:
- Document schema only (table names, purposes — not row counts)
- Query at runtime via DB or filesystem when a count is needed
- The meta-review or heartbeat can report dynamic counts

## Information Hierarchy

| Information | Single Source of Truth | Consumer Pattern |
|------------|----------------------|-----------------|
| **Cron schedules** (fire times, skills, delivery) | `cron/jobs.json` (runtime) + `system-architecture.md §3.4` (documentation) | Name-only in skills; pointer note in other docs |
| **Profile metadata** (purpose, model, config) | Profile configs on disk + `system-architecture.md §3.3` | Pointer note in profiles-crons.md; name-only in skills |
| **Skills categories & counts** | Filesystem + `system-architecture.md §3.6` | Skills reference their own name only |
| **Memory tree structure** | Filesystem + `system-architecture.md §3.7` | QMD (`memory-tree` collection) — search, not replication |
| **User identity & profile** | `contacts/pallav-vasa.md` (canonical) | `shared-facts.md` (compact subset with guardrail); `memory/finance/tax-notes.md` |
| **Dynamic system stats** | The actual DB/filesystem | Query at runtime; never document in anchor |
| **Script paths** | `$HERMES_HOME/scripts/` (filesystem) | Cron config references by filename only |

## Post-Consolidation Duplication Check

After absorbing one file into another (e.g., moving memory content into a skill reference), you MUST verify the target doesn't already contain the same content. This is separate from preventing NEW duplication — it detects PRE-EXISTING duplication in the target.

**Procedure:**
1. Extract 2-3 unique phrases from the content being absorbed (NOT generic words like "purpose" or "rule" — pick distinctive phrases unique to that document)
2. Search the target skill's SKILL.md and all its references/ files for each phrase
3. If near-verbatim matches are found:
   - Replace the duplicated passage in the target with a name-only reference to the new home
   - Example: instead of repeating "Skills own their own data — credential paths..." inline, say "Follow the skill design principles (see `references/skill-design.md`)"
4. Verify the deduplication was clean — re-read the affected section

**Why this exists:** During the 14 May 2026 consolidation session, 2 near-verbatim principle duplicates were found in `system-architect/SKILL.md` after absorbing `skill-design.md` into its references. The duplicates pre-existed the move but were only caught because the user asked "did you check for duplication?"

## Enforcement

The system-architect skill's **pre-flight checklist** includes a Deduplication Check step (item 1.4):

> **Deduplication check:** Does this information already live somewhere else?
> If yes, update the ONE source of truth — other files should POINT to it, not copy it.

The **post-flight checklist** also now includes:

> **Duplication verified?** — If I absorbed content into a skill, I searched the target for near-verbatim matches and resolved any found.

## What This Prevents

- A cron schedule change updating jobs.json but forgetting profiles-crons.md (old pattern: 2 docs)
- A new skill hardcoding "daily 7am BST" instead of saying "the morning-briefing cron" (old pattern: 5 skills)
- A reference doc from May saying scripts live at `/opt/data/home/kanban/` when they moved to `/opt/data/scripts/` (old pattern: 3 docs never updated)
- A row count in the drift anchor being 16 when the real count is 59 (old pattern: always stale)
- Content duplicated in a skill's body when the same rules are absorbed into its references (new pattern: post-consolidation check catches it)