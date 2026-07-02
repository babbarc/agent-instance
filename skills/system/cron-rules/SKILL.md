---
name: cron-rules
description: "Cron fundamentals hub — immutable laws, delivery mechanics, hygiene, cross-cron architecture, and pitfalls. Routes to sub-skills for focused tasks. Load when running or modifying cron jobs."
annotation: "Cron fundamentals hub: laws, delivery, hygiene, routing"
version: 4.0.0
metadata:
  hermes:
    tags: [cron, execution, delivery, automation]
    related_skills: [life-audit, cron-prompt-design, cron-script-design, cron-debugging]
    merged_from: ea-cron-execution (2026-06-04)
---

# Cron Execution

> Load when running cron jobs or writing/modifying cron prompts. Not for normal chat sessions.
>
> **Routing — load the right sub-skill for your task:**
> - **cron-prompt-design** — when writing or editing a cron job prompt (boundaries, scratchpad, output rules)
> - **cron-script-design** — when writing a data-collection script or no_agent cron job
> - **cron-debugging** — when a cron job misbehaves or needs health audit
>
> This hub covers cron fundamentals, delivery mechanics, and hygiene rules.
> See each sub-skill's SKILL.md for focused procedures.

## Immutable Laws

Two hard rules that every cron must obey. No exceptions.

### Law 1: Cron NEVER debugs — but distinguish critical vs supplementary failures

If a **primary data source** fails (the data the cron exists to monitor), fail the entire run. The script exits non-zero, the scheduler records `last_status: error`, and the cursor doesn't advance.

If a **supplementary data source** fails (calendar, kanban list — nice-to-have context), report it tersely and move on. No investigation, no fallback, no retry.

**The critical/supplementary distinction lives in the data-collection script, not the LLM prompt.** The script should use `set -euo pipefail` so primary-source pipelines that fail (no `||` fallback) cause a non-zero exit. Supplementary sources keep their `|| echo` fallback.

**What a cron never does:** run fallback scripts, check logs, repair auth, retry with different params, create kanban tasks about failures, patch skills.

### Law 2: Cron NEVER patches skills

A cron must never call `skill_manage`, `write_file` into a skill directory, or modify behavioral configuration.

**If a cron discovers something worth capturing:** log the observation in the output. A maintainer session picks it up. The cron does not self-modify.

## Action-First Delivery

When running as a cron, your last message IS the deliverable.

**Critical frame: The LLM must execute routing actions FIRST, then produce the summary.**

**Hidden overrider: The scheduler preamble.** Every cron gets this preamble: "Just produce your report/output as your final response and the system handles the rest." Counter it by opening with a strong action directive using `terminal("...")` format and including "MUST call terminal()" in the first rule.

- **Frame matters.** "Execute actions, then report" beats "write a report."
- **Last message must contain the deliverable.** Intermediate outputs are scaffolding.
- **Do everything first, then compose.** Complete all tool calls, then produce output.
- **`[SILENT]`** is the only case where no content is correct.
- **Zero tool calls IS valid** when there's nothing to route.

## Cron Hygiene

### One Job, One Purpose

If two crons cover the same job, kill the redundant one. Keep the LLM-driven cron; kill the no_agent script cron if it just lists filenames the LLM cron should process.

**Always `cronjob action=list` before making changes.**

### Separate Concerns Within a Cron

A task should be its own cron when it meets ALL of: silent/no user output, different cadence, different toolset, no cross-source context dependency.

**Why this matters:** Token cost, toolset overhead, decision quality. A 1,200-char enrichment section running 9x/day saves tokens when split to 2x/day.

**When NOT to split:** Concerns that share context, must execute atomically, or cost more to split than to keep.

### Pre-Flight Checklist

Before modifying any cron job, load `system-architect` for structural governance.

Key rules:
- NEVER edit cron/jobs.json or config.yaml directly — use `cronjob` tool or `hermes config set`
- `hermes config set` cannot create YAML list values — see `system-architect/references/hermes-config-cli-limitations.md` for the fallback if the CLI can't express the needed config shape
- Scope updates to ONLY the fields that need to change
- Verify the job_id matches the intended cron before calling update
- Update the snapshot file immediately after every prompt change
- After any fix: scan ALL crons for the same pattern (cross-cron systemic scan)

See `system-architect` for the complete pre-flight procedure (Step 0).

### Per-Job Model Override

Routine cron jobs (heartbeat, data collection, structured triage) do NOT need extended reasoning. When `config.yaml` sets `agent.reasoning_effort: xhigh`, crons inherit extended thinking, causing TTFT >120s during peak hours.

