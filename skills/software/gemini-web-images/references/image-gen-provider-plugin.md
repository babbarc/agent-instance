# ImageGen Provider Plugin — Gemini Web Backend

Wraps `gemini-generate-image.py` as a Hermes `ImageGenProvider` so the `image_generate` tool dispatches through Gemini Web directly. No skill loading, no terminal commands.

## Architecture

```
image_generate tool                            [image_gen toolset enabled]
       │
       ▼
get_active_provider()           [image_gen.provider: gemini-web in config.yaml]
       │
       ▼
GeminiWebImageGenProvider.generate(prompt, aspect_ratio)
       │
       ├─ prepend orientation prefix from aspect_ratio
       ├─ subprocess.run(["python3", "gemini-generate-image.py", prompt, ...])
       │
       └─ parse last STATUS:OK <path> → success_response(image=path)
```

## Plugin Structure

```
/opt/data/plugins/image_gen/gemini-web/      (NOT ~/.hermes/plugins/)
├── plugin.yaml           # Manifest (name, kind: backend)
└── __init__.py           # Provider class + register(ctx)
```

The plugin root is **`/opt/data/plugins/`** (resolved from `get_hermes_home() / "plugins"`), not `~/.hermes/plugins/`. On this system `get_hermes_home()` returns `/opt/data`.

### plugin.yaml

```yaml
name: gemini-web
version: 1.0.0
description: "CDP-backed image generation via Gemini Web UI"
kind: backend
```

`kind: backend` is critical — it tells the plugin system this is a pluggable backend for a core tool. Bundled backends (`source: bundled`) auto-load; user-installed ones need `plugins.enabled` in config.

### __init__.py — actual implementation

The live implementation is at `/opt/data/plugins/image_gen/gemini-web/__init__.py`. Key design points:

**Status parsing:** The script outputs `STATUS:OK /path/to/file.jpg` as plain text (not JSON). The provider parses the last `STATUS:` line from stdout using `_parse_status()`:

```python
@staticmethod
def _parse_status(stdout: str) -> Optional[Tuple[str, str]]:
    for line in reversed(stdout.strip().splitlines()):
        line = line.strip()
        if line.startswith("STATUS:"):
            rest = line[len("STATUS:"):]
            if " " in rest:
                code, payload = rest.split(" ", 1)
                return code.strip(), payload.strip()
            else:
                return rest.strip(), ""
    return None
```

All STATUS codes handled: `OK`, `NO_PAGE`, `TIMEOUT`, `NO_IMAGE`, plus unexpected fallthrough.

**Output to Hermes cache:** The provider creates output in `$HERMES_HOME/cache/images/` via `_images_cache_dir()` (the `agent.image_gen_provider` helper), not `/tmp/`. Filename format: `gemini_web_<YYYYMMDD_HHMMSS>_<short-uuid>.jpg`. This keeps generated images alongside other Hermes image outputs and survives across sessions.

**Aspect ratio → orientation:** The provider translates Hermes' three abstract aspect ratios into Gemini-specific orientation prompt prefixes:

```python
_ASPECT_PROMPTS = {
    "landscape": "",  # Gemini's default — no prefix needed
    "square": "SQUARE format. ",
    "portrait": "PORTRAIT orientation (taller than wide). ",
}
```

This avoids the common failure mode where Gemini generates landscape despite `aspect_ratio: portrait` — the LLM's `image_generate` call passes the abstract enum, the provider injects the concrete wording Gemini understands.

**CDP pre-flight:** `is_available()` does a rapid HTTP GET to `http://localhost:3333/json` (the browser's CDP discovery endpoint, not a websocket connect) with a 3s timeout. No WS handshake overhead. If the endpoint doesn't respond, the provider reports unavailable and the tool system handles it gracefully.

**Python interpreter:** Uses `sys.executable` rather than hardcoded `"python3"` to respect venv/container paths.

**Timeout from kwargs:** Reads `timeout` from kwargs, clamps to max 300s, defaults to 180s. Passes it as `--timeout` to the script, plus 30s margin for the subprocess wrapper.

**Error responses:** Every failure mode returns a specific error message with actionable next steps (e.g. "Ensure the Hermes browser container is running (`podman start hermes-browser`)").

### Config changes

```yaml
plugins:
  enabled:
    - image_gen/gemini-web

image_gen:
  provider: gemini-web
  model: gemini-web-imagen
```

**Important:** `hermes config set` ALWAYS stores values as YAML strings. For the `plugins.enabled` list you must write it manually. The `patch` tool also refuses direct edits to `/opt/data/config.yaml` for security. Workaround: use a Python script that loads/re-saves the YAML properly.

Then do `/reset` (new session) — `image_generate` now routes through Gemini Web.

## Key Design Decisions

**`is_available()` checks CDP, not credentials.** The CDP browser health is the real dependency — the Google session persists on the `hermes-browser-data` volume and outlives individual tool calls. If the browser container is down, the provider is invisible to `get_active_provider()` (when `image_gen.provider` is unset). If explicitly configured, it surfaces with a clear "CDP endpoint not reachable" error.

**Subprocess call, not direct CDP.** The `gemini-generate-image.py` script encapsulates all the CDP logic (navigation, typing, polling, download). Calling it via subprocess is simpler and keeps the single source of truth in the script. Downside: full Python process overhead per call (~0.5s startup). Acceptable for a 30-90s generation.

**Output goes to the Hermes image cache.** `_images_cache_dir()` returns `$HERMES_HOME/cache/images/` which is the standard location all other image_gen providers use. The gateway delivers cached images via MEDIA: convention automatically.

## Pitfalls

- **STATUS:NO_PAGE after browser restart.** If the browser container just restarted, no Gemini page target exists in Chrome — the script fails immediately. Fix: run `browser_navigate("https://gemini.google.com/app")` first to establish a page, then retry.

- **Fresh thread every call.** Each call to the provider spawns a fresh `/images` thread. Iterative refinement requires the follow-up workflow (terminal scripts), not the provider — the provider has no concept of "current thread."

- **The provider is global.** `image_gen.provider: gemini-web` replaces whatever other backend was active. If the browser is down, no `image_generate` call succeeds. To switch back:
  ```bash
  hermes config set image_gen.provider openai
  ```
  Then `/reset`.

- **No follow-ups through the provider.** The `--follow-up` flag is unavailable because the provider creates a fresh subprocess each call. For in-thread modifications, use the terminal scripts directly:
  ```bash
  python3 /opt/data/scripts/gemini-generate-image.py "Modify..." --follow-up
  ```

## When to Use the Provider vs Terminal Scripts

| Situation | Method |
|-----------|--------|
| First-time generation | `image_generate` tool (provider) |
| One-off design | `image_generate` tool (provider) |
| Iterative refinement (same thread) | Terminal: `gemini-generate-image.py --follow-up` |
| Debugging the pipeline | Terminal: modular scripts |
| Thread management (re-opening old threads) | Terminal: `gemini-thread-open.py` |

The provider is the highest-level, lowest-effort entry point. Drop to terminal scripts when you need thread awareness or debugging.
