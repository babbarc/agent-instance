# System Prompt Token Audit

## When to Use

The user asks to optimize the system prompt, reduce token usage, or audit what's being injected every turn. Also load when investigating why sessions are hitting context limits or when the stable tier feels bloated.

## Methodology

### 1. Map All Blocks

Identify every block in the system prompt using `system-prompt-assembly-chain.md` as a starting point. Then verify at runtime — don't trust docs alone.

```python
from agent.prompt_builder import (
    HERMES_AGENT_HELP_GUIDANCE,
    MEMORY_GUIDANCE, SESSION_SEARCH_GUIDANCE,
    SKILLS_GUIDANCE, KANBAN_GUIDANCE,
    WORKFLOW_GUIDANCE, STEER_CHANNEL_NOTE,
    OPENAI_MODEL_EXECUTION_GUIDANCE,
    GOOGLE_MODEL_OPERATIONAL_GUIDANCE,
    build_skills_system_prompt,
    PLATFORM_HINTS,
)

blocks = {
    'SOUL.md': '--- measure via load_soul_md() runtime call',
    'HERMES_AGENT_HELP_GUIDANCE': len(HERMES_AGENT_HELP_GUIDANCE),
    # ... all blocks
    'Skills manifest': len(build_skills_system_prompt()),
    'Telegram hint': len(PLATFORM_HINTS.get('telegram', '')),
}
```

Plus the non-constant files:
- `.hermes.md` (context tier — measure `len(read_text())`)
- `MEMORY.md` (volatile tier)
- `USER.md` (volatile tier)
- Environment hints, python toolchain probe, active profile block

**Key insight:** The stable tier is cached and gets DeepSeek's 50× prefix discount. Volatile tier blocks re-enter context on every turn but also benefit from prefix caching on turn 2+. The real cost is context-window pressure on long sessions, not per-token billing.

### 2. Identify Gating

For each block, determine whether it's loaded for the current model/profile:

| Gate | Blocks affected | Check |
|------|----------------|-------|
| Model name contains "gpt"/"codex"/"grok" | `OPENAI_MODEL_EXECUTION_GUIDANCE` | `agent.model` |
| Model name contains "gemini"/"gemma" | `GOOGLE_MODEL_OPERATIONAL_GUIDANCE` | `agent.model` |
| Kanban tool loaded + `$HERMES_KANBAN_TASK` | `KANBAN_GUIDANCE` (full) | Check if the env var is gated or just tool presence |
| Tool-specific | MEMORY_GUIDANCE, SESSION_SEARCH_GUIDANCE, SKILLS_GUIDANCE | Check `valid_tool_names` |
| Platform key | PLATFORM_HINTS | Check `agent.platform` |
| Computer use tool | COMPUTER_USE_GUIDANCE | Check tool loading |

Always-loaded blocks: SOUL.md, HERMES_AGENT_HELP_GUIDANCE, WORKFLOW_GUIDANCE, STEER_CHANNEL_NOTE, skills manifest, environment hints, active profile, platform hint (current platform).

### 3. Measure Token Cost

```python
for name, chars in blocks.items():
    print(f'{name:50s} {chars:>6d} chars  ~{chars//4:>4d} tok')
```

(Conservative estimate: 4 chars ≈ 1 token for English text. Python code, tables, and URLs tokenize differently — use `len(text) // 3` for code-heavy blocks.)

### 4. Check for Duplication

Guidance constants often duplicate SOUL.md and .hermes.md. Common overlaps:

| Constant | Where duplicated | Typical overlap |
|----------|-----------------|-----------------|
| MEMORY_GUIDANCE | SOUL.md → Storage Routing | Memory vs files vs skills routing |
| SKILLS_GUIDANCE | .hermes.md → Skills gate | Skill creation discipline |
| WORKFLOW_GUIDANCE | SOUL.md → Execution Contract | CLARIFY/EXECUTE/BLOCKED rules |

