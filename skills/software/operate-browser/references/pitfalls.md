# Operate Browser — Pitfalls (one-liners)

- **SSR hydration delay** — snapshot shows elements that don't exist yet. Wait 2-3s, verify with `browser_console('inputs.length')`.
- **browser_navigate resets context** — each call loses cookies/session. Use CDP `Page.navigate` (see `use-cdp-protocol`).
- **Stale refs** — DOM changes invalidate snapshot refs. Snapshot fresh before each click.
- **browser_vision fails on text-only models** — screenshot is still captured anyway. Use `browser_snapshot()` for text.
- **Browser-proxy architecture** — CDP is NOT direct to Chrome. `browser-proxy` runs `browser-proxy.py` listening on port 3333, forwarding to Chrome on 3334. The proxy manages Chrome lifecycle: starts on demand, stops after 1h idle. NEVER kill the proxy — only kill `hermes-browser`. If the proxy dies, all browser tools fail with "CDP endpoint not reachable".
- **Fresh Chrome restart (idle timeout)** — After 1h idle, proxy stops Chrome. Restart creates blank `about:blank` page. `find_or_create_gemini_page` returns None because no URL starts with 'http'. Fix: fall back to any `type: 'page'` target and navigate — the navigation function handles the rest.
- **gemini_web returning STATUS:NO_PAGE** — Does NOT mean browser is down. Chrome may be idle-stopped. Call `browser_navigate("https://gemini.google.com/app")` first to wake the proxy and create a page target, then retry.
- **pass-autofill.mjs** creates isolated tab — cookies don't carry to Hermes tools.
- **TOTP window** — generate right before typing, re-generate if >1 snapshot cycle passes.
- **PrimeFaces downloads** — click button, file lands in container. Do NOT try XHR interception.
- **PDF viewer download button** (Chrome built-in) — navigates to `chrome://newtab/` in headless. Use `browser_cdp(method='Page.printToPDF')` instead.
- **Passkey-first login** — snapshot shows "Use passkey"/"Authenticator app" with 0 inputs. Click "Authenticator app" → goes straight to TOTP.
- **Assumption rampage** — See `references/assumption-rampage.md` for the classic cycle: assume → execute → discover gap → blame → invent workaround. Prevention: open dialog → read ALL options → present → ask → act.
- **`<input type='submit'>` invisible to browser_click** — Many UK Government/CH forms use `<input type='submit' value='Save and continue'>` not `<button>`. The accessibility tree snapshots its ref, but `browser_click` on the ref does NOT dispatch the form. Fix: use CDP `document.querySelector('form').requestSubmit()`.
- **form.requestSubmit() fails if frame_id missing** — `document.querySelector('form')` returns null when CDP `Runtime.evaluate` is called before the page finishes hydration. Wait 2-3s after navigation or verify `document.forms.length > 0` before calling `requestSubmit`.
