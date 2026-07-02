# pass-to Path-Splitting Pitfall

## The Bug

**Incantation found in two login scripts (Jun 2026):**
```python
PASS_PATH = 'pallav/accounts.google.com'
result = subprocess.run(
    ['pass-to'] + PASS_PATH.split('/') + ['--', 'head', '-1'],
    ...
)
```

**What it does:** `PASS_PATH.split('/')` → `['pallav', 'accounts.google.com']` → the command becomes `pass-to pallav accounts.google.com -- head -1` → `pass-to` interprets `pallav` as the path (prints "pallav" since there's a directory named pallav) and `accounts.google.com` as command start → silently wrong, no error.

**What it should be:**
```python
['pass-to', PASS_PATH, '--', 'head', '-1']
```
Use `PASS_PATH` as a single argument — no splitting.

## Scripts Affected

| Script | Location | Fixed? |
|--------|----------|--------|
| `cdp-pass-inject.py` | This skill's `scripts/` directory | ✅ Patched |
| `gemini-google-login.py` | `/opt/data/scripts/gemini-google-login.py` | ✅ Patched |

## Related Bug: `read_pass_field()` vs `read_pass_password()`

The same path-splitting bug affected both `read_pass_field()` (reads a named field like `login:`) and `read_pass_password()` (reads line 1) in `gemini-google-login.py`. Both fixed.

## Also Fixed: False `ALREADY_LOGGED_IN` Detection

Gemini shows a prompt input (`[contenteditable]`) even on the logged-out landing page. The original `gemini-google-login.py` treat `hasPrompt=true && isSignIn=false` as proof of login — but Gemini's pre-login page satisfies both conditions (prompt visible, no email/password form).

**Fix:** Added `hasSignInBtn` check — if a "Sign in" button is found on the page, we're clearly not logged in, even if a prompt input exists.

```javascript
// Before: logged-in detection was too aggressive
if (state.get('hasPrompt') && !state.get('isSignIn')) // fires on Gemini landing page

// After: requires absence of "Sign in" button too
if (state.get('hasPrompt') && !state.get('isSignIn') && !state.get('hasSignInBtn'))
```

## How to Catch in Review

Scan for `PASS_PATH.split('/')` or `path.split('/')` in any code that pipes to `pass-to`. The path separator `/` is part of the single path argument — you must NOT split on it.

## Also Check: `cdp-pass-inject.py` Call Pattern

The `cdp-pass-inject.py` usage docs say:
```
One command: `pass-to <service>/<path> -- python3 cdp-pass-inject.py`
```

This is **correct** — `pass-to` handles the piping. The bug was only in the *script's own* internal `pass-to` call, not in the invocation pattern. The invocation pattern relays through `pass-to → stdin` safely.
