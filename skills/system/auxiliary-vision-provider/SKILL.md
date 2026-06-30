---
name: auxiliary-vision-provider
description: "Set up a custom auxiliary vision provider for Hermes — an OpenAI-compatible bridge that routes vision requests through local tools and cloud fallbacks."
annotation: "Custom auxiliary vision provider for Hermes — setup guide"
---

# Auxiliary Vision Provider

Set up a custom vision pipeline when your active model lacks native vision support. The pattern: a lightweight HTTP server with an OpenAI-compatible `/v1/chat/completions` endpoint that extracts images from requests, runs a primary vision tool (local), and falls back to an API.

## When to Load

- `vision_analyze` is not in your toolset — the model lacks native vision
- You want images processed locally (privacy) instead of sent to the main provider
- You need a fallback chain for reliability

## Architecture

```
vision_analyze → Hermes → auxiliary.vision (custom provider) →
    local HTTP server → primary tool (e.g. Claude Code CLI)
                      → fallback API (e.g. Gemini OpenAI-compat endpoint)
```

## Steps

### 1. Create the Bridge Server

Write a Python `http.server`-based server on `127.0.0.1` (localhost only). It must implement:

**`POST /v1/chat/completions`** — Accept OpenAI-format requests:
- Parse `messages[].content` for `image_url` items — supports `data:` base64 URLs and `file://` paths
- Extract image bytes, MIME type, and text prompt
- Return standard OpenAI response shape: `{"choices": [{"message": {"content": "..."}}]}`

**`GET /health`** — Return `{"status": "ok"}` for watchdog checks.

### 2. Implement the Primary Provider

Write a handler that receives an OpenAI-format image request, extracts the image bytes, and sends them to a local vision-capable tool. The bridge converts between OpenAI chat completions format and whatever the local tool expects.

```python
# Pseudocode — adapt to your chosen local vision tool
image_bytes, mime_type, prompt = extract_image_from_request(request)
result = call_local_vision(image_bytes, prompt)  # returns text
return {"choices": [{"message": {"content": result}}]}
```

### 3. Implement a Fallback Provider

When the primary fails, fall back to a cloud API. Example — **Gemini OpenAI-compatible endpoint:**

```python
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
```

Send a standard OpenAI chat completion POST with the image as a `data:` URL. Load the API key from a secure source at startup — never hardcode it.

**Model name hint:** The OpenAI-compatible endpoint accepts bare model IDs like `gemini-2.5-flash` (no `models/` prefix needed for chat completions).

### 4. Configure Hermes

```bash
hermes config set auxiliary.vision.provider custom
hermes config set auxiliary.vision.base_url http://127.0.0.1:9877/v1
hermes config set auxiliary.vision.api_key unused
```

The `api_key` field is required by the schema but unused by a local bridge.

### 5. Start the Bridge

```bash
nohup python3 /path/to/bridge.py > /tmp/vision-bridge.log 2>&1 &
```

Logs go to stderr — always redirect both stdout and stderr to a file.

### 6. Set Up Watchdog (Reliability)

Create a watchdog script that checks `/health` and restarts the bridge if missing:

```bash
#!/bin/bash
if ! curl -sf http://127.0.0.1:9877/health; then
    nohup python3 /path/to/bridge.py > /tmp/vision-bridge.log 2>&1 &
fi
```

Schedule via cron:
```bash
cronjob create "every 3h" --script /path/to/watchdog.sh --no_agent
```

### 7. Verify

Send an image via `vision_analyze` and check the bridge logs to confirm which provider handled the request.

## Pitfalls

- **Logs go to stderr** — the `http.server.BaseHTTPRequestHandler` uses stderr. Always redirect both fd 1 and 2 to a log file on startup.
- **vision_analyze sends file:// URLs** — the bridge must handle `image_url` values beginning with `file://` (absolute paths), not just `data:` base64.
- **pass store is git-backed** — after a `pass git pull`, API keys may appear but are decrypted correctly. `pass show <path>` works transparently.
- **API key from pass** — load in `main()` at startup, validate, and log whether fallback is enabled. Don't load lazily on each request.
- **Watchdog preserves password-store decryption** — if the bridge dies, the watchdog restarts it, which re-runs the pass lookup. No need to re-enter GPG keys.
- **Bridge process is fragile** — no built-in crash recovery except the watchdog cron. Test the health endpoint after any code change.
