# CDP Communication Patterns

## WebSocket Message Matching

Every CDP command sends a JSON message with an `id` field. Chrome may push spontaneous events to the WebSocket between command and response: `Runtime.consoleAPICalled`, `Log.entryAdded`, `Network.requestWillBeSent`, etc. These have no `id` field, or a different `id` than the command.

**Always loop until you find a message whose `id` matches your command:**

```python
async def evaluate(ws, expression, msg_id=1):
    msg = json.dumps({"id": msg_id, "method": "Runtime.evaluate",
                      "params": {"expression": expression, "returnByValue": True}})
    await ws.send(msg)
    while True:
        resp = json.loads(await ws.recv())
        if 'id' in resp and resp.get('id') == msg_id:
            result = resp.get('result', {})
            # CDP can return exceptionDetails (page context not ready, etc.)
            # instead of a normal result — check to avoid silent None returns.
            if 'exceptionDetails' in result:
                print(f"CDP evaluate exception: {result['exceptionDetails'].get('text', 'unknown')}",
                      file=sys.stderr)
                return None
            return result.get('result', {}).get('value')


async def send_cdp(ws, method, params=None, msg_id=1):
    msg = json.dumps({"id": msg_id, "method": method, "params": params or {}})
    await ws.send(msg)
    while True:
        resp = json.loads(await ws.recv())
        if 'id' in resp and resp.get('id') == msg_id:
            return resp.get('result', {})
```

**Without this:** `KeyError: 'result'` on Runtime.evaluate responses, or `send_cdp` returns `None`. The script may report "prompt sent" but actually timed out because the CDP call silently failed.

This applies to all gemini scripts that use CDP WebSocket communication. Both `gemini-generate-image.py` (inline helpers) and `cdp_utils.py` (shared module) need this pattern.

## Quill/React Text Input Reliability

**DO NOT use `el.textContent = text + dispatchEvent(new Event('input'))` for modern React/Quill editors.**

Gemini uses a Quill.js contenteditable editor. Setting `textContent` directly and dispatching synthetic `input`/`change` events does NOT trigger React's synthetic event system. The text appears in the DOM but React doesn't register it — the send button stays disabled.

**Reliable approach — use CDP `Input.insertText`:**

```python
# 1. Focus and clear the editor via JS
await evaluate(ws, """
    (function() {
        const el = document.querySelector('.ql-editor');
        if (!el) return 'NOT_FOUND';
        el.focus();
        el.textContent = '';
        el.dispatchEvent(new Event('input', {bubbles: true}));
        return 'FOUND';
    })()
""", msg_id=20)

# 2. Type the text via CDP Input.insertText (browser-level, triggers ALL events)
await send_cdp(ws, 'Input.insertText', {'text': prompt}, msg_id=21)
await asyncio.sleep(1.2)  # Let React process

# 3. Submit via CDP Input.dispatchKeyEvent for Enter (NOT JS button click)
await send_cdp(ws, 'Input.dispatchKeyEvent', {
    'type': 'rawKeyDown', 'windowsVirtualKeyCode': 13,
    'key': 'Enter', 'code': 'Enter'
}, msg_id=22)
await asyncio.sleep(0.1)
await send_cdp(ws, 'Input.dispatchKeyEvent', {
    'type': 'keyUp', 'windowsVirtualKeyCode': 13,
    'key': 'Enter', 'code': 'Enter'
}, msg_id=23)
```

**Why it works:** `Input.insertText` dispatches proper `beforeinput` events with `inputType: 'insertText'` at the browser compositor level — the exact event flow React and Quill listen for.

**Why JS button click (`b.click()`) is unreliable:** The send button's React onClick handler checks internal state. If React hasn't registered the text input, the click lands on a button that's visually enabled but functionally inert.

**Fallback:** Always try CDP `dispatchKeyEvent` for Enter FIRST, then JS button click as a backup.

**`document.execCommand('insertText')`** is deprecated in Chrome 130+ — don't use it.

## Image Detection: Multi-Signal with gstatic.com Exclusion

Distinguish AI-generated images from UI chrome (profile pics, template thumbnails, discovery icons):

```javascript
(function() {
    const imgs = document.querySelectorAll('img');
    for (let i = imgs.length - 1; i >= 0; i--) {
        const img = imgs[i];
        if (img.naturalWidth <= 0) continue;
        const src = img.src || '';
        const alt = img.alt || '';
        if (src.includes('gstatic.com')) continue;          // Exclude template/discovery thumbnails
        const isBlob = src.startsWith('blob:');             // In-memory rendered images (most reliable)
        const isCDN = src.includes('googleusercontent.com/'); // CDN-served after generation
        const hasLongAlt = alt.length > 40;                   // Descriptive AI alt text
        const isLarge = img.naturalWidth > 300;               // Bigger than UI chrome
        if (isBlob || (isCDN && isLarge) || (hasLongAlt && isLarge)) {
            return JSON.stringify({found: true, src, w: img.naturalWidth, h: img.naturalHeight});
        }
    }
    return JSON.stringify({found: false});
})()
```

**Signal hierarchy:**
1. `blob:` URL — gold standard. AI images always start as blob URLs when first rendered.
2. `googleusercontent.com/` + large size — CDN-cached after the page has been open a while.
3. Long descriptive alt text (>40 chars) + large size (>300px). Template thumbnails have short alts like "Origami" or "Bronze". Generated images have descriptions like "A breathtaking, vertical portrait photograph capturing a majestic dragon..."

**Exclude `gstatic.com` always.** Template thumbnails (240×320), discovery icons, and stock images all live there.

## `STATUS:OK <json>` Output Convention

Every script outputs one `STATUS:OK <json>` line to stdout as the last line. Stderr is for human-readable progress. This makes output machine-parseable:

```bash
python3 script.py | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d['status'])"
```

All scripts handle: `OK` (success with payload), and error codes: `NO_PAGE`, `TIMEOUT`, `NO_IMAGE`, `NOT_FOUND`.
