---
name: kanban-crud
description: "Companion reference for the kanban plugin — validation rules, deadline ordering, dependency chains, pitfalls, and kanban-first reading/writing discipline. Load when creating or updating tasks that need careful setup."
annotation: "Kanban CRUD: validation rules, deadline ordering, naming"
version: 1.7.0
---

# Kanban CRUD — Companion Reference

Companion reference for the consolidated `kanban` tool (plugin). The tool handles execution; this reference covers the **rules, pitfalls, and patterns** it doesn't know about.

## When to Load

Load this skill when you need the rules:
- **Creating a task** with deadlines, parent links, or complex setup → check validation rules + deadline ordering first
- **Deleting a task** → check pre-deletion data migration rules
- **Kanban state divergence** → check kanban-first reading/writing discipline
- **Dispatcher not picking up a task** → check pending vs ready rules

For simple operations (list, get, update status, add comment), just call the tool directly.

---

## ⚠️ Kanban-First Reading — always check kanban before asking, digging, or acting on files

When the user mentions a project, workstream, or task — or when you're about to ask the user a basic context question about one (e.g. "what's the occasion?" or "what date?" or "what theme?") — check the kanban first with `kanban(action="list", active=True, format="table")` or `kanban(action="get", task_id="...")`. 

**This also applies before printing, emailing, scanning, or otherwise acting on any file that may belong to a workstream.** The kanban task body is the designated source of truth not just for status and next steps, but also for exact file paths. Before touching any file associated with a task, `kanban(action="get", task_id="...")` to check the body for the correct managed location.

NOT session_search, file inspection, email search, raw `/nebula/Documents/` spelunking, or asking the user first. Only go deeper (session_search, inbox, files, or asking the user) AFTER reading the kanban and finding it incomplete or stale.

**Common anti-pattern:** User says "let's work on the baby shower" → agent asks "what's the occasion?" → user corrects: "you already have the details on kanban." The answer was in the kanban body. Check there first before asking.

**When kanban body contradicts reality:** If the kanban says "at Step 2" but an appointment is booked (which requires submission), flag the inconsistency rather than reporting the kanban's stale data. The appointment is the stronger signal.

## ⚠️ Kanban-First Writing — update kanban BEFORE files on status changes

When the user reports a status change on an active workstream (offer rejected, deal dead, new development, phase completed), update the kanban task FIRST — before touching any memory/reference files. The kanban body is the source of truth for task state. Memory files hold reference data only (features, comps, financials, contacts) and should never duplicate kanban state.

**Pattern:** User says "X happened" → `kanban(action="update", task_id="...", status="...", body="...")` + `kanban(action="comment", task_id="...", text="...")` → THEN sync memory files if there's durable reference data to add or remove.

**Memory file rule:** If a memory file has a "Status:" line or progress tracker checklist, that's task-state contamination. Strip it — the kanban owns that now. See `references/kanban-memory-boundary.md`.

## ⚠️ Pitfall — `pending` tasks are NOT auto-dispatched

The gateway's embedded dispatcher scans for `ready` tasks every 60 seconds. Tasks with status `pending` are **never picked up** — they sit indefinitely with no worker spawned.

- `pending` — Needs manual triage; no worker should touch it yet
- `ready` — Ready for a specialist profile worker to claim and process
- `todo` — Blocked by dependencies (auto-promotes to `ready` when all parents complete)

**Common mistake:** Creating tasks for specialist profiles (ca-expert, home-manager, inventory-manager) with status `pending`. The dispatcher ignores them. Always pass `status="ready"` when the task should be auto-processed.

## ⚠️ Pitfall — Profile Worker Startup Failures

A task can be `ready` and the dispatcher will claim it, but the worker fails on spawn from:

**Cause 1 — skill name collision.** A profile-local copy of `kanban-worker` under its profile skills dir conflicts with the global one. Fix: remove the profile-local copy.

