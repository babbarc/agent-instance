# Context Injection Audit — Full Pipeline Discovery

**When to use this:** The system prompt is bloated, contradictory, or producing non-deterministic behaviour. Instead of guessing, trace every injected block back to its source and analyse the stack.

**Scope:** Covers ALL tokens injected into the LLM context — stable tier (identity, guidance blocks, skills index, environment hints, platform hints), context tier (system_message, project files), volatile tier (memory, user profile, timestamp), and ephemeral layer (per-call system prompt).

---

## Phase 1 — Map the Assembly Chain

Start with `agent/system_prompt.py:build_system_prompt_parts()`. This is the single entry point. Three tiers are built:

### 1a — Stable Tier (`agent/system_prompt.py` lines 84-280)
Each block is appended in order. Trace each one:

| Block | Source | Defined In |
|---|---|---|
| SOUL.md | `load_soul_md()` reads `$HERMES_HOME/SOUL.md` | On disk or `prompt_builder.py:DEFAULT_AGENT_IDENTITY` |
| Hermes agent help | `HERMES_AGENT_HELP_GUIDANCE` | `prompt_builder.py` constant |
| Workflow | `WORKFLOW_GUIDANCE` (universal — replaces TASK_COMPLETION + TOOL_USE_ENFORCEMENT) | `prompt_builder.py` constant |
| Memory guidance | `MEMORY_GUIDANCE` (if memory tool loaded) | `prompt_builder.py` constant |
| Session search | `SESSION_SEARCH_GUIDANCE` (if tool loaded) | `prompt_builder.py` constant |
| Skills guidance | `SKILLS_GUIDANCE` (if skill_manage loaded) | `prompt_builder.py` constant |
| Kanban guidance | `KANBAN_GUIDANCE` or worker-generated | `prompt_builder.py` constant |
| Computer use | `COMPUTER_USE_GUIDANCE` (if tool loaded) | `prompt_builder.py` constant |
| Nous subscription | `build_nous_subscription_prompt()` | `prompt_builder.py` |
| Model-specific guidance | GOOGLE_MODEL_OPERATIONAL / OPENAI_MODEL_EXECUTION (model-gated, non-duplicative) | `prompt_builder.py` constants |
| Skills index | `build_skills_system_prompt()` | `prompt_builder.py` |
| Env hints | `build_environment_hints()` | `prompt_builder.py` |
| Python probe | `get_environment_probe_line()` | `tools/env_probe.py` |
| Active profile | Hardcoded in `system_prompt.py` | Inline |
| Platform hints | `PLATFORM_HINTS[platform_key]` | `prompt_builder.py` dict |

**Key insight:** Every constant can be `grep`-searched in `agent/prompt_builder.py`. Read the file top-to-bottom — the constants are sequential.

### 1b — Context Tier (`system_prompt.py` lines 283-298)
- `system_message` (caller-supplied, from CLI `--system` or gateway context)
- `build_context_files_prompt()` — loads ONE of: `.hermes.md`, `AGENTS.md`, `CLAUDE.md`, `.cursorrules` (priority order, first wins)

### 1c — Volatile Tier (`system_prompt.py` lines 301-338)
- Memory block — `agent._memory_store.format_for_system_prompt("memory")`
- User profile — same for "user"
- External memory provider — `agent._memory_manager.build_system_prompt()` (if configured)
- Timestamp line — date only (not time), model name, provider name

### 1d — Ephemeral Layer (API-call time only)
- Injected at `conversation_loop.py` line 1006-1007 and `chat_completion_helpers.py` line 1303-1304
- `agent.ephemeral_system_prompt` is appended with `\n\n` separator
- NOT cached, NOT persisted to session DB
- Used for per-call instruction overrides (gateway `/steer`, `--system` CLI flag)

---

## Phase 2 — Condition Gate Analysis

Not every block fires for every session. Map the **condition gates**:

