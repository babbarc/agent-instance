---
name: use-cdp-protocol
description: "Load when you need raw CDP commands (browser_cdp tool) — JS eval, navigate preserving session, cookies, dialogs, screenshots, async eval patterns. For CDP CLI scripts, load run-cdp-scripts instead."
annotation: "Raw CDP commands: browser_cdp tool, methods, frame routing"
version: 1.1.0
author: Joy
license: MIT
metadata:
  hermes:
    tags: [CDP, Chrome DevTools Protocol, Browser, Automation]
    related_skills: [operate-browser, run-cdp-scripts, choose-web-tool]
---

# use-cdp-protocol — Raw CDP Commands

Use `browser_cdp(method, params, target_id, frame_id)` for raw CDP. Load `run-cdp-scripts` first for the CLI tools — only come here when you need protocol-level control.

## Critical: target_id vs frame_id

`target_id` = tab ID from `Target.getTargets()`. Required for page-level methods.
`frame_id` = cross-origin iframe ID from `browser_snapshot().frame_tree.children[]` where `is_oopif=true`.

Without `frame_id`, each `browser_cdp` call is stateless — sessions don't persist.

## Essential Methods

### List tabs
```python
browser_cdp(method="Target.getTargets", params={})
# → {"targetInfos": [{"targetId": "...", "title": "...", "url": "..."}]}
```

### Run JavaScript
```python
r = browser_cdp(method="Runtime.evaluate", params={"expression": "...", "returnByValue": True}, target_id=tab_id)
# Value at r["result"]["result"]["value"]
```
Key expressions: `document.title`, `document.body.innerText`, `JSON.stringify(Array.from(document.querySelectorAll('a')).map(a => ({href: a.href, text: a.textContent.trim()})))`.

### Navigate (preserve session)
```python
browser_cdp(method="Page.navigate", params={"url": "https://..."}, target_id=tab_id)
```
Use instead of `browser_navigate` which creates a fresh isolated context every call.

### Handle dialogs
```python
browser_cdp(method="Page.handleJavaScriptDialog", params={"accept": True}, target_id=tab_id)
# For prompt(): params={"accept": True, "promptText": "my response"}
```
Prefer `browser_dialog(action)` when available.

### Get/set cookies
```python
browser_cdp(method="Network.enable", params={})                                          # must call first
browser_cdp(method="Network.getAllCookies", params={})
browser_cdp(method="Network.setCookie", params={"name": "...", "value": "...", "domain": ".example.com", "path": "/"})
```
**Gotcha:** `getAllCookies()` silently returns `[]` if `Network.enable()` wasn't called first.

### Screenshot
```python
r = browser_cdp(method="Page.captureScreenshot", params={"format": "png", "fromSurface": True}, target_id=tab_id)
# r["result"]["data"] = base64 PNG
```
For clipped (element-only): get `el.getBoundingClientRect()` via JS, pass `clip` param.

### Type into input (SPA-safe)
```python
browser_cdp(method="Runtime.evaluate", params={"expression": """
(() => {
    const el = document.querySelector('input[name="email"]');
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(el, 'user@example.com');
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
})()
""", "returnByValue": True}, target_id=tab_id)
```

### Set viewport
```python
browser_cdp(method="Emulation.setDeviceMetricsOverride", params={"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False}, target_id=tab_id)
```

## Async Eval (CDP WebSocket scripts only)

`Runtime.evaluate` returns immediately — doesn't await Promises. Use **fire → drain → poll → read**:

```javascript
ws.send({id: 10, method: 'Runtime.evaluate', params: {expression: `
(async function() { window._r = null; window._ready = false;
    window._r = await someLongOperation(); window._ready = true; })()`}})
// Drain id=10 → poll window._ready → read window._r
```

Use `run-cdp-scripts`'s `cdp-eval.py --async` instead of writing raw WebSocket code.

## Blob URL Download (SPA images)

`fetch(blobUrl)` fails (CORS). Use `new Image()` → canvas:
```javascript
var img = new Image();
await new Promise(r => { img.onload = r; img.src = blobUrl; });
var c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = img.naturalHeight;
c.getContext('2d').drawImage(img, 0, 0);
var b64 = c.toDataURL('image/jpeg', 0.92).split(',')[1];
```
CDP's returnByValue drops strings >~200KB — read in chunks.

## Persistent Session Pattern

```python
browser_navigate("https://example.com/login")                    # open site
tabs = browser_cdp(method="Target.getTargets", params={})
tab_id = tabs["targetInfos"][0]["targetId"]                      # save tab
# ... login via browser_type/browser_click ...
browser_cdp(method="Page.navigate", params={"url": "https://example.com/account"}, target_id=tab_id)  # stays logged in
```

## Pitfalls

- **.result.value nesting** — Always `result["result"]["value"]`.
- **Network cookie footgun** — `getAllCookies()` returns `[]` if `Network.enable()` not called first.
- **Context isolation** — `browser_navigate` resets cookies. Use `Page.navigate` with saved target_id.
- **Chrome 148+** blocks remote debugging on default data dir. Use non-default path.
- **Never put secrets in tool params** — leaks to permanent record. Pipe via `pass-to` (see credential-pre-flight).
