---
name: gemini-web-images
description: Companion reference for the gemini-web image provider — prompt strategy (format gate, orientation), follow-up modifications, and troubleshooting.
annotation: "Gemini-web image provider: prompt structure, capabilities"
---

# Gemini Web Images

## Prerequisites

- Browser CDP endpoint running on `localhost:3333`
- Google credentials in pass at `pallav/accounts.google.com`
- Persistent volume `hermes-browser-data` mounted (survives container restarts)
- After a browser restart: navigate to `https://gemini.google.com/app` first so scripts can discover the page

## Workflow Hierarchy (pick the right tier)

### Tier 1: `image_generate` tool (via gemini-web plugin)
When `image_gen.provider: gemini-web` is configured, this wraps navigate → prompt → poll → download in one call.

- **Use for:** first-time generation, one-off designs
- **Don't use for:** follow-up modifications, debugging steps

If the plugin is enabled but `image_generate` isn't in your tool list: the tool registers at session init only. Suggest a session restart (`/reset`). Offer fallback to Tier 2 if restart isn't practical.

### Tier 2: `gemini-generate-image.py` via terminal
```bash
cd /opt/data/scripts && python3 gemini-generate-image.py \
  "Your prompt" --output /tmp/result.jpg --timeout 120
```

Key flags:
- `--follow-up` — sends modification in the CURRENT thread (no navigation). Essential for iterative refinement.
- `--output`, `--timeout`, `--quality` — per-call control

- **Use for:** follow-up modifications, or when the plugin isn't active

### Tier 3: Modular scripts (debug only)
```bash
cd /opt/data/scripts
python3 gemini-thread-new.py --images
python3 gemini-prompt-send.py "Your prompt"
python3 gemini-response-read.py --timeout 120
python3 gemini-image-download.py --output /tmp/out.jpg
```

- **Use when Tiers 1-2 fail** and you need to isolate which step broke
- Never use ad-hoc CDP commands (`Runtime.evaluate`, `browser_cdp`) — scripts are more reliable

## Script Reference

All scripts live in `/opt/data/scripts/` and output `STATUS:OK <json>` to stdout (stderr for human progress). See `references/cdp-communication-patterns.md` for output format details.

| Script | Purpose |
|--------|---------|
| `gemini-generate-image.py` | One-shot: navigate → prompt → wait → download. `--follow-up` for in-thread modifications. Preferred workflow. |
| `gemini-google-login.py` | Google OAuth flow (email → password → phone prompt). After first login, session persists on volume. |
| `gemini-prompt-send.py` | Send a prompt to Gemini's chat input (human-like typing via CDP) |
| `gemini-response-read.py` | Poll for response completion |
| `gemini-thread-new.py` | Start fresh conversation. `--images` for image gen page. |
| `gemini-thread-open.py` | Open conversation thread by title. `--list` shows threads, `--last` opens most recent. |
| `gemini-thread-info.py` | Count turns and images in a thread. `--verbose` for per-turn details. |
| `gemini-chat-list.py` | List recent chats from the sidebar |
| `gemini-image-download.py` | Download generated image from a thread. `--image N` (1=oldest), omit for newest. `--last` alias. |
| `gemini_utils.py` / `cdp_utils.py` | Shared CDP utilities. All scripts import from these. |

## Debugging CDP Scripts

**Before debugging any script failure, verify the check_fn prerequisites** — browser container running (`podman ps --filter name=hermes-browser`), CDP endpoint reachable at `http://localhost:3333/json`, and a Gemini page target exists.

When a script returns empty text, partial responses, or hangs until timeout:

1. **Check if it uses `gemini_utils` or `cdp_utils` evaluate()** — run `grep 'from.*import.*evaluate' /opt/data/scripts/<script>.py`. If it imports from either utility module, the `evaluate()` function is broken — it reads the first WebSocket message without checking if the message ID matches the command ID, so spontaneous CDP events (`Runtime.consoleAPICalled`, etc.) can arrive first and cause a silent `None` return.

2. **Run the combined script** (`gemini-prompt-and-read.py`) first when debugging text-response issues — it has the only correct `evaluate()` implementation with an ID-matching loop. If this works but modular scripts don't, the bug is in the shared utilities.