These guidance constants are installed Hermes code — **don't patch them to dedup**. Instead, trim the SOUL.md side to remove the overlap. Keep only what's unique to SOUL.md (person facts, binary paths, specific override rules).

### 5. Profile the Loaded Set for This Session

Run a measurement with the same model/provider as the active session:

```bash
cd /opt/hermes && python3 -c "
import sys; sys.path.insert(0, '.')
# ... measure all blocks
total = sum(blocks.values())
print(f'ACTIVE SESSION EST: {total} chars ~{total//4} tok')
"
```

### 6. Trace the Full Gating Chain

A block's gating is often multi-layered. Don't stop at the first check — trace end-to-end:

```
system_prompt.py gate → agent_init.py resolution → tool registration check_fn → config/toolsets → env var
```

**Example: KANBAN_GUIDANCE trace**
```
system_prompt.py → agent._kanban_worker_guidance (pre-resolved at init)
                → agent_init.py: KANBAN_GUIDANCE IF "kanban_show" IN valid_tool_names
                → kanban_tools.py: "kanban_show" registered with check_fn=_check_kanban_mode()
                → _check_kanban_mode(): True IF $HERMES_KANBAN_TASK set OR "kanban" in toolsets
```

The chain reveals that KANBAN_GUIDANCE is already correctly gated — the main session (no `$HERMES_KANBAN_TASK`, no kanban toolset) never sees it. A shallow look at system_prompt.py's `"kanban" in valid_tool_names` would wrongly conclude it's loaded.

**Always trace the actual check_fn/registration chain — never trust the first gating condition you see.**

### 7. Prioritize Optimization Recommendations

| Priority | Token savings | Type | Example |
|----------|--------------|------|---------|
| High | 500+ tok | Workflow-level gating | Gate KANBAN_GUIDANCE on `$HERMES_KANBAN_TASK` (already done — verify at runtime first) |
| Medium | 100-500 tok | Trimming duplicates | SOUL.md sections that overlap guidance constants |
| Low | <100 tok | Tightening wording | Platform hint text, help guidance pointers |

**Always check:** is the block in the stable tier (cached/discounted) or volatile tier (per-turn)? A 1,000 tok savings in stable tier is worth ~20 tok per turn after caching. A 1,000 tok savings in volatile tier saves 1,000 tok every turn.

**Always verify gating at runtime before recommending a change.** Documented gating can differ from actual gating (e.g., a constant gated on tool presence may be further gated by a check_fn that effectively gates on an env var).

### 7. Reference Doc Verification

After any system prompt restructuring:
1. Update `system-prompt-architecture.md` (the authoritative assembly reference)
2. Update `prompt-assembly.md` (lightweight copy in memory tree)
3. Update all `prompt-assembly-architecture.md` copies in skill references
4. Search for stale file/section references across all `.md` files

## Common Findings

| Finding | Likely cause | Recommendation |
|---------|-------------|---------------|
| KANBAN_GUIDANCE >1K tok in main session | Gated on tool presence, not env var — **verify at runtime first, the check_fn may already gate on env var** | Trace the full gating chain before recommending changes; the env-var gate may already exist deeper in the chain |
| Full skills manifest 2.7K tok | `build_skills_system_prompt()` lists all 89 skills with descriptions | Trim descriptions to 1 line, or strip descriptions and keep names only |
| Guidance blocks duplicate SOUL.md | SOUL.md was written before guidance constants existed | Trim SOUL.md to unique content only |
| Per-model guidance for wrong model | Model name doesn't match any gating pattern | Already correctly gated — no action |
| Platform hint > 200 chars | Verbose formatting rules | Tighten to 2 sentences |

## Exit Criteria

After optimization:
- Total stable tier tokens reduced by measured amount
- No behavioral change (verify with a test query: "do X" → agent still executes correctly)
- All affected docs updated
- Gating changes patched and verified at runtime