| Block | Gate Condition | Check Target |
|---|---|---|
| DEFAULT_IDENTITY vs SOUL.md | File exists at `$HERMES_HOME/SOUL.md` | File probe |
| MEMORY_GUIDANCE | `"memory" in agent.valid_tool_names` | `agent_init.py` tool loading |
| SESSION_SEARCH_GUIDANCE | `"session_search"` in tools | Same |
| SKILLS_GUIDANCE | `"skill_manage"` in tools | Same |
| WORKFLOW_GUIDANCE | `agent._task_completion_guidance` config (default True) AND tools loaded | `system_prompt.py` (no model gating — universal) |
| GOOGLE_OPERATIONAL | "gemini" or "gemma" in model lower | `system_prompt.py` line 136 |
| OPENAI_EXECUTION | "gpt" or "codex" or "grok" in model lower | `system_prompt.py` line 139 |
| Nous subscription | `managed_nous_tools_enabled()` returns True | `prompt_builder.py` function |
| Platform hint | `platform_key` (lowercase) in `PLATFORM_HINTS` dict | `system_prompt.py` line 270 |
| env_probe line | Remote backend OR clean environment → emits nothing | `tools/env_probe.py` |
| Kanban guidance | Kanban worker env var OR kanban_show tool in tools | `system_prompt.py` lines 125-130 |

**Audit protocol:** `grep -n the_constant_name /opt/hermes/agent/prompt_builder.py` to find each constant and gate condition. Cross-reference with the active session's model, provider, and toolset.

---

## Phase 3 — Contradiction & Overlap Scan

Read each pair of adjacent/overlapping guidance blocks for competing directives.

### Common Contradiction Archetypes

**A. STOP vs KEEP GOING (RESOLVED Jun 2026 → further refined Jun 2026):**
- Old: TOOL_USE_ENFORCEMENT said "MUST STOP" while TASK_COMPLETION said "produce a working artifact" and OPENAI_EXECUTION said "Keep calling tools until done"
- First merged into single WORKFLOW_GUIDANCE with 5-phase state machine: CLARIFY → INVESTIGATE → PROPOSE → EXECUTE → BLOCKED
- **Further refined Jun 2026**: replaced 5-phase ladder with 3-state model (CLARIFY → EXECUTE → BLOCKED). INVESTIGATE and PROPOSE phases removed. Clear instructions skip directly to EXECUTE. Ambiguous instructions return to CLARIFY.
- If you see STOP/GO conflict again, check that only the current WORKFLOW_GUIDANCE fires (no orphaned old constants)

**B. ASK vs ACT (RESOLVED Jun 2026 → further refined):**
- Old: EA Posture/SOUL.md: "never skip explicit go-ahead for state-modifying actions" vs OPENAI `<act_dont_ask>`: "act on it immediately instead of asking for clarification"
- First resolved by `<act_dont_ask>` → `<resolve_ambiguity>` reframe (separated instruction ambiguity from execution-context ambiguity)
- **Further refined Jun 2026**: EA Posture replaced with Execution Contract. `<act_dont_ask>` already removed. The 3-state WORKFLOW_GUIDANCE has no INVESTIGATE or PROPOSE phases — the old PROPOSE-vs-ACT tension is eliminated. Now: clear instruction → execute directly. Ambiguous → clarify. State-modifying: if instruction is explicit, proceed; if not addressed, confirm once.
**C. SKILLS SCANNING × ? (VERIFY BEFORE CLAIMING):**

The code-generated skills prompt header (`build_skills_system_prompt()`) restates the same concept 3 ways internally: "MUST load", "Err on the side of loading", "Only proceed if none relevant." But do NOT assume this instruction also exists in SOUL.md without reading it first — it may not. Read both files before claiming cross-source duplication.

**D. MEMORY FORMAT RULES vs ACTUAL CONTENT:**
- MEMORY_GUIDANCE: "Write declarative facts, not instructions to yourself"
- Actual memory entries: "Load credential-pre-flight skill BEFORE...", "Execution Contract: propose → execute"
- The content contradicts its own format guide

### Scan protocol

1. Read all guidance constants in `prompt_builder.py` sequentially
2. For each pair of adjacent blocks (order matters — injected top-to-bottom), ask: "If the LLM obeyed both instructions simultaneously, would either be violated?"
3. Tag each contradiction with: source blocks, competing text, and severity (blocks execution / wastes tokens / confuses priority)
4. For token waste: estimate by reading each block's instruction-set — count how many times the same concept is stated