**Cause 2 — HOME / environment mismatch.** The gateway runs with `HOME=/opt/data`, workers inherit this. Scripts using `~` resolution (e.g. `pass` for credentials) may look in the wrong directory. Fix: pin `PASSWORD_STORE_DIR` and `GNUPGHOME` explicitly.

**Diagnosis pattern:**
1. `kanban(action="events", task_id="...")` for crash pattern
2. Check worker log at `/opt/data/kanban/logs/<task_id>.log`
3. Check `last_failure_error` on the task
4. Check profile's `agent.log`

## ⚠️ Pitfall — Raw SQL in Cron Scripts

The heartbeat and other cron scripts MUST use `kanban(action="list", ...)` or the kanban.py CLI, never raw `sqlite3` queries. Raw SQL:
- Bypasses validation (title rules, status constraints)
- Creates hex-blob IDs instead of readable `t_verb_noun` IDs
- Defeats the single-purpose interface

**Exception — bulk seeding:** When you need to update 3+ records with the same pattern (e.g. `SET last_heartbeat_at = created_at WHERE last_heartbeat_at IS NULL`), raw SQL is the practical choice because kanban.py has no batch update. Flag the trade-off and explain why.

## Validation Rules

- **Title** — must be verb+noun workstream (rejects micro-steps: `"1. check X"`, `"remind me about Y"`, `"check the status"`)
- **Two-word guard** — `< 3 words` rejected as micro-step. "Buy house" (2 words) triggers it. "Buy a new house" (4 words) passes.
- **Case-sensitivity gap in prohibited patterns** — `PROHIBITED_TITLE_PATTERNS` use lowercase regex without `re.IGNORECASE`. A title like `"Follow up Gudiben contact"` (capital F) passes the pattern guard (the word-count guard catches very short ones, but 4+-word titles can slip through via title case).
- **Status** — must be one of: pending, in_progress, completed, cancelled, blocked, ready, todo, done
- **Assignee** — must be a known profile (joy, researcher, analyst, writer, etc.)
- **Workspace** — must be scratch, worktree, or dir:\<path\>
- **IDs** — auto-generated from title as `t_verb_noun`, deduped with `_2`, `_3` suffix

## ⚠️ Pitfall — Deleting a task with deadline/appointment orphans the date

When you delete a task that carries a deadline or appointment reference, that date silently falls out of structured data. It might survive in a prose note, but structured queries will never find it again.

**Example (8 Jun 2026):** `t_apply_priyanka_schengen` was deleted, but its TLScontact appointment (16 Jun 13:00) was never migrated. The morning briefing saw empty calendar + no kanban task → missed the appointment entirely.

**Rule — pre-deletion data migration:**
1. Does the task body contain a date, appointment, or deadline that still matters?
2. If yes: add it to the calendar OR create a successor task with the date in the body BEFORE deleting.
3. If the info is already tracked elsewhere, verify it's actually findable — not just a prose note.
4. Only then delete.

## Board Audit & Cleanup

Periodic task pruning prevents the kanban dump from bloating cron context (heartbeat watchdog, morning briefing). Run quarterly, or as-needed when context exceeds ~8k tokens.

1. **List all active tasks:** `kanban(action="list", active=True, format="table")`

2. **Categorise each task into one of:**
   - **Core workstream** — active, ongoing, will receive future inbound (property sale, visa, family events, active projects). → Keep.
   - **One-shot notification / review** — security alert, password reset, single response to review, lead to evaluate. These exist to track a single notification already seen. → Delete after verifying completeness at step 3.
   - **Back-office** — assignee is ca-expert or legal-expert, no expected inbound from WhatsApp/email. → Delete unless it is actively blocking a core workstream.
   - **Duplicate / ghost** — two tasks with the same title. → Keep one, delete the other.

3. **For each candidate-for-deletion:** Check the task body for any date, appointment, or deadline that still matters (per the pre-deletion data migration rule above). Migrate to calendar or successor task before deleting.

4. **Delete in bulk:** `kanban(action="delete", task_id="t_<id>")` — one call per task (no batch endpoint).

