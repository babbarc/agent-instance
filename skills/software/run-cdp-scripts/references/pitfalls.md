# Pitfalls — CDP Browser Automation

## Async returns `{}` or `None`

**Cause:** You fired an async function via `Runtime.evaluate` but didn't drain the initial CDP response before polling for the window variable. The async Promise resolves asynchronously, and the subsequent `evaluate()` calls consume the wrong response from the WebSocket buffer.

**Fix:** Always drain the response for the message id before sending new messages. Use `cdp-eval.py --async` or the fire → drain → poll → read pattern.

## `"Failed to fetch"` on blob URLs

**Cause:** You used `fetch(blobUrl)` to download a blob URL. Blob URLs are subject to opaque-origin restrictions — `fetch()` from the same page context can't access them.

**Fix:** Use `new Image()` → canvas. The browser's image rendering pipeline has internal access to blob storage that `fetch()` doesn't.

## Images not loading (naturalWidth stays 0)

**Cause:** You scrolled `document.body` or `document.documentElement` but the content is inside a custom scrollable container (like an `<INFINITE-SCROLLER>` component). The images never enter the viewport of the correct container so lazy-loading never triggers.

**Fix:** Use `findPrimaryScrollable()` to discover the correct scrollable element, then scroll that container.

## Stale window variables from previous run

**Cause:** A previous CDP script set `window._my_var` and didn't clean up at the end. The next run reads the old value before the new async function has set it.

**Fix:** Always initialize variables to `false`/`null` at the top of the async function. Always delete them in a cleanup step.

## DOM not ready after navigation

**Cause:** You ran selectors or probes immediately after navigation or a click, but the SPA hadn't finished rendering the target elements. All strategies return empty results because the DOM is still empty.

**Fix:** Wait 3-5s after navigation before probing. For SPA sidebar clicks, wait 3s. For full page navigations, wait 5s+.

## Chrome 148+ refuses remote debugging on default profile

**Cause:** Chrome >=148 silently refuses to start the DevTools server when `--user-data-dir` resolves to the default path (`~/.config/google-chrome`). The browser runs normally but port 3333 shows no LISTEN and CDP returns empty replies.

**Fix:** Use a non-default path for `--user-data-dir` (e.g. `/home/chrome/devtools-profile`).

## CDP scripts return STATUS:NO_PAGE but browser tools work

**Cause:** After a browser restart or fresh container start, only the default new-tab page exists. CDP scripts (`cdp-find-page.py`, `cdp-navigate.py`) scan `Target.getTargets` for pages matching a URL/title pattern and find nothing. Meanwhile `browser_navigate` works because the browser tools establish a fresh connection.

**Fix — two approaches:**

1. **Establish the page first with browser_navigate:** Call `browser_navigate("https://target.url")` to open the page through browser tools. After 3-5s, CDP scripts discover the target normally.

2. **Use Target.getTargets directly:** Call `browser_cdp(method='Target.getTargets')` to list all open pages. Find the `targetId` of the page you want, then use `browser_cdp` with `target_id` set to that ID for subsequent calls.

**Root cause:** Browser tools and CDP scripts share the same Chrome instance but use different discovery paths. browser_navigate creates a page tracked internally by the tools, but CDP scripts that re-scan `Target.getTargets` may run before the page fully initializes.

## Multiple page targets = wrong connected page

**Cause:** When multiple browser tabs are open on the same domain (gemini.google.com, etc.), `get_gemini_ws()` or `cdp-find-page.py --url "gemini"` returns the first matching target — which may not be the one you want.

**Fix:** Use `cdp-list-tabs.py --verbose` first to see all open tabs, then use a more specific match. Or use `cdp-find-page.py --title` instead of `--url` for more precise targeting.
