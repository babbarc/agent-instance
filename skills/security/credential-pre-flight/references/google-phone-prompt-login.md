# Google Phone-Prompt Login (CDP Flow)

For Google services that trigger 2FA phone notification (Gemini, Gmail web, Google Cloud Console), the password + phone-prompt flow is the most reliable automation path. Avoids TOTP entry entirely.

## Prerequisites

- Browser running on CDP port 3333 (Hermes default)
- `pass` entry with `login:` field and password on line 1
- Pass path splitting already fixed (see `references/pass-to-path-splitting-pitfall.md`)

## Step-by-Step Flow

### 1. Start with a Fresh Browser Tab

```python
# Navigate to the target Google service
browser_cdp(
    method="Page.navigate",
    params={"url": "https://gemini.google.com"},
    target_id="TAB_ID"
)
```

### 2. Click "Sign in"

```python
browser_cdp(
    method="Runtime.evaluate",
    params={
        "expression": "(()=>{const btns=document.querySelectorAll('button');for(const b of btns){if(b.textContent.trim()==='Sign in'){b.click();return 'CLICKED'}}return 'NOT_FOUND'})()",
        "returnByValue": True
    },
    target_id="TAB_ID"
)
```

### 3. Enter Email

Use CDP `Runtime.evaluate` with native value setter + event dispatch (SPA-safe):

```python
browser_cdp(
    method="Runtime.evaluate",
    params={
        "expression": "(()=>{const el=document.querySelector('input[type=\"email\"]');if(!el)return 'NOT_FOUND';const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;s.call(el,'pallavvasa');el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));return 'OK'})()",
        "returnByValue": True
    },
    target_id="TAB_ID"
)
```

Click Next:

```python
browser_cdp(
    method="Runtime.evaluate",
    params={
        "expression": "(()=>{const btn=document.querySelector('#identifierNext button');if(!btn)return 'NOT_FOUND';btn.click();return 'OK'})()",
        "returnByValue": True
    },
    target_id="TAB_ID"
)
```

### 4. Inject Password via pass-to (Zero Exposure)

Do NOT use `browser_cdp(params={"text":"password"})` — this leaks into the tool-call record. Instead, pipe from `pass-to` in a standalone Python script:

```bash
pass-to pallav/accounts.google.com -- python3 -c "
import sys, json, asyncio, websockets, urllib.request

password = sys.stdin.read().strip().split('\n')[0]

async def inject():
    resp = urllib.request.urlopen('http://localhost:3333/json', timeout=5)
    targets = json.loads(resp.read())
    page_target = next((t for t in targets if t.get('type') == 'page' and 'accounts.google.com' in t.get('url', '')), None)
    ws_url = page_target['webSocketDebuggerUrl']

    async with websockets.connect(ws_url) as ws:
        safe = json.dumps(password)
        expr = f'''(()=>{{const el=document.querySelector('input[type=\"password\"]');if(!el)return 'NOT_FOUND';const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;s.call(el,{safe});el.dispatchEvent(new Event('input',{{bubbles:true}}));el.dispatchEvent(new Event('change',{{bubbles:true}}));return 'OK'}})()'''
        msg = json.dumps({'id':1,'method':'Runtime.evaluate','params':{'expression':expr,'returnByValue':True}})
        await ws.send(msg)
        resp = json.loads(await ws.recv())
        result = resp.get('result',{}).get('result',{}).get('value','UNKNOWN')
        print(result)

asyncio.run(inject())
"
```

**Key:** `python3` receives the password on stdin from `pass-to`. The script opens its own CDP WebSocket, injects the password, and exits. The password never appears in any Hermes tool parameter.

### 5. Click Next on Password

```python
browser_cdp(
    method="Runtime.evaluate",
    params={
        "expression": "(()=>{const btn=document.querySelector('#passwordNext button');if(!btn)return 'NOT_FOUND';btn.click();return 'OK'})()",
        "returnByValue": True
    },
    target_id="TAB_ID"
)
```

### 6. Handle Phone Prompt (2FA)

If Google sends a phone notification, the page shows "Open the Gmail app on [device]" with a "Resend it" link. **The user must tap "Yes" on their phone.** No further CDP interaction needed — just wait and inform the user.

Check page state:

```python
# Verify we hit the phone prompt page
result = browser_cdp(
    method="Runtime.evaluate",
    params={
        "expression": "JSON.stringify({url: window.location.href, title: document.title, bodyPreview: document.body.innerText.substring(0,500).trim()})",
        "returnByValue": True
    },
    target_id="TAB_ID"
)
```

Look for `"2-Step Verification"` in the title and `"Google sent a notification"` in the body.

### 7. After User Approves — Navigate to Target

```python
browser_cdp(
    method="Page.navigate",
    params={"url": "https://gemini.google.com"},
    target_id="TAB_ID"
)
```

### 8. Verify Login

```python
result = browser_cdp(
    method="Runtime.evaluate",
    params={
        "expression": "JSON.stringify({hasSignIn: document.body.innerText.includes('Sign in'), bodyPreview: document.body.innerText.substring(0,200).trim()})",
        "returnByValue": True
    },
    target_id="TAB_ID"
)
# hasSignIn should be false if logged in
```

## Pitfalls

- **Password stale in pass** — if Google rejects the password, tell the user to update it in pass and run `cd ~/.password-store && git pull --rebase origin master` to fetch the update
- **SPA click resistance** — Google's React login sometimes ignores `element.click()` via CDP. If the email/password entry doesn't stick, try `MouseEvent` dispatch instead: `new MouseEvent('click', {bubbles:true,cancelable:true,view:window})`
- **Recovery info page** — after phone approval, Google may redirect to `gds.google.com/web/recoveryoptions` (recovery info prompt). Navigate directly to your target URL
- **Target IDs expire** — CDP page target IDs change when the tab navigates. If a `target_id` returns "No target with given id found", re-fetch via `Target.getTargets`
- **Page-level vs browser-level WS** — The scripts above connect to the page-level WebSocket URL from `/json` (e.g., `ws://localhost:3333/devtools/page/...`). This automatically scopes commands to that tab, so `Runtime.evaluate` does NOT need a `sessionId`
