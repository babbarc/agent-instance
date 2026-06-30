---
name: create-plugin
description: "Blueprint for two kinds of Hermes plugins: (1) provider backends for image_gen, TTS, web_search — wrapping CDP automation, APIs, SaaS dashboards; (2) custom tool plugins that register tools into a named toolset via ctx.register_tool()."
annotation: "Hermes plugins: provider backends, custom tool plugins"
---

# Create Plugin (Hermes Plugin Development)

Hermes supports two plugin patterns:

| Pattern | Use When | Registration Method | Example |
|---------|----------|-------------------|---------|
| **Provider Backend** | Wrapping a service as an image_gen, TTS, web_search, or web_extract provider | `ctx.register_*_provider(YourProvider())` | gemini-web image generator |
| **Custom Tool** | Adding tools to a custom toolset that the agent can call directly | `ctx.register_tool(name, toolset, schema, handler, ...)` | Spotify, network-printer |

Both use the same directory structure, manifest format, and `register(ctx)` entry point.

- **Provider backend plugins** — register as a backend for an existing Hermes tool category (image_gen, TTS, web_search, web_extract). The agent calls the category's tool and your provider handles it.
- **Tool-registration plugins** — register entirely new tools with custom schemas and handlers. The tools appear in the agent's toolbelt alongside the built-in ones.

Both patterns share the same directory layout, manifest format, and enablement flow.

## Architecture

### Provider Backend Plugin
```
$HERMES_HOME/plugins/<category>/<name>/
├── plugin.yaml          # Manifest — name, version, kind
├── __init__.py          # Provider class + register(ctx) entry point
└── ...                  # Supporting scripts, templates, assets
```

### Tool-Registration Plugin
```
$HERMES_HOME/plugins/<name>/
├── plugin.yaml          # Manifest — name, version
├── __init__.py          # register(ctx) → ctx.register_tool() calls
├── <module>.py          # Tool handler implementations
└── references/          # Protocol docs, API references (optional)
```

## Skill-to-Plugin Audit — Evaluating Which Skills to Convert

Not every skill is a plugin candidate. Before building, audit existing skills against these criteria.

### Gate 1 — Is the skill a tool-shaped CLI/API wrapper?

A skill qualifies for plugin consideration only if it wraps an external CLI, API, or service that has **clear, repeatable inputs and outputs** — the kind of operation you'd model as a function call.

Passes the gate ✅:
- Wraps a CLI (`openhue`, `xurl`, `notion`, `nano-pdf`, `himalaya`)
- Wraps an API endpoint (`arxiv`, `polymarket`, `fitness-nutrition` via wger/USDA)
- Has a custom CRUD harness (`kanban-crud`, `life-track-crud`, `contacts-database` with `people` CLI)

Fails the gate ❌:
- Pure guidance/patterns (`one-three-one-rule`, `professional-email`, `system-architect`, `contract-review`)
- Process/workflow docs (`tax-return-filing`, `life-audit`, `travel-itinerary`, `meeting-prep`)
- Framework/reasoning procedures (`plan`, `spike`, `signal-noise-classifier`)

### Gate 2 — How strong is the candidate?

| Tier | Criteria | Examples |
|------|----------|---------|
| **Strong** | High-frequency ops + mature CLI + clear `check_fn` precondition | `contacts-database`, `kanban-crud`, `life-track-crud`, `xurl` |
| **Weaker** | Lower frequency or niche scope | `maps`, `git`, `blogwatcher`, `arxiv`, `polymarket` |
| **Already tooled** | Built-in Hermes tool covers the domain | `spotify` (bundled plugin), `browser-*` (built-in tools), `google-workspace` (gws tools), `github-*` (`gh` CLI) |

### After conversion — skill lifecycle

When a user skill becomes a plugin, the skill **stays** as the companion reference. Skills and plugins serve different roles:

- **Plugin** = the tool call (fast, token-efficient, no context overhead)
- **Skill** = companion reference (prompt strategy, failure modes, follow-up workflows, debug patterns — everything the plugin doesn't cover)

**Update the annotation to "companion reference" mode.** The annotation, description, and SKILL.md structure all need to shift:

1. **Annotation** — signal when to load the skill, not what domain it covers:
   > `annotation: "Companion reference for the <plugin-name> provider. Covers prompt strategy, follow-up modifications, and troubleshooting — load when <tool-name> needs refinement, a follow-up, or debugging."`

2. **Description** — mirrors the annotation role:
   > `description: "Companion reference for the <plugin-name> provider — prompt strategy, follow-up modifications, and troubleshooting."`

3. **SKILL.md** — trim what the plugin handles (script invocation, basic generation steps), keep what the plugin doesn't cover:
   - **Keep:** Prompt strategy / format gates, orientation rules, interactive refinement protocol, follow-up modification workflows, troubleshooting / failure mode decision trees
   - **Cut or move to references/:** Implementation history, CDP internals, design rationale, session-specific debugging notes, login flow, script reference tables (learn once)
   - **Cut entirely:** Steps the plugin handles in one call (the skill shouldn't document doing manually what the plugin automates)

**Worked example:** `software/gemini-web-images` — plugin at `plugins/image_gen/gemini-web/` took over fresh generation. The skill's SKILL.md was cut from ~7500 to ~4000 chars (pure decision tree + prompt strategy + pitfalls). CDP/Quill/internal details moved to `references/cdp-communication-patterns.md`. Annotation changed from "Use when the user wants AI-generated images from Gemini's web UI" to "Companion reference for the gemini-web image provider."

See `references/skill-to-plugin-audit.md` for the concrete audit of this agent's skill library.

## Plugin Discovery Paths

User plugins live at `$HERMES_HOME/plugins/<name>/`. Legacy path `~/.hermes/plugins/<name>/` is NOT scanned — use `$HERMES_HOME/plugins/` (check with `python3 -c "from hermes_constants import get_hermes_home; print(get_hermes_home() / 'plugins')"`).

Plugins are scanned from four sources (later overrides earlier on name collision):
1. Bundled — `<repo>/plugins/<category>/<name>/` (shipped with Hermes)
2. User — `$HERMES_HOME/plugins/<name>/` (created by you)
3. Project — `./.hermes/plugins/<name>/` (opt-in via HERMES_ENABLE_PROJECT_PLUGINS)
4. Pip — packages exposing `hermes_agent.plugins` entry-point group

---

## Pattern A: Provider Backend Plugin

Register a backend for an existing Hermes tool category.

### Categories

| Category | Provider Base Class | Registration Method | Config Key |
|----------|-------------------|-------------------|------------|
| `image_gen` | `ImageGenProvider` | `ctx.register_image_gen_provider()` | `image_gen.provider` |
| `tts` | `TTSProvider` | `ctx.register_tts_provider()` | `tts.provider` |
| `web_search` | `WebSearchProvider` | `ctx.register_web_search_provider()` | `web.search_provider` |
| `web_extract` | `WebExtractProvider` | `ctx.register_web_extract_provider()` | `web.extract_provider` |

### Plugin Manifest

```yaml
name: my-provider
version: 1.0.0
description: "What this plugin does"
author: "You"
kind: backend
```

### Provider Implementation

Create `__init__.py`:

```python
\"\"\"Your plugin. Describe what it wraps and how.\"\"\"

from __future__ import annotations
import logging
from pathlib import Path
from typing import Any, Dict

from agent.<provider_base_module> import <ProviderBaseClass>

logger = logging.getLogger(__name__)

class YourProvider(<ProviderBaseClass>):
    @property
    def name(self) -> str:
        return "your-plugin-name"

    @property
    def display_name(self) -> str:
        return "Your Display Name"

    def is_available(self) -> bool:
        \"\"\"Return True when all preconditions are met.\"\"\"
        return True

    def list_models(self) -> list[Dict[str, Any]]:
        return [{"id": "default", "display": "Default Model", ...}]

    def default_model(self) -> str | None:
        return "default"

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Your Display Name",
            "badge": "browser",
            "tag": "Short description",
            "env_vars": [],
        }

    def generate(self, ...) -> Dict[str, Any]:
        \"\"\"The actual work — call script, parse output, return result.\"\"\"
        ...

def register(ctx) -> None:
    ctx.register_<category>_provider(YourProvider())
```

### Enable + Configure

```bash
hermes plugins enable <category>/<name>
```

```yaml
# config.yaml
<category>:
  provider: <name>
  model: <model-id>
```

CDP automation pattern (browser-based provider backends): see `references/gemini-web-example.md`.

---

## Pattern B: Tool-Registration Plugin

Register entirely new tools that appear in the agent's toolbelt alongside built-in tools. Modeled after the bundled Spotify plugin (`/opt/hermes/plugins/spotify/`).

### Plugin Manifest

```yaml
name: my-plugin
version: 1.0.0
description: "What this plugin does"
author: "You"
```

No `kind: backend` — tool plugins are standalone; `kind` is optional.

### Tool Design — Map the Full CLI Surface First

Before writing a single line of plugin code, enumerate EVERY subcommand of the CLI being wrapped. Run `<cli> --help` or check the skill's command table. Then decide coverage:

1. **List every subcommand** — produce a table mapping CLI → proposed tool name → include/exclude
2. **Flag exclusions** — for any subcommand you propose skipping, state why (too niche, terminal is fine)
3. **Get sign-off** — present the full table to the user; don't assume a subset is acceptable
4. **Only then start writing** — one tool handler at a time

**Anti-pattern:** Proposing 3 tools for a CLI with 10 subcommands without first showing the full surface. The user will catch the gap.

**Good coverage rule of thumb:** Include every subcommand that produces useful output or modifies state. Only exclude truly diagnostic/debug-only commands (e.g. `schema` for a DB wrapper, `--debug` flags). Read-only inspection commands (`get`, `children`, `events`) are cheap to include and prevent the user from needing the terminal.

### Tool Implementation

Tools live in a separate module, imported by `__init__.py`.

**`tools.py` — handler implementation:**

```python
\"\"\"Tool handlers for my-plugin.\"\"\"

from __future__ import annotations
from typing import Any
from tools.registry import tool_error, tool_result


def _check_available() -> bool:
    \"\"\"Return True when the tool's preconditions are met.
    If False, the tool is hidden from the agent's toolbelt.\"\"\"
    return True


def _handle_my_tool(args: dict[str, Any], **kwargs) -> str:
    \"\"\"Tool handler — receives parsed args, returns JSON string.

    NOTE: The Hermes dispatch framework injects ``task_id`` and
    ``user_task`` keyword arguments into every registered tool handler.
    Handlers MUST accept ``**kwargs`` to absorb them.  Without it,
    the framework raises:
    ``TypeError: _handle_my_tool() got an unexpected keyword argument
    'task_id'``.
    \"\"\"
    try:
        result = do_something(args.get("param"))
        return tool_result(success=True, data=result)
    except Exception as exc:
        return tool_error(str(exc))


MY_TOOL_SCHEMA = {
    "name": "my_tool",
    "description": "What this tool does — concise, one line.",
    "parameters": {
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "What this param does"},
        },
        "required": ["param"],
    },
}
```

### Plugin Registration

**`__init__.py`:**

```python
\"\"\"My plugin — registers custom tools.\"\"\"

from __future__ import annotations
from .tools import (
    MY_TOOL_SCHEMA,
    _handle_my_tool,
    _check_available,
)

_TOOLS = (
    ("my_tool", MY_TOOL_SCHEMA, _handle_my_tool, "🔧"),
)

def register(ctx) -> None:
    for name, schema, handler, emoji in _TOOLS:
        ctx.register_tool(
            name=name,
            toolset="<toolset-name>",
            schema=schema,
            handler=handler,
            check_fn=_check_available,
            emoji=emoji,
        )
```

### Key API: `ctx.register_tool()`

```python
ctx.register_tool(
    name: str,              # Tool name (snake_case, used to call it)
    toolset: str,           # Toolset name for enable/disable grouping
    schema: dict,           # JSON Schema (OpenAI tool format)
    handler: Callable,      # fn(args: dict) -> str (JSON)
    check_fn: Callable | None = None,  # fn() -> bool (show/hide tool)
    requires_env: list | None = None,  # Env vars needed
    is_async: bool = False,
    description: str = "",
    emoji: str = "",
    override: bool = False,  # Replace built-in tool with same name
) -> None
```

### Tool Schema Format

The schema follows the OpenAI tool calling format (JSON Schema):

```python
SCHEMA = {
    "name": "tool_name",
    "description": "Short description shown to the LLM.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to operate on"},
            "mode": {"type": "string", "enum": ["auto", "manual"]},
            "count": {"type": "integer", "description": "Number of items"},
            "options": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["path"],
    },
}
```

### Handler Return Values

Always return a JSON string via one of these helpers:

```python
from tools.registry import tool_result, tool_error

# Success — pass a dict positional OR keyword args
tool_result(data={"ink": {"black": 96}})          # dict with 'data' key
tool_result(success=True, state="idle", ink=ink)   # flattened keywords

# Error
tool_error("File not found")                       # {"error": "..."}
tool_error("Failed", status_code=500)              # with extra fields
```

---

## Common: Plugin Hooks & Slash Commands

Beyond tools, plugins can register hooks and slash commands:

```python
def register(ctx) -> None:
    # Hook into tool call lifecycle
    ctx.register_hook("post_tool_call", my_post_tool_handler)

    # Register a /command for the session
    ctx.register_command(
        "my-command",
        handler=_handle_my_slash,
        description="Do something useful.",
    )
```

Available hooks: `post_tool_call`, `on_session_end`, `on_session_start` (check `VALID_HOOKS` in `hermes_cli/plugins.py`).

---

## Reverse Direction — Plugin → Skill Conversion

A tool-registration plugin's schemas cost ~200-500 tokens per turn (3-6 tools). Converting it to a skill removes that overhead since skills load on-demand.

**Decision rule:** don't do it. The savings (~350 tokens/turn for a typical plugin) don't justify the operational cost — load-on-demand friction, two artifacts to maintain (the underlying script still lives in the plugin dir), and loss of direct tool calling. Reserve reverse conversion for plugins with 10+ tools, unusually verbose schemas (>1000 tokens/turn), or when the underlying service is already a skill and the plugin adds no capability the skill doesn't cover. In those cases, disable the plugin and let the skill drive via terminal(). Otherwise, leave the plugin alone — a few hundred tokens in a 30K+ system prompt is noise.

## Pitfalls

### Handler Must Accept `**kwargs`

Every tool handler registered via `ctx.register_tool()` is called by the Hermes dispatch framework as `handler(args, task_id=..., user_task=...)`. If your handler signature is `def handler(args)` without `**kwargs`, you get:

```
TypeError: _handle_my_tool() got an unexpected keyword argument 'task_id'
```

**Always** define handlers as `def handler(args: dict, **kwargs)`. The `**kwargs` absorbs the injected parameters harmlessly. If you need `task_id` for logging or tracing, retrieve it as `kwargs.get("task_id")`.

### Subprocess Environment vs Gateway Environment

When a tool handler spawns a subprocess (e.g. wrapping a CLI script), the subprocess inherits the **gateway process environment** — not the user's interactive shell environment. `$HOME` may differ:

- **Terminal (interactive):** `$HOME=/opt/data/home`
- **Gateway (subprocess):** `$HOME=/opt/data`

This matters for tools that rely on `os.path.expanduser("~")` to locate credential files, token caches, or config. If a tool works from the terminal but fails from the gateway, check `$HOME` in the subprocess first. Prefer hardcoded absolute paths or symlinks over `~` expansion in plugin code.

### Plugin Changes Require Process Restart

Plugin discovery + tool registration happens once per gateway process. New or updated plugins require:
- **Gateway:** `/restart` or gateway restart
- **CLI:** `/reset` (session restart)
- Tools appear on the NEXT session, not the current one

### Stale `.pyc` Cache

After editing a plugin's Python files, clear `__pycache__/` directories. The old bytecode survives process restarts if the `.pyc` isn't invalidated.

### Plugin Toolset Known-Vs-Enabled Fallthrough

A plugin toolset can be registered correctly with `check_fn` returning True yet silently invisible on a specific platform. The toolset auto-enable logic has a three-way fallthrough that catches developers off guard:

```python
for pts in plugin_ts_keys:
    if pts in toolset_names:            # platform_toolsets.<platform> lists it → ON
        enabled_toolsets.add(pts)
    elif pts in _DEFAULT_OFF_TOOLSETS:  # opt-in toolset → OFF
        continue
    elif pts not in known_for_platform: # never seen before → default ON
        enabled_toolsets.add(pts)
    # else: known but not in config = user disabled it → OFF ← SURPRISE
```

**The trap:** Once a toolset enters `known_plugin_toolsets.<platform>` for a platform (as a side-effect of `hermes tools` saving, or manual config edits), its absence from `platform_toolsets.<platform>` flips from "new plugin, auto-enable" to "known but disabled." Tools that were working disappear on the next `/reset`.

**Triggers:** Running `hermes tools` on any platform writes ALL plugin toolsets into `known_plugin_toolsets` for that platform. If the toolset also leaked into another platform's `known_plugin_toolsets` (e.g. via a `_save_platform_tools` call from a different session), that platform now treats it as disabled.

**Fix:** Add the toolset to `platform_toolsets.<platform>` explicitly:
```yaml
platform_toolsets:
  cli:
  - hermes-cli
  - my-plugin-toolset
```

Or use the CLI:
```bash
hermes tools enable my-plugin-toolset
```

---

## Enablement & Lifecycle

```bash
# Enable — adds to config.yaml plugins.enabled list
hermes plugins enable <name>

# List plugins (shows bundled + user + enabled status)
hermes plugins list

# Disable without removing
hermes plugins disable <name>

# Full remove from disk
hermes plugins remove <name>
```

## Troubleshooting

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| Tool not in agent's toolset | Session was started before plugin was enabled | `/reset` |
| Plugin not in `hermes plugins list` | Wrong directory path | Check `$HERMES_HOME/plugins/` path, not `~/.hermes/plugins/` |
| `check_fn` returning False | Precondition not met (service unreachable, missing env var) | Check each condition in `check_fn()` |
| Tools registered but don't appear | Wrong toolset name or `check_fn` returns False | Verify toolset name matches, debug `check_fn` |
| check_fn passes, tool still invisible | Toolset is in `known_plugin_toolsets.<platform>` but absent from `platform_toolsets.<platform>` — system treats known+absent as "user disabled" | Add the toolset to `platform_toolsets.<platform>` in config.yaml or run `hermes tools enable <toolset-name>` |
| Plugin shows "not enabled" | Not yet in `config.yaml plugins.enabled` | `hermes plugins enable <name>` |
| ImportError from plugin code | Missing dependencies in the runtime env | Install via Containerfile or `uv pip install` |
| `TypeError: got an unexpected keyword argument 'task_id'` | Handler lacks `**kwargs` | Add `**kwargs` to handler signature |
| Tool works from terminal but fails from gateway | `$HOME` differs between environments | Hardcode credential path or create symlink |
| Old code runs after edit | `.pyc` cache not invalidated | Clear `__pycache__/` then restart |

## Verification Checklist

- [ ] Plugin appears in `hermes plugins list`
- [ ] Plugin status is `enabled`
- [ ] `check_fn()` returns True (if you set one)
- [ ] After `/reset` or gateway restart, tool appears in agent's toolbelt
- [ ] Tool calls succeed end-to-end with real data
