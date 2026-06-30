---
name: hermes-maintainer
description: "Proactive Hermes maintenance cycle: track releases, audit state, propose improvements. Load when running the weekly maintainer meta-review, investigating system health, or auditing skills/cron/memory."
annotation: "Maintain: release tracking, state audit, skill efficiency"
version: 1.0.0
metadata:
  hermes:
    related_skills: [system-architect, hermes-patching]
---

# Hermes Maintainer — Release Tracking, State Audit & Improvement

> A proactive cycle that tracks Hermes Agent releases, researches agent-building papers, audits the current state, and proposes improvements. Runs manually or via the weekly meta-review cron.

**Workspace:** `~/.hermes/maintainer/` — files: `proposals.md`, `changelog.md`, `research.md`, `tracking.md`.

**Core directive:** Research, plan, and track — but never execute without the user's explicit approval.

For source patching workflows, see `hermes-patching`. For structural governance (cron, profiles, DB, memory), see `system-architect`.

---

## 1. Check Hermes Agent Releases

1. Fetch from GitHub: `https://api.github.com/repos/nousresearch/hermes-agent/releases?per_page=5`.
2. Compare with what's logged in `changelog.md`.
3. For each new release: summarise the feature, bugfix, or breaking change.
4. Evaluate: should we adopt this? What would it change?

---

## 2. Research Agent-Building Papers (arXiv)

1. Search topics (priority order): agent memory systems, tool-use LLM, self-improving agents, autonomous agent planning, LLM debugging/self-correction.
2. For each paper: read abstract, log to `research.md` with 2–3 sentence summary and relevance to Hermes.
3. If APIs are unreachable after retries: note deferred topics in `research.md` under `## Deferred Topics` (see `references/deferred-topics-template.md`).

---

## 3. Audit Current State

1. Load all skills with `skills_list()` — check for staleness and drifts between installed base skills and modified copies.
2. `cronjob(action='list')` — check for errors, orphan skill references, schedule collisions.
3. Read memory tiers (MEMORY.md entries → memory tree → session patterns).
4. Run `hermes skills check` for upstream updates before deciding to revert any modified installed skill.

**Modified skill triage:** When a base skill was customised and upstream has since updated:

| Category | Action |
|----------|--------|
| CLI flag/command name changes | Revert — upstream fixed it |
| Instance-specific paths/credentials | Extract to a reference under the appropriate learned skill, then revert |
| Workflow improvements / pitfalls | Add to the equivalent learned skill or its references, then revert |
| Architecture docs / reference files | Move to an appropriate learned skill (e.g. `system-architect`), then revert |

After reverting, always verify the skill is still enabled — `hermes skills update` can flip it to `disabled`.

---

## 4. Propose Improvements

1. Evaluate each finding on four axes: **Value** (what improves), **Cost** (effort), **Risk** (what could break), **Priority**.
2. Only create a proposal if it unlocks a new capability, reduces maintenance burden, fixes a recurring problem, or adopts a directly-mappable research technique.
3. Max 5 proposals per cycle — prioritise and defer.
4. End every digest with: "None of these will be executed without your approval."

---

## 5. Track

1. Log active proposal status in `tracking.md`.
2. On approval: present a concrete implementation plan with files, changes, risk assessment. Await explicit confirmation before executing.
3. On completion: update status to `done`, report back.

---

## 6. Proactive Analysis Tools

These run during audit or when triggered independently:

- **Skills Token Efficiency Analysis** — scan all skills for byte size, map cron load frequency × size, identify top offenders, trim by extracting detail to `references/` or condensing verbose sections. Target 15–25% reduction per pass; skills over 30KB yield highest returns.
- **Skill Consolidation & Merging** — when two skills overlap, merge them: identify unique content from each, absorb into the more umbrella-named survivor, delete the consumed skill with `absorbed_into=<survivor>`. Run cross-reference hunt (`grep -rn <old-name> /opt/data/skills/ /opt/data/.hermes.md /opt/data/memory/`) after every merge.
- **Curator Backup Recovery** — when a file is referenced but missing on disk, check `~/.hermes/skills/.archive/` or curator backups for recoverable copies. Search `ls .archive/*/` first (fastest), then older snapshots if needed.
- **Reference File Alignment Audit** — verify all files in a skill's `references/` directory are listed in the SKILL.md. Python check included in `references/consistency-audit-checklist.md`.

---

## Reference Files

| File | Purpose |
|------|---------|
| `brain-architecture-audit.md` | 6-dimension system health check |
| `consistency-audit-checklist.md` | 8-layer cross-layer audit |
| `cross-skill-reference-pruning.md` | Stale-reference search-prune-verify |
| `deferred-topics-template.md` | Template for inaccessible-research deferrals |
| `installed-skill-drift-audit.md` | Detecting modifications to installed base skills |
| `prompt-file-audit.md` | Cross-file, cross-profile composition audit |
| `skill-distillation-protocol.md` | Instance data distillation |
| `system-prompt-token-audit.md` | Token efficiency methodology and runtime verification |
| `tool-debugging-plugin-trace.md` | Read plugin source first when debugging Hermes tool errors |