3. **If the combined script itself fails**: check whether `Runtime.evaluate` is returning CDP exceptions (page context not ready). The correct `evaluate()` still returns `None` on `exceptionDetails` without surfacing the error. See `references/cdp-silent-failure-diagnosis.md` for the full diagnosis checklist and fix pattern.

4. **Check CDP target selection**: `find_or_create_gemini_page()` returns the first Gemini page found by URL substring match. If multiple tabs are open, a follow-up script may connect to the wrong one. Run `cdp-utils.discover_targets()` to list all available pages.

See `references/cdp-communication-patterns.md` for the correct CDP WebSocket message-matching pattern and `references/cdp-silent-failure-diagnosis.md` for the step-by-step failure diagnosis checklist (including which scripts are affected and the fix to apply).

## Prompt Strategy

### Format gate — declare output format in first 30 words
Gemini defaults to 3D card-on-table mockup mode when it sees words like "card" or "invitation." Set the mode explicitly in the first sentence.

**For flat graphic (design filling the frame) — default choice:**
> "Create image. NOT a card mockup and NOT a photograph of a card on a surface. The entire image canvas IS the [design] — fill it edge to edge with zero margins, zero borders, zero background visible. This is a FLAT GRAPHIC DESIGN, not a physical card. ... NO CARD EDGES. NO MARGINS/PADDING. Full-bleed flat design."

**For mockup/lifestyle visual:**
Only when the user explicitly wants a physical-object render (card-on-table, framed print, etc.).

### Orientation — explicit in first sentence
Gemini defaults to 1024×559 landscape. For portrait: say **"PORTRAIT orientation (taller than wide)"** — just "portrait" alone is misinterpreted as portrait photo style.

Orientation is NOT fixable via follow-up. Start a fresh generation to change it.

### Content prompt — concise round 1, prescriptive round 2
**Round 1:** Style direction + content. Let Gemini compose the layout.
**Round 2 (--follow-up):** List exact text changes. Include "Keep everything else the same."

### Beware: follow-up treated as text query
If the follow-up prompt doesn't signal "generate an image" strongly enough, Gemini responds with text instead. Open with **"Regenerate this [design] image with the following changes:"** — avoid passive "Modify" alone.

### The richness gap
"Minimalist" produces near-empty designs. If the user says "too simple", add rich descriptors alongside the minimalist constraint: ornate borders, intricate botanical art, sophisticated typography.

### Iterative refinement protocol
1. **Fresh generation** for structural changes (orientation, format switch).
2. **Follow-up** for text/content changes (preserves existing artwork).
3. When follow-up doesn't produce a new image: check `gemini-thread-info.py --verbose` to see if image count increased. If yes, download explicitly with `--image 2`. If no, regenerate with a stronger image-signal prompt.

## Common Pitfalls

- **Fresh generation creates a new thread each time.** Sequential fresh generations accumulate unreachable threads. For iteration on the same design, use `--follow-up`. Only fresh-generate for genuinely different directions.

- **STATUS:NO_PAGE after browser restart.** No Gemini page target exists yet. Fix: `browser_navigate("https://gemini.google.com/app")` first.

- **--follow-up downloads the first image, not the new one.** Always md5-compare the downloaded file against the previous one. If same: download explicitly with `gemini-image-download.py --thread "Title" --image 2 --output /tmp/new.jpg` or `--last`.

- **STATUS:TIMEOUT but image was generated.** Don't retry the script — it creates another fresh thread. Check Recent threads in the Gemini sidebar, open the matching thread, download from there.

- **CDP target mismatch.** After `browser_navigate`, scripts and browser tools may see different targets. When browser tools return empty results: call `Target.getTargets` via `browser_cdp` to find the real Gemini page target.

- **Follow-up can't fix orientation.** If the user corrects orientation, do NOT use `--follow-up` — it inherits the original aspect ratio. Start fresh.

- **Don't do ad-hoc CDP when scripts exist.** Before writing `Runtime.evaluate` expressions targeting Gemini's DOM, check if a script already handles it. If not, create a script first.
