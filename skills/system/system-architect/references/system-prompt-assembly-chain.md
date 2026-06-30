# System Prompt Assembly Chain

Traced 2026-06-11 during contradiction audit. Maps how each section of the system prompt reaches the LLM.

## Overview

Three tiers, assembled by `build_system_prompt_parts()` in `/opt/hermes/agent/system_prompt.py`:

```
stable + context + volatile → system prompt
```

## Stable Tier (identity + guidance)

| Section | Source | Notes |
|---------|--------|-------|
| SOUL.md identity | `/opt/data/SOUL.md` | Loaded by `load_soul_md()` in `prompt_builder.py` (line 1384). Reads from `$HERMES_HOME/SOUL.md`. Scanned for injection, truncated at 20K chars. |
| HERMES_AGENT_HELP_GUIDANCE | `prompt_builder.py` | Static string, always appended after SOUL.md |
| WORKFLOW_GUIDANCE | `prompt_builder.py` | Patched version replaced old TASK_COMPLETION_GUIDANCE + TOOL_USE_ENFORCEMENT_GUIDANCE |
| MEMORY_GUIDANCE | `prompt_builder.py` | Only injected when `memory` tool is in `valid_tool_names` |
| SESSION_SEARCH_GUIDANCE | `prompt_builder.py` | Only when `session_search` tool is loaded |
| SKILLS_GUIDANCE | `prompt_builder.py` | Only when skill tools are loaded |
| Skills index | Compiled from `**/SKILL.md` files | Preamble + descriptions. Built by `build_skills_system_prompt()` |
| Environment hints | `system_prompt.py` (inline) | WSL/Termux detection. Stable for process lifetime. |
| Profile hint | `system_prompt.py` (inline) | Reads from `file_safety._resolve_active_profile_name()` |
| Platform hints | `system_prompt.py` + plugin registry | Keyed by `agent.platform` |

## Context Tier (project files)

Discovered from `TERMINAL_CWD` at session start, priority order:
1. `.hermes.md` / `HERMES.md` (walk to git root)
2. `AGENTS.md` / `agents.md` (cwd only)
3. `CLAUDE.md` / `claude.md` (cwd only)
4. `.cursorrules` + `.cursor/rules/*.mdc` (cwd only)

First match wins. Capped at 20K chars each. Built by `build_context_files_prompt()`.

SOUL.md is excluded from this tier when already loaded as identity (`skip_soul=True`).

## Volatile Tier (per-session, never cached)

| Section | Source | Notes |
|---------|--------|-------|
| MEMORY section | `memory_tool.py` → `_render_block(target="memory")` | Header: "MEMORY (behavioral guardrails) [N% — X/Y chars]". Content from `$HERMES_HOME/memory/MEMORY.md`. Frozen snapshot at load time. |
| USER PROFILE section | `memory_tool.py` → `_render_block(target="user")` | Header: "USER PROFILE (who the user is) [N% — X/Y chars]". Content from `$HERMES_HOME/memory/USER.md`. |
| External memory | `agent._memory_manager.build_system_prompt()` | Additive, from configured external memory provider |
| Timestamp line | `system_prompt.py` (inline) | "Conversation started: Thursday, June 11, 2026" + session ID + model + provider |

## Assembly Code

```python
# /opt/hermes/agent/system_prompt.py
parts = build_system_prompt_parts(agent, system_message=system_message)
return "\n\n".join(p for p in (parts["stable"], parts["context"], parts["volatile"]) if p)
```

## Cache Behavior

- System prompt is built once per session and cached on `agent._cached_system_prompt`
- Only rebuilt after context compression events (`invalidate_system_prompt()`)
- Volatile tier is stable mid-session — memory writes update disk but NOT the prompt (next session picks up changes)
- This is the prefix-cache invariant: upstream API caches the system prompt across turns

## Patch Layer

All guidance constants in `prompt_builder.py` can be patched via the 99-hermes-patches s6 overlay mechanism. Live patches sit at `~/.hermes/patches/`. See `references/system-prompt-patch-workflow.md`.
