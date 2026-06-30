---
name: cron-prompt-design
description: "Design and structure cron job prompts — prompt boundaries, output format rules, scratchpad authoring, and style conventions. Load when writing or editing a cron job prompt."
annotation: "Cron prompt authoring: boundaries, scratchpad, output rules"
version: 1.0.0
metadata:
  hermes:
    related_skills: [cron-rules, cron-script-design, cron-debugging]
---

# Cron Prompt Design

> Load when writing or editing a cron job prompt. Not for normal chat sessions.

## Procedural Steps

### 1. Define Prompt Body Boundaries

The stored cron prompt must contain ONLY the instruction body — from the instruction-start marker onward. Do NOT include scheduler-managed headers.

**The scheduler prepends at runtime:**
- `[IMPORTANT: ...]` — delivery mode enforcement
- `## Script Output` — data injection section with ``` markers

**Test:** Run `cronjob action=list` after update. The `prompt_preview` field should show your instruction body starting from the first meaningful instruction.

### 2. Choose Self-Contained vs Skill-Dependent

**Prefer self-contained prompts** (all rules/commands inlined, zero skills loaded). Every loaded skill is 5-20KB of context overhead.

- Self-contained → No skill dependencies. Prompt makes sense in isolation.
- Skill-dependent → Load `cron-rules` hub skill for sub-skill routing.

**Embedded rule beats loaded skill.** If the prompt needs one rule from a skill, inline that rule.

**Format delegation — CLI owns format, not the prompt.** When a cron calls a CLI tool that writes formatted data (e.g. `people enrich` prepends date + dashes), the prompt must NOT duplicate the format specification. The CLI is the single source of truth for output format. The prompt provides content; the CLI formats it.

Test: if the same format string appears in both the prompt text AND the CLI tool's code/help text, one of them will drift. Remove it from the prompt.

Past failure (Jun 2026): heartbeat v40 prompt specified `<current-date>: observation` but `people enrich` auto-prepends `- <today-date>: `. The prompt's Format: line and the CLI's output diverged, causing 14 orphaned notes invisible to the weekly sweep.

### 3. Enforce Procedural-Only Content

Cron prompts must contain only procedural instructions: decision logic, output format rules, and data references. Do NOT embed personal facts.

**Where facts belong instead:** Injected via the pre-run data script's output sections, user profile/memory tree, or contact records.

### 4. Write in Structured Procedural Prose (Never Pseudocode)

Do NOT convert prompts to pseudocode (IF/ELSE IF gates, SCORE = sum() formulas, FOR EACH loops). Write numbered steps, scoring tables, and clear branching in natural language.

### 5. Add a Short-Circuit Gate

Place the short-circuit gate immediately after data collection, before any decision-making logic. If no data to process, output `[SILENT]` and stop.

**Covers both patterns:** When data scripts output JSON via CLI wrappers (life-track.py --json), an empty array `[]` is also a no-data signal — enumerate it alongside `(no data)` in the gate:

```
If ALL injected sections show "(no data)" or empty "[]", output exactly [SILENT] and stop.
```

See `references/data-script-json-output-boundary.md` for model-specific guardrails when mixing JSON and text fallback outputs.

### 6. Scope Data Windows to Cron Frequency

- **Daily/weekly crons** — can look ahead 7-14 days
- **High-frequency crons (every 2h or less)** — scope window to the next run interval

### 7. Design the Output Format Block

Consolidate all output format rules into one compact block at the end of the prompt:

```
- FIRST CHARACTER: 🔴, 🟡, 🔵, -, *, or [ (for [SILENT]).
- NO SCRATCHPAD: Do not output any planning, phase notes, or internal reasoning.
- [SILENT]: Output exactly "[SILENT]" and nothing else if nothing to report.
- BASH SAFETY: Use single quotes around summary strings. No apostrophes ($, `, ") in summaries.
- Address the user as "you".
- After the digest, stop. No additional commentary.
```

**Action-First Delivery:** Open with a strong action directive. Use `terminal("...")` format. Include "MUST call terminal()" in the first rule to counter the scheduler preamble's "just produce your report" bias. A `## Post-Step` that runs terminal() after composing output is an anti-pattern — move those side-effects to the data script instead. See `references/scheduler-preamble-override.md` and `references/post-step-ordering.md`.

### 8. Use Output Templates Instead of Scratchpad XML Tags

When the cron needs structured reasoning before executing, use this pattern (NOT XML `<scratchpad>` tags):

**Step A — Silent Planning Instructions:**
```
## PLAN BEFORE ACTING (think silently — never write this down)
Think through these steps internally:
1. Score each item using the rubrics below
2. Dedup across channels
3. Decide routing actions
4. Execute terminal() commands
5. Output ONLY the template below
```

**Step B — Explicit Output Templates:** Show the ONLY acceptable output shapes:
```
## YOUR RESPONSE RULES
Your entire response is ONE of these patterns:
**Pattern A — terminal() then summary:**
terminal("...command 1...")
🔴 Urgent item description

**Pattern B — summary only:**
🔴 Urgent item description

**Pattern C — silent:** [SILENT]
```

**Step C — First-Character Constraint:** The model's first character must be one of: t (for terminal), 🔴, 🟡, 🔵, or [ (for [SILENT]).

### 9. Decide: Suppression vs Output-First Inversion

| Factor | Suppression (Steps 8A+B+C) | Output-First Inversion |
|--------|---------------------------|----------------------|
| Model compatibility | DeepSeek, most models | Models that can't plan silently |
| Failure mode | Planning text in output | Truncated but valid summary |
| Complexity | 3 changes applied together | 1 structural change |
| When to use | Model follows "think silently" | Model leaks planning despite suppression |

**Output-First Inversion alternative:**
```
## YOUR RESPONSE
First, output terminal() calls (if any), then the emoji-bullet summary.
After the summary, you may add reasoning on a line starting with WHY:
This reasoning is optional — the summary is the deliverable.
```

### 10. Every Prompt Section Must Justify Its Existence

Before adding a section, step, or action block to a cron prompt, ask:

1. Does this section produce output a human or downstream cron consumes?
2. Does this action write data that has a verifiable downstream reader?
3. If the answer to both is "no" or "for traceability" — remove it.

Signals with no reader, steps that duplicate what the data script already collects, and action blocks that copy data between tables (LLM-mediated table sync) are all noise. A cron's `last_run_at` and `last_status` fields already prove execution — signals that replicate this information have no purpose.

### 11. Verify Before Finishing

1. Would the response make sense without tool blocks?
2. Run `cronjob action=list` — verify `prompt_preview` starts with your instruction body.
3. **Snapshot fidelity check** — After any prompt content change: update the prompt in `jobs.json` FIRST via `cronjob action='update'`, THEN update the snapshot file (if one exists) to match. The snapshot must never diverge from the live prompt — a stale snapshot is worse than no snapshot because you'll trust it and miss the real prompt state. Update the snapshot `Last updated` date to reflect the change.

   Common failure mode: updating the snapshot metadata line ("removed step 2") but never touching the actual stored prompt. Next session loads the snapshot and assumes the dead step is gone — but it's still running every morning.
4. **Verify the prompt persisted in jobs.json** — After `cronjob action='update'`, check the returned `prompt_preview` field or re-read `jobs.json` to confirm the change actually took. Snapshot metadata being correct but the live `jobs.json` prompt being stale is the most common cron-editing failure. The API returns success even when the prompt body hasn't changed — you must verify content, not just status.
5. **Toolset cleanup** — After removing ALL terminal() calls from a cron prompt, clear `enabled_toolsets` by passing `enabled_toolsets=[]` in the `cronjob action='update'` call. A cron with zero tool calls should not load any tools — every unused toolset adds token overhead on each run.
6. After a scratchpad fix: let a full scheduled run complete, check output for planning text.

7. **Data-script → prompt coherence check** — After ANY change to a cron's data script, audit whether the prompt's Actions section, step references, or terminal() calls are still valid. The data script may now handle functionality that the prompt still tries to do via terminal() — the drift is invisible until a session catches the cron in action.

   The failure pattern: you edit `*-data.sh` (adding a new data section, removing a stale API call, absorbing a DB write), update the snapshot, and declare victory. But the stored cron prompt in `jobs.json` still has the old terminal() step. Next morning's run wastes tokens executing a redundant step or, worse, calls a script the data collector now supersedes. See `references/divergent-snapshot-recovery.md` for the full pitfall table.

## References

- `references/output-template-pattern.md` — Output template design, silent planning, first-character constraints
- `references/cron-prompt-assessment.md` — Checklist for reviewing an existing cron prompt
- `references/scheduler-preamble-override.md` — How to counter the scheduler preamble's hidden override
- `references/post-step-ordering.md` — The post-step terminal() anti-pattern: why "compose, then tool, then output" fails in the agent loop, and how to move side-effects to the data script
- `references/data-script-json-output-boundary.md` — Handling `[]` from JSON-output CLI tools in the short-circuit gate, model-specific guardrails for DeepSeek
