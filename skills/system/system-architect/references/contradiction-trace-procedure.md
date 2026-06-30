# Contradiction Trace Procedure

Systematic approach for tracing where a behavioral rule lives in the prompt stack and checking for cross-tier contradictions.

## Trigger

Load this procedure when the user gives a new behavioral instruction and you need to verify it doesn't conflict with existing prompt layers — or when investigating "why does the agent keep doing X despite rules saying not to."

## Step-by-Step

### Step 1 — Read the Identity Layer (SOUL.md)

```
read_file("/opt/data/SOUL.md")
```

SOUL.md defines the agent's identity, prime directive, execution contract, communication rules, and feedback response. It's loaded as slot #1 in the stable tier by `load_soul_md()` in `prompt_builder.py`.

Check: does the new rule align with or contradict SOUL.md sections?

### Step 2 — Check Guidance Constants (prompt_builder.py)

```
search_files(path="/opt/hermes/agent/prompt_builder.py", pattern="<SECTION_NAME|KEYWORD>")
```

Major constants that inject behavioral instructions:
- `WORKFLOW_GUIDANCE` — phase/state machine (CLARIFY / EXECUTE / BLOCKED)
- `MEMORY_GUIDANCE` — what to store in the memory tool vs the memory tree
- `SESSION_SEARCH_GUIDANCE` — when/how to use session_search
- `SKILLS_GUIDANCE` — when to create/update skills
- `STEER_CHANNEL_NOTE` — out-of-band user messages
- `GOOGLE_MODEL_OPERATIONAL_GUIDANCE` — Google model-specific rules
- `OPENAI_MODEL_EXECUTION_GUIDANCE` — GPT/Codex/Grok rules

Each is conditionally injected based on tool availability (e.g., MEMORY_GUIDANCE only when `memory` tool is loaded).

### Step 3 — Check Volatile Tier Labels (memory_tool.py)

```
search_files(path="/opt/hermes/tools/memory_tool.py", pattern="_render_block")
```

The `_render_block` method generates the header labels injected into every system prompt:
- "MEMORY (behavioral guardrails)" — from `_SystemPromptSnapshot("memory")`
- "USER PROFILE (who the user is)" — from `_SystemPromptSnapshot("user")`

These labels can conflict with the tool description or MEMORY_GUIDANCE (e.g., old label said "personal notes" while descriptions said "behavioral guardrails").

### Step 4 — Check the Assembly Chain (system_prompt.py)

```
read_file("/opt/hermes/agent/system_prompt.py")
```

`build_system_prompt_parts()` assembles three tiers:
- **Stable**: SOUL.md identity + guidance constants + skills index + environment/profile hints
- **Context**: project files (.hermes.md, AGENTS.md, CLAUDE.md, .cursorrules) + caller's system_message
- **Volatile**: memory/USER.md snapshot from memory_tool.py + external memory provider + timestamp

The volatile tier is `format_for_system_prompt("memory")` and `format_for_system_prompt("user")` — these return the frozen snapshot captured at session load.

### Step 5 — Cross-Reference Between Tiers

For each potential contradiction spot:

| Check | What to compare |
|-------|----------------|
| SOUL.md vs WORKFLOW_GUIDANCE | Do they describe the same workflow the same way? |
| SOUL.md vs MEMORY_GUIDANCE | Does SOUL.md say something about memory that contradicts MEMORY_GUIDANCE? |
| Tool description vs constant | Does the tool's `description` field say something different from the guidance constant? (See guidance-tool-contradiction-diagnosis.md) |
| Memory header vs content rules | Does the `_render_block` label match what MEMORY_GUIDANCE says memory is for? |
| USER PROFILE vs SOUL.md | Does the user's stored preferences contradict the generic operational guidance? |

### Step 6 — Check Patches

If the running system has patches applied:

```
ls /opt/data/home/.hermes/patches/
```

Patches modify installed Python files. Check the patch content for each modified file:
- `prompt_builder.py.patch` — may have overridden `WORKFLOW_GUIDANCE` or `MEMORY_GUIDANCE`
- `memory_tool.py.patch` — may have changed `_render_block` labels or tool descriptions
- `system_prompt.py.patch` — may have changed the assembly logic

### Step 7 — Verify with Memory Content

Read the actual on-disk memory:

```
read_file("$HERMES_HOME/memory/MEMORY.md")
read_file("$HERMES_HOME/memory/USER.md")
```

The memory store's content is injected verbatim into the volatile tier. Check that memory entries don't contradict guidance constants or SOUL.md.

## Common Contradiction Patterns

| Pattern | Detection | Fix |
|---------|-----------|-----|
| **Label vs description mismatch** | `_render_block` label says X, tool description says Y | Patch memory_tool.py or the tool description |
| **Directional conflict** | WORKFLOW says "investigate→propose," SOUL.md says "execute directly" | Align both to the same model |
| **Self-undermining exception** | Constraint states rule X, then immediately carves out "unless Y" | Remove the carve-out or tighten it |
| **Level strength mismatch** | MUST-level directive overrides should-level constraint | Soften the MUST language or strengthen the should |
| **Memory vs guidance** | Memory entry says "always ask first," guidance says "direct orders get direct execution" | Update memory to match current guidance |

## When to Patch vs Report

| Target | Action |
|--------|--------|
| `/opt/data/SOUL.md` | Edit directly (user-created identity file) |
| `/opt/data/home/.hermes/patches/*.patch` | Edit patch file directly (applies at next restart) |
| `/opt/hermes/tools/memory_tool.py` (installed) | Create/update a patch via 99-hermes-patches |
| `/opt/hermes/agent/prompt_builder.py` (installed) | Create/update a patch via 99-hermes-patches |
| Bundled skills (`/opt/hermes/skills/`) | Report — don't patch |
| User-created skills (`/opt/data/skills/`) | Patch via skill_manage(action='patch') |
