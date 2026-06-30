---
name: system-architect
description: "Governance for structural changes. Load before modifying cron jobs, profiles, DB schemas, memory tree, or system equilibrium."
annotation: "Structural changes: cron, profiles, DB, memory — load first"
version: 2.1.0
metadata:
  hermes:
    tags: [architecture, governance, system-design]
    related_skills: [ea-domain-routing, hermes-patching, hermes-maintainer]
---

# System Architect — Structural Governance

> **Load before:** modifying cron jobs, creating/deleting profiles, changing data flows (DB, API, tool), editing `$HERMES_HOME/memory/` or SOUL.md, auditing equilibrium. When in doubt: load anyway.

---

## Pre-Flight Checklist

> **Must-fire rule: Step 0 is mandatory before any structural change.**

### Step 0 — Present Findings, Await Approval

Before touching ANY file, config, cron, or data source:

1. **Load this skill** — `skill_view('system-architect')`. The governance rules only help if they're in context.
2. **Load cron-rules** — If the change touches cron jobs, `skill_view('cron-rules')` for fundamentals, plus the relevant sub-skill based on task (`cron-prompt-design`, `cron-script-design`, or `cron-debugging`).
3. **Present, don't act** — Output a terse summary of: (a) what you found, (b) what you propose to change, and (c) the exact tool/wrapper you will use. Wait for explicit go-ahead. "Do not fix! show me your findings first" is the rule — not a preference.
4. **Use wrapper tools** — See the Wrapper-First Policy table below. If the wrapper tool exists, use it. If it doesn't exist for the specific operation, say so and propose using `execute_code` with Python's `json` module (not `patch` with raw-text matching on multi-KB JSON).
5. **If the wrapper produces an unexpected result** (e.g. `cronjob action=run` doesn't create an output file), stop and investigate. Do NOT switch to direct file editing as a workaround — that bypasses the scheduler's state management and causes silent failures.

**Consequence of skipping Step 0:** See `references/consequence-of-direct-edit.md` for what happens when wrapper tools are bypassed.

**Step 0a — Rollback source priority for cron jobs:**

When reverting or recovering cron jobs, use curator backups in this order — NOT ad-hoc `.bak` files or random backups:

1. **Curator snapshots** — `ls /opt/data/skills/.curator_backups/ | sort` . These are dated, clean JSON dumps taken by the curator cron job. Pick the most recent one **before** the corruption point.
2. **Git-versioned snapshot files** — For individual prompt restoration, `git log -- memory/reference/<jobname>-prompt-snapshot.md` provides the prompt version at each commit. Use `git show <hash>:memory/reference/...` to extract a specific version.
3. **Cron output file headers** — `/opt/data/cron/output/<jobid>/<timestamp>.md` contains the full prompt text in the header. Use only as last resort — these are archives of what *ran*, not necessarily the intentional config state.

**Never** use `/opt/data/cron/jobs.json.bak` for restoration — it's a stale snapshot created by a different mechanism, not by the curator.

**Step 0b — Cross-reference against snapshot files before any cron prompt edit:**

Before modifying ANY cron job prompt:
1. Check `memory/reference/<jobname>-prompt-snapshot.md` on disk — this contains the current curated prompt with version history
2. Run `git diff -- memory/reference/<jobname>-prompt-snapshot.md` to verify the disk version matches the latest committed version. If they differ, the snapshot hasn't been committed yet — flag this.
3. Only proceed after verifying the snapshot is the intended source of truth.

### Step 0d — Use Claude Opus for complex code analysis, not Gemini/DeepSeek

When the user asks you to get an expert code review or analysis from an LLM:

1. **Use `claude_code` with model='opus'** — NOT `gemini_web`, NOT `delegate_task` (which defaults to the session's provider, usually DeepSeek)
2. If opus is unavailable (auth failure 401, timeout, "Unknown error"), **diagnose before retrying** — do NOT loop 4+ times with identical arguments. Check:
   - `claude auth status` — if it returns `loggedIn: true`, the credentials are valid but the tool may still fail due to **environment mismatch**. Check whether `HOME` in the gateway process differs from the terminal:
     1. `cat /proc/<gateway-pid>/environ | tr '\0' '\n' | grep '^HOME='` — compare against `echo $HOME` in your terminal.
     2. `HOME=$WRONG_HOME claude -p "hi" --output-format json` — reproduces the failure; the correct `HOME` produces success. The CLI reads credentials from `$HOME/.claude/`.
     3. Fix: patch the plugin to set `env["HOME"] = "/opt/data/home"` in the subprocess env dict.
   - If `claude auth status` also fails (not just the tool), check `claude status` or `claude credits` — a persistent 401 may indicate an expired token.
   - `cat ~/.claude/.credentials.json` — check the `expiresAt` field (milliseconds epoch). Convert: `python3 -c "import datetime; print(datetime.datetime.fromtimestamp(<expiresAt>/1000))"`
   - If the token IS expired: report "Claude Code auth token expired on <date>. Needs `claude login` (interactive browser OAuth) or setting ANTHROPIC_API_KEY in the environment." Stop — do not retry, do not silently substitute.
   - If credentials missing entirely: report "Claude Code not configured. Needs `claude login` first."
   - **Never delete or rename `.credentials.json` based on a single 401.** The file IS the auth source — removing it breaks authentication entirely.
3. Keep the task goal focused — full context, minimal tool permissions (Read only for analysis), short max_turns (1-3 for review, not production code)
4. **Before iterating** on a failing claude_code call, check the auth state first. Do not retry without first understanding why the previous attempt failed.

When a system tool displays state that seems wrong (e.g. `cronjob list` shows `last_run_at=10:02` but you expect a more recent run), DO NOT report it as a failure immediately. The display may lag behind actual state. Instead:

1. Check the raw data source — for cron output files: `ls -lt /opt/data/cron/output/<jobid>/ | head -5`
2. For config: read the JSON directly with `python3 -c "import json; ..."`
3. Compare display state against raw data before reporting anything to the user
4. If the raw data looks current but the display doesn't, the scheduler is running fine — the display refresh may be deferred. Do NOT attempt to force-run or restart jobs based on stale display state.

### Checklist (run after Step 0 approval)

1. **Purpose** — What domain? Is there an existing mechanism? Is a simpler alternative possible? Is the target a learned skill (editable) or installed skill (/opt/hermes/ — report, don't patch)? For tools: is it user-created (check `/opt/data/plugins/` + `plugins.enabled` in config) or built-in? See `references/tool-origin-verification.md`.

2. **Hermes-native investigation** — If the structural change touches Hermes' own behavior (skill loading, sync mechanism, profile seeding, config flags, DB schemas, environment handling): load `skill_view('hermes-agent')` first. The hermes-agent skill is the authoritative reference for how the system works — it covers the sync pipeline, CLI commands, config sections, paths, profiles, platforms. After reading it, trace the actual code path (grep for relevant function/class names mentioned in the skill) before drawing conclusions about system architecture. Do not assume, guess, or make config changes based on partial reads of the codebase — the hermes-agent skill or its reference files will often have the definitive answer.

   **Skill-divergence sub-investigation** — When the user points out that a skill at `HERMES_HOME/skills/` differs from its bundled upstream (`/opt/hermes/skills/` or `/opt/hermes/optional-skills/`), diagnose before proposing any fix:

   a. **Check the manifest** — Read `.bundled_manifest` in the skills directory. Is the skill name listed? If no, the skill was never synced from bundled — it's user-created, hub-installed, or from optional-skills (not auto-synced). If yes, note the recorded hash.

   b. **Determine modification state** — Diff the user's SKILL.md against the upstream version. The sync only updates skills where user hash matches origin hash. Divergence means the sync correctly respects modifications — the change was intentional or the sync never tracked it.

   c. **Identify the source** — Does a bundled version exist at `/opt/hermes/skills/`? An optional version at `/opt/hermes/optional-skills/`? Or was the skill created entirely by the user (no upstream)?

   d. **Propose, don't act** — Present findings (manifest state, divergence details, source). Only make changes after explicit direction. The sync pipeline is the canonical bridge; do not work around it with config changes like `external_dirs` unless the user explicitly asks.
3. **Drift anchor** — Check relevant section in system-architecture.md. Update it after the change.
   - **Verify anchor claims against code** — The anchor can be stale or inaccurate. Don't trust it implicitly. Trace key claims to their implementation source: "Which function? Show me the actual code." If the code doesn't match the doc, the doc is wrong — fix it, don't assume the doc is right.
3. **Plan minimum change** — Sketch the minimal fix before implementing. One function, one condition, one fallback path. If touching infrastructure, stop — fix the script logic instead. Present the plan for approval.
4. **Data flow** — What data, from where, to where? Verify DB path on disk.
5. **Cache impact** — Tier 1 memory change? Follow Tier 1 Update Protocol (must ask explicit approval).
6. **Single source of truth** — Does this info already live elsewhere? If yes, update ONE file — others POINT to it. Skills reference components by NAME only, never by schedule/path/config value.
  — SOUL.md vs .hermes.md overlap: .hermes.md should carry only environment-specific overrides. If it repeats SOUL.md verbatim, remove the duplicate. If it adds concrete paths, strip the generic preamble.
6. **Hardcoded counts** — Never embed dynamic counts. Say "count varies — query filesystem."
7. **After the change** — Search ALL skills and docs for old values (stale refs). Verify cron job skills lists AND cron prompt text for old names.
8. **Outcome logged** — Write to intervention_log.
9. **QMD re-index** — Run after structural changes to memory tree.

### Wrapper-First Policy

Before touching ANY system file directly (cron/jobs.json, config.yaml, profiles/*/config.yaml, etc.), check for an existing wrapper CLI or tool:

| If touching... | Use wrapper | Never do | Recovery if corrupted |
|---|---|---|---|
| Cron jobs | `cronjob` tool (action=create/update/run) | Patch cron/jobs.json directly | Restore from curator_backups, then overlay snapshot prompts |
| Hermes config | `hermes config` CLI | sed/awk/patch on config.yaml | Restore from `.hermes/config.yaml.curator-backup` if curator is enabled |
| Skills | `skill_manage` | Direct write_file to skill dirs | `git checkout` from joy-brain.git |
| Kanban | `kanban` tool | SQLite on kanban.db directly | Restore from daily kanban.db backup |
| Contacts | `people` CLI or contact-specific tools | Direct edit of contact .md files when a structured tool exists | Restore from git (contacts/ is tracked) |

**Exception:** When all wrapper tools fail or don't exist for the specific operation, use `execute_code` with Python's json module (not `patch` with raw-text matching — that corrupts large JSON strings with escape sequences). Verify JSON validity after every write.

**If the wrapper approach works but yields a surprising result** (e.g. `cronjob run` doesn't produce an output file), stop and investigate — don't switch to direct file editing as a workaround. Direct file editing bypasses the scheduler's state management and can cause silent failures, duplicate runs, or profile resolution errors.

## Core Principles

### 1. SOUL First, Infrastructure Second
Identity → memory tree → infrastructure → build. Never construct tooling before defining operating principles.

### 2. Drift Anchor Is Procedural, Not Factual
System-architecture.md describes HOW the system works — behavior, connections, purpose. Never enumerate HOW MANY. Dynamic state is queried at runtime.

### 3. Single Source of Truth
- **MEMORY.md** (memory tool) — behavioral guardrails that must fire every turn
- **`$HERMES_HOME/memory/`** (write_file) — structured reference facts, domain-organized
- **Skills** (skill_manage) — procedures only, zero instance data

Skills reference system components by NAME only. No schedules, paths, or config values in skill bodies.

### 3b. Infrastructure Boundary

When a script or tool fails, fix the script logic — never manage containers, services, or infrastructure from within a tool script. `browser-proxy` handles Chrome lifecycle; scripts that need the browser navigate to a page and let the proxy handle the rest. See `references/trace-before-fix.md` for the full approach.

### 4. No Hard Mandates Without Safety Reason

Hard "never" prohibitions that force a specific tool path should only exist when the blocked action is genuinely unsafe (e.g., "never edit config.yaml directly" — breaks YAML structure; "never use pass show" — exposes secrets to LLM context).

For routing/source-of-truth choices, use directional language: "prefer Y for discovery; X works for known paths." Never "never do X, only do Y" when both paths are safe — that turns the identity document into a routing table that forces unnecessary indirection every turn.

**The indicator:** If you already know the exact path or value and the rule still forces you through a search/discovery tool, the rule needs weakening.

**The fix pattern:**
| Anti-pattern | Effective replacement |
|---|---|
| "Search via X (never Y)" | "Use X for search/location; Y for known paths" |
| "Only use X for Z" | "X is preferred for Z; Y works when path is known" |
| "Always do X before Y" | "Do X before Y unless you already have the result" |

*(Captured June 2026 — SOUL.md audit found 2 instances of this anti-pattern in Memory Access and Storage Routing sections. Pattern likely to recur in new guidance entries.)*

### 5. Self-Healing Equilibrium Loop
`Change → Drift anchor updated → Knowledge propagated → System + doc converge`

Every structural change must propagate through ALL affected files. The system is healthy when anchor and reality match.

### 6. Look Before Designing
How does a similar mechanism already work? Check cron jobs, kanban workers, existing skills for the pattern before designing from scratch.

## Equilibrium Check Sequence

1. Read drift anchor (system-architecture.md)
2. Survey actual: kanban DB, cron jobs, profiles on disk, memory tree
3. Cross-reference — produce drift list
4. **PRESENT drifts for approval** — never fix without go-ahead
5. For each approved drift: pre-flight checklist → fix → update anchor
6. Re-verify, stale-ref scan, log to intervention_log

## Patch Tool Safety

patch() fuzzy matching corrupts pipe chars in tables and bullet lists. **For markdown tables or bullets:** use execute_code (Python read/write/edit) or write_file (full replacement). If patching despite warning, verify immediately with raw repr.

## Tier 1 Update Protocol

Trigger: behavioral guardrail change in memory store.

1. **Ask first** — "This needs Tier 1. Do you want me to add it?" Wait for explicit "yes, put it in Tier 1" — not "sure" or "ok".
2. Update via memory(action='add', target='memory')
3. Update system-architecture.md (count, chars, description)
4. Batch all Tier 1 changes into one atomic session.

## Key Reference Files

- `references/skill-design.md` — creating, merging, designing skills
- `references/identity-prompt-audit.md` — scanning skills for personal data
- `references/identity-document-llm-readability.md` — structural/semantic patterns that cause LLMs to misinterpret identity documents
- `references/deduplication-protocol.md` — single-source-of-truth conventions
- `references/equilibrium-stale-reference-scanner.md` — search patterns after drift fix
- `references/pre-flight-system-audit.md` — full system integrity check (QMD, cron skills, script paths)
- `references/contradiction-trace-procedure.md` — systematic trace of behavioral rules to source files; contradiction detection between tiers
- `references/guidance-tool-contradiction-diagnosis.md` — tool description vs guidance constant conflicts
- `references/system-prompt-assembly-chain.md` — full trace: SOUL.md → prompt_builder → system_prompt → memory_tool injection chain
- `references/system-prompt-patch-workflow.md` — patching Hermes Python source via 99-hermes-patches
- `references/path-dependency-tracing.md` — full-system sweep before removing a path/symlink
- `references/cron-prompt-design.md` — recency bias, prompt structure, token budget
- `references/trace-before-fix.md` — trace root cause before patching symptoms
- `references/post-rename-verification.md` — what to check after renaming a skill
- `references/runtime-prompt-verification.md` — three-source cross-reference: doc claims vs patch files vs runtime; post-removal stale-ref sweep
- `references/system-prompt-token-audit.md` — methodology for measuring per-block token cost, identifying bloat, tracing full gating chain, prioritizing optimization recommendations
