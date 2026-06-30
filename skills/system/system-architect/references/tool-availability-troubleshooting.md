# Tool Availability Troubleshooting

Use this reference when a tool the user expects isn't showing up in the session — despite correct config, installed plugins, and `/reset`.

## Debugging Chain

### 1. Is the tool in the toolset definition?

Tool sets are defined in `toolsets.py`. The default toolset for all platforms (`_HERMES_CORE_TOOLS` at line 31) includes ~25 tools by default, including `image_generate` (line 39). Platform-specific toolsets (e.g. `hermes-telegram`, `hermes-discord`) all include `_HERMES_CORE_TOOLS`.

If the tool IS in `_HERMES_CORE_TOOLS`, it's expected to be available by default.

### 2. Does the tool have a `check_fn`?

Tools are registered in `tools/registry.py` via `registry.register()`. The `check_fn` parameter is a callable that returns `bool` — if it returns `False`, the tool is excluded from `get_tool_definitions()` output even though it's registered.

To find a tool's `check_fn`: look at its `registry.register()` call (typically at the bottom of the tool file). Example:

```python
# tools/image_generation_tool.py line 1051
registry.register(
    name="image_generate",
    ...
    check_fn=check_image_generation_requirements,
)
```

### 3. What does the `check_fn` actually check?

Read the function body. Example: `check_image_generation_requirements()` (line 805 of `image_generation_tool.py`):

1. **First** checks FAL backend (`check_fal_api_key()` + `_load_fal_client()`) — returns True if FAL is configured
2. **Then** probes plugin-based providers: calls `_ensure_plugins_discovered()` then `list_providers()`, checks `provider.is_available()` on each

If neither FAL nor any plugin provider returns True, the tool is unavailable.

### 4. Are the plugin providers actually registered?

Check the image gen provider registry:

```python
from agent.image_gen_registry import list_providers, get_active_provider
providers = list_providers()
for p in providers:
    print(f'{p.name}: available={p.is_available()}')
active = get_active_provider()
```

If the expected provider isn't in the list, it was never registered. If it IS registered but `is_available()` returns False, check the provider's availability criteria (CDP endpoint, API key, script path).

### 5. If plugin IS installed but NOT registered — the gateway cache trap

This is the most common subtle failure. Plugin discovery (`discover_plugins()`) is called once per **gateway process** at startup. It is **idempotent by caching**:

```python
# plugins.py line 1037
if self._discovered and not force:
    return
```

When a user installs a plugin or updates config AFTER the gateway started, the plugin IS discovered but skips the `register()` call because `discover_and_load(force=False)` is a no-op after the first call. The manifest is recorded but the plugin is skipped with "not enabled in config" if the config didn't have `plugins.enabled` at discovery time, or the `register()` function was never called.

**The `/reset` command does NOT fix this.** The agent runs in the SAME gateway process (a thread, not a subprocess). A new AIAgent is created, but the plugin manager's `_discovered=True` flag persists in process memory. The agent's re-init calls `get_tool_definitions()` which calls `check_fn` which calls `_ensure_plugins_discovered()` which is a no-op.

**Solution:** Restart the gateway process so plugin discovery runs fresh.

### 6. Check gateway start time vs plugin install time

```bash
# Gateway start time
head -5 /opt/data/logs/gateway.log

# Plugin file timestamps
ls -la /opt/data/plugins/image_gen/<name>/plugin.yaml

# Config update time
ls -la /opt/data/config.yaml
```

If gateway is older than the plugin or config changes → stale cache.

### 7. Fresh-process verification

Run the checks in a completely fresh Python process (bypasses the gateway process cache):

```bash
python3 -c "
from hermes_cli.plugins import discover_plugins
discover_plugins(force=True)
from agent.image_gen_registry import list_providers, get_active_provider
for p in list_providers():
    print(f'{p.name}: available={p.is_available()}')
print(f'Active: {get_active_provider()}')
from tools.image_generation_tool import check_image_generation_requirements
print(f'check_fn result: {check_image_generation_requirements()}')
"
```

If this works but the session doesn't have the tool, the gateway cache is stale.

## Architecture Summary

```
gateway startup
  └─ discover_plugins()          ← scans plugins/ dirs, runs once
       └─ discover_and_load()    ← reads config.yaml, checks plugins.enabled
            └─ _load_plugin()    ← imports __init__.py, calls register(ctx)
                 └─ ctx.register_image_gen_provider(provider)  ← stores in registry

session /reset
  └─ new AIAgent()               ← same process, same cached plugin state
       └─ get_tool_definitions()
            └─ for each registered tool:
                 └─ check_fn()   ← tool availability check
                      └─ _ensure_plugins_discovered()  ← NO-OP (already discovered)
                           └─ list_providers()
                                └─ provider.is_available()

gateway restart
  └─ fresh discover_plugins()   ← picks up new plugins and config
```

## Key Files

| File | Role |
|---|---|
| `tools/registry.py` | Tool registration + `check_fn` evaluation |
| `toolsets.py` | Toolset definitions (`_HERMES_CORE_TOOLS`) |
| `tools/image_generation_tool.py` | `image_generate` tool + `check_image_generation_requirements()` |
| `agent/image_gen_registry.py` | Plugin provider registry + `get_active_provider()` |
| `agent/image_gen_provider.py` | `ImageGenProvider` base class |
| `hermes_cli/plugins.py` | Plugin discovery + `discover_and_load()` + `_ensure_plugins_discovered()` |
| `hermes_cli/tools_config.py` | Toolset config from `platform_toolsets` |
| `/opt/data/config.yaml` | `image_gen.provider` + `plugins.enabled` |
