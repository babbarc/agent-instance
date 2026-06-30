# Gemini Script Debugging — 10 Jun 2026 Session

## Symptom: Script Reports "Prompt Sent" but Times Out

The script navigates to `/images`, types the prompt, clicks send, returns "Prompt sent, waiting for image...", then `STATUS:TIMEOUT` after 120s. But the page is still on `/images` with the prompt text in the editor — the send never actually triggered.

### Root Cause 1: textContent doesn't trigger React

The `send_prompt` function used `el.textContent = text` + `dispatchEvent(new Event('input'))`. Quill.js (Gemini's editor) does NOT react to this — React's synthetic event system listens for `beforeinput` events with specific `inputType`, not arbitrary `input` events on `textContent` changes.

**Fix:** Replace with CDP `Input.insertText` which dispatches the correct `beforeinput` event at the browser compositor level.

### Root Cause 2: JS b.click() doesn't trigger React handler

Even when `textContent` worked (visually appearing in the editor), `b.click()` on the "Send message" button didn't submit. The button looked enabled (no `disabled` attribute) but React's onClick handler checked internal state — if React state didn't register a non-empty input, the handler was a no-op.

**Fix:** Use CDP `Input.dispatchKeyEvent` for Enter key. This is a browser-level keystroke that the page handles the same way as a real user pressing Enter. Works even after the page navigates from `/images` to `/app/<id>`.

### Detection Debugging

Use this pattern to inspect the page state when the script fails:

```python
import asyncio, json, websockets

async def inspect():
    async with websockets.connect(ws_url) as ws:
        def ev(expr, mid=1):
            return json.dumps({"id": mid, "method": "Runtime.evaluate",
                "params": {"expression": expr, "returnByValue": True}})

        # Check all buttons
        await ws.send(ev("""JSON.stringify(
            Array.from(document.querySelectorAll('button')).map(b => ({
                label: b.getAttribute('aria-label')||'',
                disabled: b.disabled,
                visible: b.offsetParent !== null
            }))
        )""", 1))
        r = json.loads(await ws.recv())
        # ... parse and inspect

        # Check editor state
        await ws.send(ev("""(function(){
            const el = document.querySelector('.ql-editor');
            if(!el) return 'NO_EDITOR';
            return JSON.stringify({
                text: el.textContent.substring(0,100),
                html: el.innerHTML.substring(0,100)
            });
        })()""", 2))
        r = json.loads(await ws.recv())

        # Check for large/blob/images
        await ws.send(ev("""JSON.stringify(
            Array.from(document.querySelectorAll('img'))
                .filter(i => i.naturalWidth > 100)
                .map(i => ({src: i.src.substring(0,80), alt: i.alt.substring(0,40), w: i.naturalWidth}))
        )""", 3))
```

### Important: `send_cdp` and `evaluate` Must Skip Events

After `Input.insertText`, Chrome fires CDP event messages (`Runtime.consoleAPICalled`, `Log.entryAdded`) before the response. If `evaluate` does a single `ws.recv()` it gets an event with no `id` field → `KeyError: 'result'`. If `send_cdp` does a single `ws.recv()` it may get a response with a different `id` from a previous command.

**Both functions MUST loop until they find a message whose `id` matches the command they sent.**

### Key: browser_navigate Creates New Tab

`browser_navigate` may create a **new browser tab** with a different CDP targetId than the gemini page. The scripts discover targets by URL pattern and may find the wrong target. Always verify:

```python
for t in targets:
    if t.get('type') == 'page' and 'gemini.google.com' in t.get('url', ''):
        print(f"targetId={t['id'][:16]} url={t['url'][:80]}")
```

### How to reliably test the pipeline

1. Navigate to a fresh `/images` page via `browser_navigate("https://gemini.google.com/images")`
2. Wait 5-8s for full page load
3. Run the script: `cd /opt/data/scripts && python3 gemini-generate-image.py "Your prompt" --output /tmp/out.jpg --timeout 150`
4. If it times out: inspect the page state to determine which step failed

### Successful end-to-end flow (verified 10 Jun 2026)

```
browser_navigate(/images)
  → Input.insertText(prompt) via CDP (msg_id=21)
  → Input.dispatchKeyEvent(Enter) via CDP (msg_id=22-23)
  → poll_for_image() with multi-signal detection
  → canvas download → STATUS:OK /path/to/image.jpg

Output: 1024x1024 square, 572x1024 portrait
Models: Nano Banana 2 (Flash mode), Imagen
Generated conversations appear under /app/<id> in sidebar
```
