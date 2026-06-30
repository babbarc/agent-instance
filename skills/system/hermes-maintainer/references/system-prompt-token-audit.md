# System Prompt Token Efficiency Audit

Methodology for auditing system prompt token usage and identifying savings.

## Key Lesson: Don't Trust Architecture Docs Alone

The architecture docs (`system-prompt-architecture.md`, `prompt-assembly.md`) describe the intended design. They can be stale — gating logic changes, patches get removed, env vars get added. **Always verify at runtime before reporting token costs.**

## Audit Procedure

### Phase 1 — Map the Structure

Read the architecture docs for a structural overview. Identify:
- The three tiers (stable/context/volatile)
- Which blocks are gated vs always-on
- Which model families get per-model guidance

### Phase 2 — Trace Actual Gating Logic

For every block claimed by the docs:

1. **Check system_prompt.py** — find the actual `if` conditions that gate each block. Are they gated on:
   - Tool presence? (`"kanban_show" in agent.valid_tool_names`)
   - Model name substring? (`"gpt" in _model_lower`)
   - Env var? (`os.environ.get("HERMES_KANBAN_TASK")`)
   - Config value? (`agent.skip_context_files`)

2. **Check agent_init.py** — some guidance is pre-resolved at init time (e.g. `_kanban_worker_guidance`). Trace the resolution logic.

3. **Check tool registrations** — tools registered with `check_fn` may conditionally appear/disappear from `valid_tool_names`, which affects gating of the guidance blocks that check for them.

### Phase 3 — Verify at Runtime

| Check | Method |
|-------|--------|
| Env vars present | `os.environ.get("VAR_NAME")` |
| Toolsets enabled | `load_config()["toolsets"]` |
| Model name | The agent's `agent.model` value |
| Tool presence | Check your own tool list for tool names |
| Function behavior | Call the function: `load_soul_md()` returns content, inspect it |

### Phase 4 — Separate Stable from Volatile

- **Stable tier** (cached for session — benefits from DeepSeek 50× prefix cache discount)
- **Volatile tier** (re-injected every turn — full token cost every turn)

Stable tier tokens are cheap per-turn but consume context window. Volatile tier tokens cost full price every turn.

### Phase 5 — Measure

```python
# For Python constants
len(CONSTANT_NAME)  # chars
len(CONSTANT_NAME) // 4  # rough token estimate

# For loaded files
len(open(path).read())

# For function-generated blocks
len(build_skills_system_prompt())
```

## Canonical Failure Mode

KANBAN_GUIDANCE (~1KB, ~1,014 tok) is listed in the architecture doc as a stable-tier block. The doc says it's gated on kanban tools being loaded. Since kanban tools ARE loaded in the main session, you'd conclude it's injected.

**Why that's wrong:** The actual gating chain is:
1. `agent._kanban_worker_guidance` is pre-resolved at `agent_init.py` line 978
2. It gates on `"kanban_show" in agent.valid_tool_names`
3. `kanban_show` is registered with `check_fn=_check_kanban_mode` in `kanban_tools.py`
4. `_check_kanban_mode` returns True only if `$HERMES_KANBAN_TASK` is set OR the profile has `"kanban"` in its toolsets
5. The main session has neither → `kanban_show` is NOT in `valid_tool_names` → guidance is set to `""` → NOT injected

**Lesson:** Trace the full gating chain — tool registration → check_fn → env vars → toolset config → agent init → system prompt assembly — before concluding a block is or isn't loaded.

## What's Worth Optimizing

Not all token savings are equal:

| Priority | Type | Why |
|----------|------|-----|
| High | Duplicative volatile-tier blocks | Pay full price every turn |
| Medium | Gating errors (block fires when it shouldn't) | Fix the gate, save it forever |
| Low | Bloated stable-tier blocks | Cached after turn 1 — cheap per-turn |

The skills manifest (2,733 tok) is the largest stable-tier block. It benefits from prefix caching but consumes context window. Only worth optimizing if you're hitting context limits.
