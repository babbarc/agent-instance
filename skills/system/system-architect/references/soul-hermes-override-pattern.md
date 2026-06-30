# SOUL.md ↔ .hermes.md Override Pattern

> Separating generic system-prompt guidance from environment-specific bindings.

## Problem

`.hermes.md` (project context, context tier) often duplicates content already in SOUL.md (identity tier). When both describe the same thing — storage routing, memory access, skills routing — the `.hermes.md` copy drifts, accumulates stale refs, and the two sources never agree.

**Root cause:** `.hermes.md` was treated as a patch overlay ("add more rules") instead of an override layer ("refine or replace for this environment").

## Principle

| Layer | Role | What goes there |
|-------|------|-----------------|
| **SOUL.md** | Universal decision framework | Data-type categories, precedence rules, access patterns. Profile-agnostic. |
| **.hermes.md** | Environment-specific bindings | Concrete paths, domain overrides, local conventions. Only what differs from the generic case. |

**Rule:** If `.hermes.md` says the same thing as SOUL.md, remove it from `.hermes.md`. If `.hermes.md` needs to refine a SOUL.md rule, say only what changes — don't repeat the framework.

## Detection

Common overlap patterns:

1. **Identical sections** — Same heading, same body, same examples. `.hermes.md` is cargo-culting SOUL.md. → Remove from `.hermes.md`.

2. **Same concept, different detail level** — SOUL.md gives a generic rule; `.hermes.md` adds concrete paths. → Keep in `.hermes.md` but strip the generic preamble — just the overrides.

3. **Stale cross-references** — `.hermes.md` points to a file (`DATABASE.md`, `hermes-docs-map.md`) that never existed or was deleted. → Fix or remove the reference.

4. **Split routing across 3+ fragments** — Same decision tree (e.g. "facts → memory/, procedures → skills, preferences → MEMORY.md") appears in SOUL.md's Storage Routing section + SOUL.md's Memory paragraph + `.hermes.md`'s Skills routing line. → Consolidate into one authoritative source (SOUL.md), remove duplicates from `.hermes.md`.