**Mandatory verification gate — before claiming overlap or contradiction between ANY two sources, read BOTH sources' actual content.** Do not assume what SOUL.md contains based on what the code-generated skills prompt says, or vice versa. `cat` or `read_file` the actual file. If you cannot produce a verbatim quote from each source showing the overlap, you have not verified — you have assumed. An unverified claim in an audit is worse than no claim: it sends effort down a phantom fix.

---

## Phase 4 — Token Waste Quantification

Measure each block precisely:

```bash
# Count chars per constant in prompt_builder.py (use grep for constants, WORKFLOW_GUIDANCE etc.)
grep -A999 '^WORKFLOW_GUIDANCE' /opt/hermes/agent/prompt_builder.py | \
  sed -n '/^)/q;p' | wc -c

# Count memory block size
cat $HERMES_HOME/memories/MEMORY.md 2>/dev/null | wc -c

# Count user profile size  
cat $HERMES_HOME/memories/USER.md 2>/dev/null | wc -c

# Full stable tier size (before model gating)
# Read from system_prompt.py to see all parts, then grep each one
```

Rough token ratio: 1 token ≈ 3.5 chars for code-heavy prose, 4 chars for plain prose.

**Typical audit results (June 2026):**
- SOUL.md: ~1,200 tokens
- Skill scanning header (in code): ~260 tokens
- MEMORY_GUIDANCE + SESSION_SEARCH + SKILLS_GUIDANCE: ~265 tokens
- OPENAI_MODEL_EXECUTION_GUIDANCE: ~450 tokens
- WORKFLOW_GUIDANCE: ~100 tokens (merged TASK_COMPLETION + TOOL_USE_ENFORCEMENT, saved ~80)
- Platform hints (all 12): ~1,200 tokens of which ~960 is shared MEDIA boilerplate
- Memory decorative separators: ~100 tokens (2 × 46-char ═ lines)
- **Total before skills index: ~3,420 tokens**

---

## Phase 5 — Architecture Map

Document the 3+1 tier structure:

```
SYSTEM PROMPT (cached at session start)
├── STABLE TIER (never changes mid-session)
│   ├── Identity (SOUL.md or DEFAULT_AGENT_IDENTITY)
│   ├── Hermes agent help guidance
│   ├── Workflow guidance (universal — 3-state: CLARIFY/EXECUTE/BLOCKED)
│   ├── Model-specific execution guidance (model-gated)
│   ├── Memory/session/skills guidance (tool-gated)
│   ├── Kanban/computer-use guidance (tool-gated)
│   ├── Nous subscription block (subscription-gated)
│   ├── Skills index (always present if skills exist)
│   ├── Environment hints
│   ├── Python toolchain probe
│   ├── Active profile hint
│   └── Platform hint
├── CONTEXT TIER (per-session)
│   ├── system_message (caller-supplied)
│   └── Project context files (.hermes.md / AGENTS.md / etc.)
└── VOLATILE TIER (rebuilds on compression)
    ├── Memory block (MEMORY.md snapshot)
    ├── User profile (USER.md snapshot)
    ├── External memory provider block (if configured)
    └── Timestamp + model + provider + session_id

EPHEMERAL (per API call, NOT cached)
└── ephemeral_system_prompt
```

This map is the canonical reference for any audit — pin it to the session's working doc.

---

## Phase 6 — Proposing Fixes

For each finding, classify:

| Category | Action |
|---|---|
| Duplicate instruction | Remove one instance (prefer code-generated over user-authored for system-level rules) |
| Contradicting directives | Merge into one block with explicit phase markers |
| Token waste | Factor boilerplate, collapse overlapping blocks, trim decorative chars |
| Condition gate misses | Block should/shouldn't fire for this model/toolset |
| Format rule violation | Fix content (memory) or fix rule (guidance constant) |

**Important:** Present findings as a structured report. Propose consolidated text. Do NOT edit anything without explicit go-ahead — the system prompt is a structural component and Tier 1 changes invalidate cached prefixes.