**Quick decision:**
- Routine/scoring triage → Override needed (faster, cheaper)
- Open-ended analysis → Keep global config

**Options:**
- **A** — Set `reasoning_effort: none` in config.yaml (all sessions, simplest)
- **B** — Set `reasoning_effort: low/medium` in config.yaml (balanced)
- **C** — Create profile-based isolation (mixed workloads, see `cron-debugging`)

## Per-Profile Cron Workers

When a cron job needs a different profile's config, .env, skills, or credentials than the default gateway, run a separate gateway per profile — each gateway has its own in-process cron ticker, isolated HERMES_HOME, and process boundary. Do NOT patch the cron scheduler's `run_one_job()` to do in-process profile switching.

### Decision tree: should a job run under a dedicated profile gateway?

1. Does the job need a different model, API key, or skill set than the default profile?
   - YES → proceed to step 2
   - NO → keep the job in the default profile's cron; do not create a profile gateway

2. Does the target profile gateway already exist and run? Check: `hermes profile show <name>` shows `Gateway: running`
   - YES → skip to step 5
   - NO → proceed to step 3

3. Start the target profile's gateway:
   - **Host with systemd:** `hermes -p <name> gateway install` then `hermes -p <name> gateway start`
   - **Host without systemd (tmux):** `tmux new -s <name> -d 'hermes -p <name> gateway run'`
   - **Container (s6):** `hermes -p <name> profile create --gateway` — the boot reconciler (`02-reconcile-profiles`) auto-starts it on next boot. Verify: `docker exec <c> /command/s6-svstat /run/service/gateway-<name>`

4. Verify the gateway started: `hermes profile show <name>` — expect `Gateway: running`

5. Create the cron job under the target profile's own cron store:
   ```
   hermes -p <name> cron create '<schedule>' \
     --prompt '<self-contained prompt>' \
     --deliver '<platform>:<chat_id>' \
     --name '<job-name>'
   ```
   The job is stored in the profile's `cron/jobs.json` and fired by its own ticker.

### What NOT to do

- Do NOT patch `cron/scheduler.py::run_one_job()` to switch HERMES_HOME via ContextVar — this is architecturally unsound (see `references/profile-worker-arch.md`):
  - `os.environ` is process-global. Subprocesses (agent sessions) see the wrong HERMES_HOME.
  - Job scheduling state reads from one profile's `cron/jobs.json` but mark_job_run/advance_next_run writes to another → infinite-refire or lost-state bug.
  - `.tick.lock` resolves from the gateway's profile. A separately-running profile gateway and the patched gateway share no lock → double execution.
  - `except Exception` fallback during profile resolution silently runs the job under the gateway's own profile → security boundary violation.
- Do NOT share a single `cron/jobs.json` across profiles. Each gateway owns its own cron store.

## Cross-Cron Data Pipeline

Crons can share data through the life-tracking DB. One cron writes to `life_signals`; a later cron reads and builds on it.

**Rules:**
1. Writer cron must commit >=1h before reader cron fires (avoid race condition)
2. Reader must gracefully handle "no signal yet" — default to independent assessment
3. Reader should cross-reference, not delegate
4. Document dependency in both cron prompts
5. **Only the designated collector cron calls the external API.** All other crons read from DB.

## Pitfalls

39 known failure modes for cron jobs. See `references/pitfalls.md` for the full list with diagnosis and fix steps.

## References

- `references/api-collector-pattern.md`
- `references/calendar-creation-from-triage.md`
- `references/context-scope-demarcation.md`
- `references/conversation-grouping-pattern.md`
- `references/diagnosing-zero-tool-calls.md`
- `references/email-triage-scoring-checklist.md`
- `references/google-contacts-phone-fallback.md`
- `references/heartbeat-cursor-migration.md`
- `references/intent-based-email-classification.md`
- `references/jobset-recovery.md`
- `references/pitfalls.md` — 39 known cron failure modes with diagnosis and fixes
- `references/profile-worker-arch.md` — Per-profile cron worker architecture: why not to patch the scheduler; correct gateway-per-profile approach; Telegram delivery for worker profiles (adapter lock + standalone path); job migration checklist (env/skill/script parity, deliver conversion, sequencing)
- `references/routing-flow-bc-vs-d.md`
- `references/routing-flow-transient-items.md` — Distinguishing transient/one-shot items from durable workstreams
- `references/routing-table-authority.md`
- `references/violation-pattern-snapshot-mirror.md`
- `references/whatsapp-lid-resolution.md` — Fix for WhatsApp LID-based JID resolution
- `references/windowing-buffer-overlap.md`
