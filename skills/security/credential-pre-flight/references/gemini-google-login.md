# Gemini Google Login Script

**Location:** `/opt/data/scripts/gemini-google-login.py`

A CDP-based script for automated Google login into Gemini. Handles the multi-step flow:
email → password → TOTP (if prompted) → navigate to Gemini.

## Usage

```bash
python3 /opt/data/scripts/gemini-google-login.py --port 3333 --pass-path pallav/accounts.google.com
```

## Known Issues & Recent Fixes (Jun 2026)

### 🔧 `pass-to` Path Splitting Bug
The script originally used `PASS_PATH.split('/')` when calling `pass-to`, which broke the command into separate arguments (`pass-to pallav accounts.google.com -- ...` instead of `pass-to pallav/accounts.google.com -- ...`). **Both `read_pass_field()` and `read_pass_password()` had this bug.** Fixed by using `PASS_PATH` as a single unsplit argument.

### 🔧 False `ALREADY_LOGGED_IN` Detection
Gemini shows a prompt input even on the logged-out landing page. The original check (`hasPrompt=true && isSignIn=false`) triggered `ALREADY_LOGGED_IN` even when not logged in. **Fix:** Added `hasSignInBtn` check — if a "Sign in" button exists, we're clearly not logged in.

### ⚠️ For Google 2FA (Phone Prompt)
If Google sends a phone notification instead of TOTP, the script waits 30s for the user to approve — but this is unreliable. Prefer the manual CDP flow documented in `references/google-phone-prompt-login.md` within this skill, which gives the user a clear prompt and waits indefinitely.

## Status Outputs

| Code | Meaning |
|------|---------|
| `STATUS:OK` | Logged in, on Gemini page with prompt input |
| `STATUS:ALREADY_LOGGED_IN` | Already logged into Gemini |
| `STATUS:NO_WS` | Couldn't connect to CDP |
| `STATUS:LOGIN_FAILED` | Login didn't complete |
| `STATUS:TOTP_FAILED` | TOTP entry failed |
| `STATUS:NO_GOOGLE_PAGE` | No accounts.google.com tab found |

## How It Works

1. Connects to the existing Hermes browser via CDP WebSocket (auto-discovery)
2. Attaches to the Google sign-in page target (`Target.attachToTarget`)
3. Reads email/password from pass via `pass-to` (no tool-param exposure)
4. Sets values using native value setter + event dispatch (SPA-safe)
5. Generates TOTP via `pass otp` if prompted
6. Navigates to gemini.google.com after login
7. Saves session cookies to `~/.cache/gemini-session/cookies.json`

## Caveat — Google Prompt

If Google sends a phone prompt instead of a TOTP challenge, the script waits up to
30 seconds for the user to approve it. This is the preferred path (no TOTP needed).
