# Tool Origin Verification

Use when asked whether a specific tool is built-in (Hermes core) or user-created (plugin-provided). Do not guess from superficial signals (tool appearing alongside other native tools in the toolset).

## Procedure

### 1. Check the plugins directory

```
ls /opt/data/plugins/
```

A matching directory under `/opt/data/plugins/` means the tool comes from a user-created plugin. No match means it's built into Hermes core.

### 2. Check the config

Read `/opt/data/config.yaml`:

- `plugins.enabled` — is the plugin listed here?
- `plugins.disabled` — is it explicitly disabled?

Current platform is determined by: if the session loaded `toolsets: [hermes-cli]` in config, the platform is `cli`; if `platform: telegram` then the platform is `telegram`, etc.

### 3. Check `check_fn` — the actual runtime gate

Plugin toolsets are **auto-enabled by default** for all platforms (see `hermes_cli/tools_config.py` resolution logic, ~line 1456). The only exceptions:
- Toolset is in `_DEFAULT_OFF_TOOLSETS` (`spotify`, `homeassistant`, `discord`, `discord_admin`, `video`, `video_gen`, `x_search`, `moa`) — these require explicit opt-in via `hermes tools`
- User previously ran `hermes tools` for the platform and explicitly disabled it (tracked via `known_plugin_toolsets.<platform>` — if the toolset is "known" for the platform but absent from the saved toolset list, it's user-disabled)

**The real gate is the `check_fn`** — most plugins register a `check_fn` callback that the tool registry calls to decide whether to expose the tool. Common `check_fn` checks:
- Binary on PATH (`shutil.which(...)`)
- File exists on disk (`os.path.isfile(...)`)
- Auth status (`subprocess.run(['...', 'auth', 'status'])`)

### 4. Diagnose which gate is blocking

**Step A — Inspect the actual process environment first.**

The gateway process runs in a different environment than your login shell. Don't assume env vars from your terminal match what the gateway sees. Check the live process:

```bash
# Find the Hermes gateway PID
ps aux | grep 'hermes gateway run' | grep -v grep | awk '{print $2}'

# Read its actual environment
cat /proc/<PID>/environ | tr '\0' '\n' | sort

# Key vars to inspect:
# - PATH — does it include the dir where the tool's binary lives?
# - HOME — does it match where auth tokens / config files are stored?
# - Any tool-specific env vars (ANTHROPIC_API_KEY, HASS_TOKEN, etc.)
```

**Step B — Understand the check_fn's actual probe(s).**

Read the plugin's `tools.py` and find the `_check_available` / `_check_fn` function. It may have **multiple staged checks** — a failure at any stage blocks the tool:

| Stage | Common probe | Environment-sensitive? |
|---|---|---|
| 1 | Binary on PATH (`shutil.which(...)`) | ✅ PATH |
| 2 | Auth status (`subprocess.run(['...', 'auth', 'status'])`) | ✅ HOME (where creds are stored) |
| 3 | File exists (`os.path.isfile(...)`) | ❌ static (environment-independent) |

A tool can fail at stage 2 even when stage 1 passes — the binary was found but auth fails because HOME differs.

**Step C — Simulate the check_fn faithfully, using the gateway's environment.**

Don't just run the check from your shell — you'll get a false positive if PATH/HOME differ. Copy the env from `/proc/<PID>/environ`:

```bash
# Use the gateway's actual env vars
PID=$(ps aux | grep 'hermes gateway run' | grep -v grep | awk '{print $2}')
TRUNCATED_ENV=$(cat /proc/$PID/environ | tr '\0' '\n' | grep -E '^(PATH|HOME)=' | tr '\n' ' ')
env -i $TRUNCATED_ENV python3 -c "
import shutil, subprocess, os
# Exact check_fn logic:
claude = shutil.which('claude')
print(f'which claude: {claude}')
if claude:
    r = subprocess.run([claude, 'auth', 'status', '--text'], capture_output=True, text=True, timeout=10)
    print(f'auth exit: {r.returncode}, stdout: {r.stdout.strip()}')
else:
    print('FAIL: claude not found on PATH')
"
```

If this passes but the tool is still missing in-session, see Step E (gateway cache trap).

**To test the `check_fn` directly** from the agent process:

```bash
python3 -c "
from hermes_cli.plugins import get_plugin_manager
mgr = get_plugin_manager()
mgr.discover_plugins(force=True)
for name, loaded in mgr._plugins.items():
    for tool_name in loaded.tools_registered:
        entry = __import__('tools.registry', fromlist=['registry']).registry.get_entry(tool_name)
        if entry and entry.check_fn and not entry.check_fn():
            print(f'BLOCKED: {tool_name} (toolset={entry.check_fn.__name__})')
"
```

**To test a specific plugin's check** without the gateway cache:

```bash
# Import the plugin's tools module directly
python3 -c "
from tools.registry import registry
entry = registry.get_entry('claude_code')
if entry:
    print(f'check_fn result: {entry.check_fn()}')
else:
    print('Tool not registered — toolset may not be loaded')
"
```

### 5. Answer

- Plugin directory exists + listed in `plugins.enabled` → **user-created plugin**
  - If tool appears: `check_fn` passed ✅
  - If tool doesn't appear: `check_fn` returned False, or the toolset was manually disabled via `hermes tools` for this platform, or the `known_plugin_toolsets` + `platform_toolsets` interaction flipped it to disabled (see Common Traps below)
- No matching plugin directory → **built-in Hermes core tool**
- Plugin directory exists but listed in `plugins.disabled` → **plugin exists but disabled**
- Plugin toolset in `_DEFAULT_OFF_TOOLSETS` (spotify, discord, etc.) → **requires explicit opt-in via `hermes tools`**

### 6. If `check_fn` passes but tool still missing — gateway cache trap

The plugin discovery runs once per gateway process. A `/reset` does NOT restart the gateway — the agent runs in the same process. If the plugin or its dependencies were installed AFTER the gateway started, restart the gateway process so plugin discovery runs fresh.

## Common Traps

- **Plugin enabled ≠ tool loaded is usually a `check_fn` failure, but not always.** The `known_plugin_toolsets` + `platform_toolsets` interaction (see trap below) can block a tool even when `check_fn` passes.
- **`known_plugin_toolsets` entry ≠ enabled.** When a plugin toolset name appears in `known_plugin_toolsets.<platform>` but is NOT in `platform_toolsets.<platform>`, the resolution logic at `hermes_cli/tools_config.py:1469` treats it as **"user explicitly disabled it."** This is a common silent-kill pattern: once `hermes tools` saves for a platform (or the entry gets populated during debugging), any new plugin toolset gets added to `known_plugin_toolsets` but not to `platform_toolsets` — flipping from "default enabled" to "user disabled":
  - Unknown in `known_plugin_toolsets` → default enabled
  - Known + in `platform_toolsets` → explicitly enabled
  - **Known + NOT in `platform_toolsets` → treated as disabled** ← silent killer
  - Fix: either add the toolset to `platform_toolsets.<platform>` or remove it from `known_plugin_toolsets.<platform>` to return to "unknown → default enabled"
- **Don't infer origin from toolset neighbors.** A tool appearing alongside native tools in the list is not evidence it's built-in — plugins may wire into the same toolset.
- **Tool name vs plugin name may differ.** The tool's invocation name (e.g. `kanban`) may be shorter than the plugin directory name (e.g. `kanban-crud`). Check the plugin directory for the closest match.
- **`platform_toolsets` IS the gate for built-in toolsets** (like `hermes-cli` sub-toolsets). But for plugin toolsets, the resolution chain is: auto-enabled → `check_fn` → user-disabled-via-hermes-tools. `platform_toolsets` is relevant for plugin toolsets only as an explicit override (if the toolset name is literally listed there, it's force-enabled).
