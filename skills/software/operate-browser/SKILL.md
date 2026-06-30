---
name: operate-browser
description: "Load BEFORE touching the browser. Covers browser_navigate/click/type/scroll, file downloads from container, screenshot delivery, TOTP login, bot detection, and all browser tool pitfalls. Prevents the '20-turn download fight' anti-pattern."
annotation: "Load before browser: navigation, forms, snapshots, scroll"
version: 1.4.0
metadata:
  hermes:
    tags: [browser, web, scraping, automation, screenshots]
    related_skills: [choose-web-tool, scrapling, run-cdp-scripts, credential-pre-flight]
---

# Operate Browser — Hermes Browser Tools

Pitfalls in `references/pitfalls.md`.

## 1. Load companion skills before any browser call

1. Load `choose-web-tool` first — it decides whether you even need the browser vs curl/scrapling.
2. If the task involves a login, credentials, or password entry, load `credential-pre-flight` next.
3. Only then call a browser tool. The user will catch you if you skip this.

## 2. Bootstrap the browser/CDP connection

If browser tools return "CDP endpoint not reachable" or `STATUS:NO_PAGE`:

1. The browser-proxy container manages Chrome lifecycle. It should always be running on port 3333.
2. Chrome may have been idle-stopped (1h timeout). Call `browser_navigate(url)` — this triggers the proxy to start Chrome.
3. If Chrome restarted fresh (blank page), tools may find no HTTP page target. Fall back to any available page target (`type: 'page'`) and navigate to the target URL.
4. If the proxy itself is down, it needs to be recreated from the Quadlet definition. This is rare — proxy is long-lived.

## 3. Decide: is browser the right tool?

1. Try curl/web_extract for static HTML or API endpoints — faster, no bot detection.
2. Try scrapling for Cloudflare-protected or JS-rendered pages — may bypass where headless fails.
3. **Browser last** — only for login flows, SPAs that need JS, or sites that block scrapling.

## 4. Navigate and interact

- `browser_navigate(url)` — Go to a URL. **Resets cookies/session** — for in-session navigation, use CDP `Page.navigate` (see `use-cdp-protocol`).
- `browser_click(ref)` — Click element by snapshot ref. **Stale refs** — DOM changes invalidate refs; snapshot fresh before each click.
- **`<input type="submit">` workaround** — When clicking a submit button via `browser_click` does NOT advance the page (page reloads, same form shown), the button is likely an `<input type="submit">` element (not a `<button>`), which the accessibility tree snapshots but cannot dispatch reliably. Fix: use CDP `document.querySelector('form').requestSubmit()`. This works regardless of whether the submit button is an `<input>` or `<button>`.
- `browser_type(ref, text)` — Type into input. **Never pass passwords here** — see credential-pre-flight for zero-exposure injection.
- `browser_scroll(direction)` — Scroll up/down.
- `browser_snapshot()` — Full textual DOM snapshot. **SSR hydration delay** — wait 2-3s, verify with `browser_console('inputs.length')` before interacting.
- `browser_vision(question)` — Screenshot + vision. Use when text snapshot is too truncated. Captures screenshot even when analysis fails.
- `browser_console(expression)` — Run JS / get logs.

## 5. Verify UI behavior — never assume what a dialog offers

Before claiming a web UI "has X", "supports Y", or "exports Z":

1. **Navigate** to the relevant page or section.
2. **Open** the dialog/menu (Export, Settings, Filters, etc.) — click the button and read the snapshot.
3. **Read the options verbatim** from the snapshot — format names, group selectors, radio buttons, dropdown entries. Don't extrapolate from what you think they should be.
4. **Present the exact options** to the user as raw findings — not as a conclusion about what the UI "does."
5. **Stop.** Do not propose a solution, do not execute an export, do not chase a download path. Let the user decide what to do with the findings.
6. If the user then asks you to act, follow their instruction exactly — do not add your own steps or assumptions.

**Violation pattern documented in** `references/pitfalls.md` (section: Assumption rampage).

## 6. Login with credentials

1. Load `credential-pre-flight` first.
2. Navigate to the login page.
3. **Never pass a password string into browser_type, browser_console, or browser_cdp(Input.insertText)** — the secret is recorded in tool-call params permanently.
4. Use the `cdp-pass-inject.py` script from credential-pre-flight, or a custom CDP script that reads from `pass-to`.
5. For TOTP: generate right before you need it (30s window) via `pass otp <path>`.

## 7. Download files from the browser container

Most downloads land in the container, not on the host:
```
podman exec hermes-browser ls -la /home/chrome/Downloads/
podman cp hermes-browser:/home/chrome/Downloads/<file> /tmp/
```

Known services: France-Visas (PrimeFaces) → PDF, Kraken → ZIP containing CSV.

## 8. Handle bot detection

- **Signals:** blank page after submit, silent redirect to login, endless CAPTCHA.
- **Amazon** — Headless detected at email step. Stop after 2-3 attempts. Share login URL.
- **Google OAuth** — Always blocked. Share auth URL.
- **Turnstile** — Navigate, wait ~90s (don't interact), checkbox appears on its own.
- **Mild CAPTCHA** — Retry with different timing.
- **Blank page / 404 on known-valid URL** — Try scrapling first (not another browser cycle).

## 9. Verify browser context before delivering a screenshot (MANDATORY)

  **HARD RULE: Every screenshot you send must be from the page the user asked for. Failing this causes extreme user frustration. Follow these steps in order, every time.**

  9.1. **Check what the browser is actually displaying.** Before calling any screenshot tool, call `browser_snapshot()` and read the URL from `frame_tree.top.url` (the `url` field near the top of the snapshot). This tells you what page the browser is really on — NOT what you assume it's on.

  9.2. **Identify the root cause** if the browser is on the wrong page:
       - `gemini_web` leaves the browser on `gemini.google.com` after analysis — the most common trap.
       - `browser_navigate` to a URL changes the displayed page.
       - A prior filing, login, or search flow navigated to a sub-step.
       Calling `browser_vision()` without navigating first captures WHATEVER is currently displayed, not what the user asked for.

  9.3. **If the browser is NOT on the requested page → navigate there first.** Call `browser_navigate(url)` with the correct URL. Wait for the page to load (check snapshot URL confirms the target domain). Only then take the screenshot.

  9.4. **Take the screenshot.** Use `browser_vision(question)` — the screenshot IS captured even if vision analysis fails (quota errors, non-vision model). The file at `screenshot_path` is a real browser screenshot. Share it via `MEDIA:<path>` in your response.

  9.5. **Verification failure consequences already incurred:** In one session, this rule was violated 3 times consecutively — each time sending a screenshot of `gemini.google.com` instead of the Companies House filing page the user explicitly requested. The user's response escalated from "dude! wtf!" to "FUCK!! Again exact same mistake! third time! you piece of shit!!!" This is a hard behavioral boundary — treat it as such.
