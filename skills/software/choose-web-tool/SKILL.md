---
name: choose-web-tool
description: "Load FIRST for any web interaction. Decides whether to use curl, browser, scrapling — prevents wasting turns on the wrong tool."
annotation: "Load first for web: decide search vs browser vs scrapling"
version: 2.1.0
metadata:
  hermes:
    tags: [web, browsing, scraping, navigation, bot-detection]
    related_skills: [operate-browser, run-cdp-scripts, credential-pre-flight, recaptcha-solver]
---

# choose-web-tool — Tool Selection

**Load this skill first for ANY web task.** Then load companion skills (operate-browser, run-cdp-scripts, credential-pre-flight) BEFORE starting browser work — not after.

## Decision Tree

| Situation | Tool | Why |
|-----------|------|-----|
| API endpoint (JSON/XML) | `curl -sL` | Fastest, no DOM |
| Static HTML | `curl` / `web_extract` | No browser overhead |
| JS-rendered page (SPA) | Browser tools | Needs JS runtime |
| Cloudflare-protected | Scrapling stealthy-fetch first | May bypass where headless fails |
- Heavy anti-bot (Amazon, banks) | Browser + browser_vision | Page renders but text snapshot truncated (1000+ lines). Use `browser_vision` to read rendered content from pixels. For login flows, fall through to CDP.
| Login flow | Browser + pass-to CDP script | See credential-pre-flight |
| Multi-page crawl | Scrapling Spider | Link-following, concurrent |
| Google OAuth | **Skip — share auth URL** | Google blocks headless at network level |

**Rule:** If curl works in 1 call, do that. Browser is 10× slower and triggers bot detection.

## Site Patterns

**Cloudflare Turnstile:** Navigate → wait ~90s (don't interact) → checkbox appears → click → waiting room auto-refreshes. Cron: budget 2-3 min for Turnstile wait.

**PrimeFaces / JSF portals:** Downloads work fine in headless — file lands in container `/home/chrome/Downloads/`. Retrieve with `podman cp`. See `operate-browser`.

**JS-rendered 404:** Some sites serve JS 404 pages to headless even on valid URLs. Browser returns 404 → try scrapling first. Don't conclude bot blocked.

**SPA clicks:** If `browser_click()` succeeds but URL doesn't change, SPA routing ignored it. Try `browser_cdp(method='Runtime.evaluate', params={'expression': 'document.querySelector("...").click()'})`.

## Bot Detection

**Escalation order:** browser → scrapling HTTP → scrapling stealthy-fetch. Never say "blocked" after layer 1.

**Signals:** blank page after submit, silent redirect to login, endless CAPTCHA, `AbortFromContinueButtonClick` in console.

**Response:**
- Mild (CAPTCHA) → retry with different timing
- Strong (blank page/404 on known URL) → **try scrapling first**
- Aggressive (Turnstile/immediate block) → scrapling stealthy-fetch (`--solve-cloudflare --block-webrtc --hide-canvas`). If that fails, abort.

Don't retry same tool >2-3 times — escalate instead.

## References

- `references/cdp-injection-pattern.md` — CDP password injection
- `references/site-patterns/` — site-specific accumulated knowledge
 
