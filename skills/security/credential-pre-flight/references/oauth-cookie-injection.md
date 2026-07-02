# OAuth Cookie Injection — Browser Login Without Passwords

For Google services (Gemini, Gmail web, Google Cloud Console, etc.), the preferred login method
is **OAuth cookie injection** — not password typing. This avoids stale passwords, 2FA prompts,
and "wrong password" errors entirely.

## Architecture

```
pass <user>/google/token  ──►  refresh_token
                                     │
                          fetch_google_client_details()
                                     │
                          creds.refresh(Request())  ──►  access_token (1hr)
                                                              │
                                                   POST https://www.googleapis.com/...
                                                   (not directly useful for web UI)
                                                              │
                                                   Browser CDP: Network.setCookie
                                                   (inject auth cookies from OAuth session)
```

## The Pattern

Google's OAuth tokens don't directly translate to browser cookies — but the refresh token
can be used to create a **logged-in browser session** via one of two approaches:

### Approach A: OAuth to Cookie Bridge (preferred for services with API parity)

For services that have both a web UI and an API (Gmail, Drive, Calendar):
1. Use OAuth refresh token to get an access token
2. Use the Google API (not the web UI) for the actual task
3. Skip the browser entirely — use the existing `google-workspace` skill

### Approach B: Cookie Injection via Service Account / Token Exchange (advanced)

For services that are web-UI-only (Gemini, Google AI Studio):
1. Exchange the OAuth refresh token for Google session cookies
2. Inject those cookies into the browser via CDP `Network.setCookie` or `Network.setCookies`
3. Navigate to the service — browser sees a logged-in session

The exact cookie format and names (`__Secure-3PSID`, `__Secure-3PAPISID`, etc.) are
Google-internal and can change. When this approach is needed, the most reliable path is:
- Open an incognito window
- Let the user click "Sign in" and approve the Google prompt on their phone
- Save the resulting cookies via CDP `Network.getAllCookies` → `Network.setCookies` later

### Approach C: User-Approved Prompt (simplest, most reliable)

For one-off sessions:
1. Navigate to the service's sign-in page
2. Enter email (via CDP injection or browser_click sequence)
3. Enter password (via `cdp-pass-inject.py` in this skill — zero exposure)
4. Google sends a prompt to the user's phone — user taps "Yes"
5. Session is established — no TOTP, no cookie magic
6. Save cookies to `~/.cache/<service>/cookies.json` for reuse

## When to Use Each

| Scenario | Approach | Why |
|----------|----------|-----|
| Gmail/Drive/Calendar | A (API) | Already have the pipeline, no browser needed |
| Gemini web, AI Studio | C (user prompt) | Simplest, no cookie format dependency |
| Long-running automation | B (cookie injection) | Pre-cache cookies, refresh before expiry |
| Password is known + no 2FA | CDP injection (`cdp-pass-inject.py`) | Full automation, no user interaction needed |

## Key Insight (from 26 May 2026 session)

When asked to log into Gemini web, the agent reflexively refused ("I can't log into any
website using your credentials") — but the user corrected: **the credentials are in pass**.
The question is not "can I log in" but "which secure method should I use."

Always check pass before refusing a credential request. The options above provide a
spectrum from "full automation" to "user-assisted" — pick the right one for the context.
