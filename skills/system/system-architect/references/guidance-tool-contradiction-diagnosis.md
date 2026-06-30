# Guidance-Tool Contradiction Diagnosis

**Trigger:** System behavior contradicts what a tool's description/params say it should do.

**Diagnosis chain (in order):**

1. **Read the tool description** — Check the tool's `description` and `parameters.description` fields in the tool schema. What does the tool say it does?

2. **Check MEMORY_GUIDANCE in prompt_builder.py** — This is the most common source of contradictions. Other guidance constants (SKILLS_GUIDANCE, SESSION_SEARCH_GUIDANCE, etc.) can also override tool behaviour:
   - `/opt/hermes/hermes/prompt_builder.py` — base Hermes version
   - `/opt/data/home/.hermes/patches/prompt_builder.py` — user-patched version (overrides base)

3. **Check SOUL.md** — at `$HERMES_HOME/SOUL.md`. This loads via `load_soul_md()` and may duplicate or reinforce guidance constants.

4. **Check tool implementation** — If the tool's own description contradicts the guidance but the guidance wins at runtime, the fix is in the guidance (not the tool). Tools ship from upstream and changing them requires a patch.

**Canonical example (June 2026 — full fix, then new drift discovered):**

**Before (all three sources contradicted each other):**
- `memory` tool description said "Save durable information to persistent memory"
- `'memory'` target described as "environment facts, project conventions, tool quirks, lessons learned"
- PRIORITY listed "User preferences and corrections > environment facts > procedural knowledge"
- `MEMORY_GUIDANCE` in prompt_builder.py said "Save durable facts using the memory tool: user preferences, environment details, tool quirks"
- `skill_manage` description bloated with system-prompt duplication (~300 chars of create/update/pinned guidance)

**First patch pass (June 10-11 2026):**
- `memory` tool description patched to: "Manage behavioral guardrails that fire every turn. Corrections and preferences only — reference data goes to write_file, procedures to skill_manage."
- `MEMORY_GUIDANCE` in prompt_builder.py patched to: "MEMORY.md (via the memory tool) is for behavioral re-anchor only. Save the 2-3 behavioral rules that must fire every turn here. Durable facts go to the $HERMES_HOME/memory/ tree via write_file."
- `'memory'` target: still "personal notes" — **NOT patched** (see residual drift below)
- PRIORITY removed (folded into the re-anchor-only framing)
- `skill_manage` description trimmed

**FIXED:** MEMORY_GUIDANCE, tool description, and SOUL.md now agree: memory = behavioral re-anchor only.

**Residual drift (STILL UNRESOLVED as of 2026-06-11):** The `target` parameter description in the memory tool schema still reads: "Which memory store: 'memory' for personal notes, 'user' for user profile." The phrase "personal notes" signals "write anything about the user/project here" — directly contradicting the patched description which says "corrections and preferences only." The LLM reads the parameter description when deciding the `target` argument and sees "personal notes" as the intended content type.

**The three-way split (unchanged):**
- MEMORY.md (via `memory` tool) — behavioral re-anchor only. Corrections, preferences, operating rules. Injected every turn.
- /opt/data/memory/ tree (via `write_file`) — structured reference facts. Policy numbers, paths, contacts, conventions, environment details. Organized by domain: finance/, life/, reference/, property/, etc. Accessed on demand.
- Skills (via `skill_manage`) — procedures only. Exact commands, numbered steps, templates. Zero instance data.

**Common mistake — conflating the stores:**
- "Memory" is ambiguous: flat MEMORY.md (mental notes) vs /opt/data/memory/ tree (structured facts). They are NOT the same thing.
- When a skill accumulates instance data (names, amounts, paths), the data belongs in /opt/data/memory/ — not embedded in SKILL.md or as a skill reference file.
- When you need to save a durable fact, ask: "Does this need to fire every turn?" Yes → MEMORY.md. No → /opt/data/memory/ tree. Is it a procedure? Yes → skill.

