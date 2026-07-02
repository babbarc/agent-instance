#!/usr/bin/env python3
"""Secure CDP credential injector. Reads from pass store, injects via CDP WebSocket.
   Never exposes the secret to LLM context or tool-call params.

Usage:
    python3 cdp-pass-inject.py <pass-path> [css-selector]

The css-selector defaults to: input[type="password"]

Auto-discovers the CDP WebSocket URL from the browser running on port 3333.
Properly attaches to the page target (Target.attachToTarget) before injecting,
because Runtime.evaluate requires a sessionId, not a bare targetId, at the
browser-level WebSocket.

The secret flows: pass GPG → pipe → Python memory → CDP Runtime.evaluate
→ browser DOM. Never appears in Hermes tool-call params.

For Google OAuth-based login (preferred for Google services), see
references/oauth-cookie-injection.md in this skill — you can skip password
entry entirely by injecting session cookies from an OAuth access token.
"""
import subprocess, json, sys, asyncio, websockets, urllib.request

PASS_PATH = sys.argv[1] if len(sys.argv) > 1 else None
SELECTOR = sys.argv[2] if len(sys.argv) > 2 else 'input[type="password"]'

if not PASS_PATH:
    print("Usage: cdp-pass-inject.py <pass-path> [css-selector]", file=sys.stderr)
    sys.exit(1)


def discover_cdp_url():
    """Auto-discover CDP WebSocket URL from the running browser on port 3333."""
    try:
        resp = urllib.request.urlopen('http://localhost:3333/json/version', timeout=5)
        data = json.loads(resp.read())
        ws_url = data.get('webSocketDebuggerUrl')
        if ws_url:
            return ws_url
    except Exception as e:
        print(f"CDP discovery failed: {e}", file=sys.stderr)
    print("FAILED: CDP WebSocket URL not found. Is the browser running on port 3333?", file=sys.stderr)
    return None


async def main():
    ws_url = discover_cdp_url()
    if not ws_url:
        sys.exit(1)

    # Read credential from pass (subprocess, never in LLM context)
    secret = subprocess.run(
        ["pass-to", PASS_PATH, "--", "head", "-1"],
        capture_output=True, text=True
    ).stdout.strip()

    if not secret:
        print("FAILED: no secret from pass", file=sys.stderr)
        sys.exit(1)

    async with websockets.connect(ws_url) as ws:
        # Get targets
        await ws.send(json.dumps({"id": 1, "method": "Target.getTargets", "params": {}}))
        resp = json.loads(await ws.recv())

        # Find the first non-extension page
        target_id = None
        for t in resp["result"]["targetInfos"]:
            if t["type"] == "page" and t["url"].startswith("http"):
                target_id = t["targetId"]
                break

        if not target_id:
            print("FAILED: no suitable page target", file=sys.stderr)
            sys.exit(1)

        # Attach to the target to get a session (Runtime.evaluate needs sessionId
        # at the browser-level WebSocket, not bare targetId)
        # NOTE: attachToTarget at the browser-level WS returns the session via a
        # Target.attachedToTarget event notification, NOT as a direct response
        # with id=2. We must loop until we find it.
        await ws.send(json.dumps({
            "id": 2,
            "method": "Target.attachToTarget",
            "params": {"targetId": target_id, "flatten": True}
        }))
        session_id = None
        for _ in range(10):
            msg = json.loads(await ws.recv())
            if msg.get("method") == "Target.attachedToTarget":
                session_id = msg.get("params", {}).get("sessionId")
                break
            if msg.get("id") == 2 and "result" in msg:
                session_id = msg.get("result", {}).get("sessionId")
                break
        if not session_id:
            print("FAILED: could not attach to target", file=sys.stderr)
            sys.exit(1)

        # Inject secret via Runtime.evaluate (secret stays in Python memory, not tool params)
        safe_secret = json.dumps(secret)
        expr = (
            f"(function() {{"
            f"  var el = document.querySelector({json.dumps(SELECTOR)});"
            f"  if (!el) {{ return 'SELECTOR_NOT_FOUND'; }}"
            f"  var s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;"
            f"  s.call(el, {safe_secret});"
            f"  el.dispatchEvent(new Event('input', {{bubbles:true}}));"
            f"  el.dispatchEvent(new Event('change', {{bubbles:true}}));"
            f"  return 'OK';"
            f"}})()"
        )

        await ws.send(json.dumps({
            "id": 3,
            "method": "Runtime.evaluate",
            "params": {"expression": expr, "returnByValue": True},
            "sessionId": session_id
        }))
        resp = json.loads(await ws.recv())
        result = resp.get("result", {}).get("result", {}).get("value", "UNKNOWN")
        print(f"Result: {result}")

asyncio.run(main())