5. **Verify the board is manageable:** Target ≤15 active tasks. If still bloated, repeat from step 2 with a tighter filter.

## Dependency Chains (Parent→Child)

Tasks can form parent→child dependency chains. When all parents of a child reach `completed` or `done`, the child auto-promotes from `todo` → `ready`.

- `create` with `parent` param → creates child at `todo`, auto-promotes when parent completes
- `link` action → connects two existing tasks with same auto-promotion
- Multi-parent chains: child stays in `todo` until ALL parents complete

**When the validator rejects a task creation (cron/heartbeat context):** If `kanban.py add` exits with validation errors (micro-step rejection, bad status, unknown assignee), the item IS NOT a task. Do NOT retry with a different title or rename to bypass validation. Accept the rejection — the item belongs nowhere on the board.

### ⚠️ Deadline ordering in dependency chains

When task A must happen before task B (parent→child or logically sequential), B's deadline MUST be *after* A's deadline. Otherwise the chronology is inverted.

**Rule:**
1. List all tasks in the workstream
2. Sort by logical dependency order (what feeds into what)
3. Assign deadlines in ascending chronological order that respects that sequence
4. Double-check: no task's deadline is earlier than the task it depends on

Applies to sibling tasks under a parent too — even without explicit `--parent` linkage, if A logically feeds into B, A's deadline ≤ B's deadline.

## Follow-Up Cadence at Task Creation

When creating a task that involves waiting on an external party — email sent awaiting response, application submitted, quote requested — encode the follow-up rhythm at creation time:

1. **Set a deadline** matching the expected response window (3-5 working days for email)
2. **Note the expected response time** in the body — e.g. "Emailed Encore 8 Jun, expected response 3-5 days"
3. **State the fallback action** — what to do if the window passes (e.g. "follow up if no response by 13 Jun")

For tasks with no external dependency (research, design, personal action items), set deadlines based on the work itself.

## Body Opening Convention

The heartbeat reads `substr(body, 1, 80)` for workstream matching. Bodies MUST start with a one-line description of what the task is, not metadata headers:

**Bad:** `## Status: Active\nYopa NSNF-flexi...`
**Good:** `Yopa NSNF-flexi. Live on Rightmove since 28 May 2026.`

The tool checks for noise patterns (`## Status:`, `# TODO:`, `## Progress:`) and warns.

## ⚠️ Body Truncation in List/JSON Output

When consuming kanban data via `kanban list --format json` or `kanban list --format table`, task bodies are **truncated to ~80 characters**. This affects any data-collection script that parses the JSON output — the full body is not available from the list endpoint.

**Common failure mode:** A morning briefing data script injects `kanban list --active --format json | tail -N` into the prompt context. The LLM sees truncated bodies and reports "no offers on Flat 901" because the offer details are deeper in the body. The full body IS correct — it's the list output that truncates.

**Fix options (pick one):**
1. Call `kanban get <task-id>` for priority tasks to retrieve the full body
2. Use `kanban list --format table` (text, truncated) and augment with full-body get calls
3. Pipe the JSON through a Python script that reads full bodies from the kanban DB directly

## Architecture Note — What "Kanban" Means Here

This is a **task tracker with visual status**, not a true kanban system. The classic kanban philosophy (Toyota/Lean) enforces pull systems, WIP limits, and flow metrics — none of which apply here because a single AI assistant tracks many `in_progress` tasks without context-switching cost.

See `references/kanban-vs-task-tracker.md` for the full architectural distinction.

## References

- `references/kanban-memory-boundary.md` — What belongs in kanban vs memory tree. Single-source-of-truth principle, contamination detection, and cleanup procedure.
- `references/kanban-vs-task-tracker.md` — Architectural distinction: what our "kanban" is vs classic kanban practice.
- `references/debugging-missing-tasks.md` — Protocol for when the user insists a task exists but the tool can't find it. Covers DB corruption, session-history tracing, git forensics, and orphaned-data cross-referencing.