**Verification step — don't assume the fix landed:**
After patching any guidance constant or tool schema:
1. Check that the import actually resolves your patched version (not the original)
2. If patches use overlay/copy-on-restart mechanism, confirm that mechanism
3. Fix all sources before declaring done — a single source left unchanged means the old behaviour persists

**Audit heuristic for tool descriptions:** For each LLM-facing tool description, check:
- Opener: does the first 50 chars set the WRONG frame? ("Save durable information" — behavioral-reanchor frame needed)
- Parameter descriptions: do any advertise use cases the tool shouldn't handle?
- Bloat: is the description repeating system prompt rules? The tool schema is a reference, not a training manual.
- Target descriptions: do they contradict the DO NOT ADD / routing gates elsewhere in the description?

## Asymmetric Patch Drift — A Specific Subspecies

A variant not covered by the diagnosis chain above: **asymmetric drift**, where a tool's description was patched but the corresponding prompt-level guidance constant (in `prompt_builder.py`) was never updated to match. The tool says one thing, the system prompt says another — the LLM follows the system prompt.

**Updated canonical example (June 2026 — MEMORY_GUIDANCE now patched, residual drift in parameter description):**

The asymmetric drift pattern appeared in two phases:

1. **First drift** (resolved June 10-11): MEMORY_GUIDANCE lagged behind the patched tool description. Tool said "behavioral guardrails only"; system prompt said "save durable facts." This was FIXED by patching MEMORY_GUIDANCE in prompt_builder.py.

2. **Second drift** (still unresolved): The `target` parameter description in the tool schema now lags behind BOTH the tool description AND MEMORY_GUIDANCE. The parameter says "personal notes" while everything else says "behavioral re-anchor only."

**Key lesson for future audits:** A patch to one source can reveal misalignment in a THIRD source that was invisible before — because the two patched sources now agree, making the third one stand out. After any round of patches, re-scan ALL tool description fields (including parameter descriptions), not just the top-level description.

**Detection:**
1. List installed patches: `ls ~/.hermes/patches/*.patch`
2. For each tool patch, identify the corresponding guidance constant:
   - `memory_tool.py` ↔ `MEMORY_GUIDANCE`
   - `skill_manager_tool.py` ↔ `SKILLS_GUIDANCE`
   - `clarify_tool.py` ↔ WORKFLOW_GUIDANCE (CLARIFY phase) or `OPENAI_MODEL_EXECUTION_GUIDANCE` (resolve_ambiguity section)
3. Search the tool schema for ALL description fields (not just top-level):
   ```
   grep -A5 '"description"' /opt/hermes/tools/memory_tool.py | head -20
   ```
4. Check if the guidance constant still uses the OLD frame:
   ```
   grep -n 'MEMORY_GUIDANCE\|Save durable' /opt/hermes/agent/prompt_builder.py
   ```
   Compare against `~/.hermes/patches/prompt_builder.py.patch`.

**Root cause:** The patches were created independently — memory_tool.py got its description narrowed in one pass, but the creator didn't check ALL description fields in the tool schema (top-level + each parameter) nor the corresponding guidance constant in a different file (prompt_builder.py). Three separate fields across two files need to stay in sync: tool top-level description, tool parameter descriptions, and prompt-level guidance constant.

**Fix:** Create or extend the relevant patch file to fix ALL description fields in the tool schema AND the guidance constant in the same pass. See `system-prompt-patch-workflow.md` for the patch creation workflow.

**Verification:**
- Before declaring any tool-description fix done, grep ALL description fields in the tool schema AND all guidance constants in prompt_builder.py for language that contradicts the new framing
- The four layers that must be in sync: tool top-level description → tool parameter descriptions → prompt guidance (MEMORY_GUIDANCE / SKILLS_GUIDANCE etc.) → behavioral files (SOUL.md)