5. **Baked-in tool guidance overlap** — The compiled Hermes agent (prompt slot #2) may have its own Storage Routing / Memory Access sections that duplicate or contradict SOUL.md. → Add corrections to SOUL.md (slot #1) rather than `.hermes.md` (slot #7). The identity-layer version carries more weight for the LLM.

## Storage Routing Framework

The generic SOUL.md Storage Routing section uses a precedence-ordered decision tree. Six data types, evaluated top-to-bottom — highest-priority match wins:

| Priority | Data type | Destination | Example |
|----------|-----------|-------------|---------|
| 1 | Person facts (name, DOB, phone, address, relationship) | contacts/<person>.md | Write before any other action |
| 2 | Binary documents (PDF, image, spreadsheet, scan) | per .hermes.md binary path | + .md reference in memory tree with `document:` frontmatter |
| 3 | Procedures (repeatable workflows with numbered steps) | skill_manage create | Pass the skill gate first |
| 4 | Reference facts (policy numbers, account details, env config) | memory/<domain>/<topic>.md | Search via mcp_qmd_query |
| 5 | Behavioral preferences (corrections, work-style rules) | MEMORY.md via memory tool | Max ~10 entries |
| 6 | Temp / one-off output (analysis, intermediates, scripts) | /tmp/ | Discardable |

**Note on baked-in tool guidance:** The Hermes agent's compiled tool guidance (prompt slot #2) may contain its own Storage Routing, Memory paragraph, and Memory Access sections with stale content (e.g. `DATABASE.md` ref, hardcoded domain paths). You cannot remove these, but SOUL.md's version (prompt slot #1) supersedes them conceptually — the LLM sees both and the cleaner profile-specific version carries more weight.

## How to Write an Override

Bad (repeats framework + adds path):
```
## Storage Routing
Memory tree = .md only. Binaries → /nebula/.
- User fact → contacts/pallav-vasa.md
- Life tracking → life/*.md
```

Good (overrides only):
```
## Storage Routing

Environment-specific paths. Generic framework is in SOUL.md.

**Binary storage:** /nebula/.hermes-docs/<category>/
**Life tracking:** memory/life/*.md
```

## Precedence at Assembly Time

SOUL.md is loaded first (identity tier, stable). `.hermes.md` is appended later (context tier, from CWD). The LLM sees:

```
[SOUL.md content] ... [.hermes.md content]
```

Later content has recency advantage but does NOT override earlier content syntactically — both are present. This means `.hermes.md` should **state its overrides explicitly** (e.g. "Path overrides for this environment:") rather than relying on the reader to notice a contradiction.

## Diagnosis: Baked-in vs .hermes.md Origin

When a user reports stale content in the system prompt (e.g. `DATABASE.md`, hardcoded domain paths in Storage Routing), determine origin before proposing a fix:

1. **Grep the Hermes agent code:**
   ```bash
   grep -rn 'stale_string\|unique_phrase' /opt/hermes/agent/ 2>/dev/null
   ```
   - **Hit found** → The content is baked into a Python constant (`MEMORY_GUIDANCE`, `WORKFLOW_GUIDANCE`, etc.). Patch via 99-hermes-patches mechanism (see `patch-hermes-files` skill + `references/system-prompt-patch-workflow.md`).
   - **No hit** → The content is NOT from the baked-in agent. Origin is one of: old `.hermes.md` content, old SOUL.md content, or a generated prompt fragment. Fix by editing the source file directly — no patch mechanism needed.

2. **Check the assembly chain** — The only baked-in memory-routing constant is `MEMORY_GUIDANCE` in `prompt_builder.py` (line 143). It is generic and clean:
   ```
   MEMORY.md → behavioral re-anchor only
   Durable facts → memory/ tree by domain
   Skills → procedures only
   session_search for past context
   ```
   There is no baked-in `Storage Routing` section, no `Memory Access` section, no hardcoded domain paths. If these appear in the prompt, they came from `.hermes.md` or SOUL.md.

3. **Check old session data** — `.hermes.md` was historically treated as a patch overlay, accumulating full sections (Storage Routing, Memory Access, Pre-Flight checks) that duplicated the generic framework. Search session data for patterns like `shared-facts.md`, `fitness-coach/*.md`, `DATABASE.md` to find the original source of stale routing rules.

**Key insight from 2026-06-12 audit:** The Storage Routing section with `DATABASE.md` reference and hardcoded domain paths (`user/profile.md`, `shared-facts.md`, `life/*.md`, `fitness-coach/*.md`) was NEVER in the baked-in Hermes code. It was exclusively in old `.hermes.md` content and was removed by replacing `.hermes.md` with environment-specific overrides only.

## Stale-Ref Audit

When removing an overlapping section from `.hermes.md`:

1. **Diagnose origin first** — run the grep above before deciding how to fix
2. Check SOUL.md's version — does it mention a file that doesn't exist (`DATABASE.md` pattern)?
3. Check the memory tree — does any `.md` reference file still mention the dead path?
4. Check skills — do any reference files or templates reference the removed content?
5. If the category map file (`hermes-docs-map.md`, etc.) doesn't exist, create it by surveying the actual directory structure:
   ```bash
   ls /nebula/.hermes-docs/
   ```
   Then write a reference file under `memory/reference/` with the category structure and routing rules. Point to it from the `.hermes.md` overrides and `environment.md`.
6. After removing stale content from `.hermes.md`, verify the baked-in code has no matching stale references (grep /opt/hermes/agent/ as above). If clean, the fix is complete.

## Related

- `references/system-prompt-assembly-chain.md` — how SOUL.md + .hermes.md reach the LLM
- `references/file-placement-discipline.md` — storage routing for file content
- `references/contradiction-trace-procedure.md` — systematic trace of conflicting rules
