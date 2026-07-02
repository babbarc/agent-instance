---
name: credential-pre-flight
description: Mandatory pre-flight protocol for ANY work involving passwords, credentials, secrets, tokens, API keys, or the password store. One-load drop-in — has everything you need.
annotation: "Passwords/secrets/tokens: pass-to, CDP inject, never show"
version: 1.0.0
---
# ⚠️ Password Security Protocol — Mandatory Pre-Flight

## 🔴 Trigger (INITIATE IMMEDIATELY — DO NOT SKIP)

**A single match from this list in the user's message OR your own planned action is sufficient:**

- `password` / `pass` / `password store` / `.password-store`
- `credential` / `secret` / `token` / `API key` / `api-key`
- `login` / `auth` / `authenticate` / `OTP` / `TOTP` / `2FA`
- `GPG` / `gpg` / `encrypt` / `decrypt`
- `key` (when referring to SSH/GPG/API keys)
- Any domain + `.gpg` reference

**THE PROTOCOL ACTIVATES BEFORE YOUR FIRST TOOL CALL.** Not after. Not in parallel. First: protocol. Then: work.

---

## 🛑 Pre-Reflex Credential Check — DO BEFORE REFUSING

**If the user asks you to log into a service or use credentials for anything, do NOT reflexively refuse.** This was the source of a user correction: the agent said "I can't log into any website using your credentials" when asked about a web service — without checking pass first. The user had to remind the agent "you have all the skills."

**Step 0 — Check pass before saying no:**
```text
[ ] Does `pass` have an entry for this service? Run `pass ls` or `pass find <service>`.
[ ] Do we have existing login infrastructure (CDP autofill script, OAuth pipeline, password entry)?
[ ] If credentials exist in pass → proceed with Phase 1 below. The tools exist.
[ ] If credentials DON'T exist → explain factually: "I don't have credentials stored for that service."
```

**Rationale:** The password store and CDP autofill infrastructure (`cdp-pass-inject.py`) exist specifically for secure login automation. Saying "I can't log into websites" is incorrect when credentials are in pass — what you can't do is expose them in tool parameters. The pass-to-piped CDP injection pattern is the approved path. **Always check pass before refusing a credential request.**

---

## 📋 Phase 1 — Load Safety Context (MANDATORY)

```text
[ ] 1. STOP. No tool calls yet.
[ ] 2. Load this skill — you are here ✓
[ ] 3. Run `which pass-to && which pass-inspect` — both must succeed.
[ ] 4. CONFIRM → proceed to Phase 2
```

**FAILURE MODE CHECK:** If you ever run a tool call without these 4 steps completed, abort. Go back to step 1.

---

## 📋 Phase 2 — Safe Operations

### ✅ Approved for terminal()

| Action | Command | Why safe |
|--------|---------|----------|
| List entries | `pass` or `pass ls` | No decryption, directory listing only |
| Search by name | `pass find <term>` | Name search only |
| Search inside entries | `pass grep <pattern>` | Pipe to `grep -v '^[A-Za-z0-9+/=]\\{20,\\}$'` to filter secrets |
| Check entry structure | `pass-to <path> -- pass-inspect` | Skips first line (the secret). If pass-inspect unavailable, use inline Python fallback below. |
| Copy to clipboard | `pass -c <path>` | Only reaches clipboard, not context |
| Generate TOTP | `pass otp <path>` | GPG→pipe→oathtool, only 6-digit code output |
| Pipe to script | `pass-to <path> -- <cmd>` | Secret flows GPG→pipe→stdin, never in context |
| Edit entry | `pass edit <path>` | Opens $EDITOR, no secrets to stdout |
| Create new | `pass insert <path>` | Type/paste directly, no context exposure |
| Generate password | `pass generate <path> [len]` | Generates internally, stores directly |
| Move/rename | `pass mv <old> <new>` | Re-encrypts, no decrypted output |
| Copy entry | `pass cp <old> <new>` | Re-encrypts, no decrypted output |
| Delete | `pass rm <path>` | Removes encrypted blob |
| Git | `pass git <cmd>` | Standard git operations |

### 🚫 NEVER in terminal()

| Action | Why forbidden |
|--------|--------------|
| `pass show <path>` | Dumps full secret to stdout → LLM context |
| `pass <path>` (without flag) | Identical to `pass show` |
| Any command with a secret as CLI arg | Visible in process table + shell history + LLM context |

**Exception — `pass show` in a config file (safe):** When a config file like `~/.config/himalaya/config.toml` contains `backend.auth.cmd = "pass show <path>"`, this is safe. The **config file** references the command, but the **binary** (himalaya) executes it in its own subprocess — the secret flows GPG → pipe → himalaya stdin, never through the LLM tool output. I never run `pass show` myself; himalaya does. This is the approved pattern for referencing secrets in config files.
| Any command with a secret as CLI arg | Visible in process table + shell history + LLM context |

### 🚫 NEVER in browser tools (`browser_type`, browser_console injection, browser_cdp)

| Action | Why forbidden |
|--------|--------------|
| `browser_type(ref, "actual-password-string")` | The password is visible in **tool call params forever** — stored in conversation history, outputs, and any monitoring infra. See `references/leak-postmortem-2026-06-06.md` for a real incident. |
| Injecting a secret via `browser_console("...")` expression | Same issue — the string literal is captured in the tool call record. |
| `browser_cdp(method='Input.insertText', params={"text":"actual-password"})` | **Same leak class as browser_type.** `Input.insertText` is the CDP-level equivalent of keyboard typing, but the secret travels through the `browser_cdp` params text field — visible in the permanent tool call record. The pass-to-piped script pattern is the only zero-exposure approach. See `references/leak-postmortem-2026-06-06.md` for a real incident. |

**Use instead:**
- **`cdp-pass-inject.py`** (in this skill) — reads credentials from `pass-to` internally (never exposes to tool params), auto-discovers CDP WebSocket URL, properly attaches to target via `Target.attachToTarget`. One command: `pass-to <service>/<path> -- python3 cdp-pass-inject.py` for password fields, or pass a custom CSS selector as second arg.
- **OAuth cookie injection** (see `references/oauth-cookie-injection.md`) — for Google services, skip password entry entirely by injecting session cookies derived from the OAuth refresh token. Especially useful when the password is stale or 2FA is enabled.
- **`pass -c <path>`** then ask the user to paste (only when the user is present)
- **User-approved Google prompt** — navigate to sign-in, enter email + password via CDP injection, then let Google send a phone prompt for the user to approve. Avoids TOTP entirely. Documented in `references/oauth-cookie-injection.md`.

> **Google Workspace note:** This instance uses pass-based OAuth for Gmail/Calendar/Drive — credentials fetched via `hermes_creds.py` at runtime, not from JSON files. The base google-workspace skill describes the generic setup. For this instance's actual credential flow, load `references/google-workspace-credential-setup.md` before using google-workspace.

**Telltale you're about to leak:** If you find yourself writing something like `browser_type(ref, "hunter2")` or `browser_type(ref, pass show output)`, STOP. You're about to put a secret in the permanent tool-call record. Close the browser session and use `cdp-pass-inject.py` from this skill instead — it reads from pass internally with zero exposure.

### 🚫 NEVER in your response / send_message

Never include a credential value (password, token, API key, TOTP code, seed phrase, private key) in any message sent to the user or any file written to disk. MEDIA delivery of `.gpg` files is acceptable (they're encrypted).

### 🚫 SPA Login Fallback Trap — CRITICAL

SPA login forms (React, Angular, Vue) often ignore CDP `Runtime.evaluate` value injection because the framework's internal state manager (React state, Angular FormControl, Vue reactivity) doesn't detect the DOM value change. This means:

- CDP injection sets the DOM value ✅
- CDP injection dispatches `input`/`change` events ✅
- The form framework never sees the value ❌
- The submit fires but sends an empty/old value ❌

**When CDP injection fails to login:**
1. Do NOT fall back to `browser_type(ref, password)` — this leaks the credential into tool call params
2. Do NOT fall back to inline passwords in terminal commands (heredocs, echo, etc.)
3. Instead: **stop the automated login attempt.** Use one of:
   a. Password reset flow (click FORGOTTEN PASSWORD, submit email, user checks their inbox)
   b. Ask the user to log in from their own browser
   c. If the user gives explicit permission to use browser_type, do it once (and only once)

**⚠️ Even when Input.insertText WORKS, it leaks.** The secret travels through the `browser_cdp` params text field — same leak class as `browser_type`. The only zero-exposure login path is a pass-to-piped CDP injection script (see "Use instead" above) that reads the credential internally and never passes it through any Hermes tool parameter.

**⏱️ Timebox rule — don't waste 15 minutes on alternative CDP approaches:** If Runtime.evaluate injection + Input.insertText (both documented approaches) fail to produce a working login after 3 attempts, stop immediately — the SPA framework is not going to respond to a 4th or 5th variant of DOM manipulation. Fall through to option (c) immediately: ask the user for permission to use browser_type once. See `references/leak-postmortem-2026-06-06.md` for why fallback paths matter.

### ⚠️ `credential-ops` — Pruned Import

The earlier `credential-ops` skill scripts (`pass-autofill.mjs`, `pass-cdp-login.cjs`, `totp-gen.py`) were lost when that workspace was pruned. The `pass-inspect` script was restored from curator backup.

**Current working equivalents:**

| Need | Working tool/path |
|------|------------------|
| CDP browser autofill | `cdp-pass-inject.py` (in this skill) |
| pass inspection | `pass-inspect` (restored from curator backup) or inline Python workaround below |
| pass CLI ops | Use `pass` commands directly from Phase 2 table above |
| Git sync | Post-commit hook at `references/git-auto-sync-hook.sh` (in this skill) |
| GPG key management | Not yet tooled — manage manually or ask user |

**If you load this protocol and see a stale reference to `credential-ops`, treat it as a deleted skill. Use the inline content in this skill instead.**

## 💡 Related Scripts & References

| File | Purpose |
|------|---------|
| `cdp-pass-inject.py` | Generic CDP credential injector — any site, any selector |
| `pass-inspect` | Inspect pass entry metadata without exposing the secret |
| `pass-env` | Set env var from pass secret, run a command — for scripts that require env vars. Prefer `pass-to` (stdin pipe) when possible. |
| `references/git-auto-sync-hook.sh` | Post-commit hook for pass git auto-sync |
| `references/oauth-cookie-injection.md` | OAuth token → browser cookie injection (passwordless login) |
| `references/service-portal.md` | Service portal login specifics |
| `references/leak-postmortem-2026-06-06.md` | **Read this.** Real leak that happened when the trigger was ignored: Google password + TOTP secret dumped to LLM context via `pass show`. Concrete grounding for why Phase 1 is mandatory. |
| `references/pass-to-path-splitting-pitfall.md` | **Bug found in cdp-pass-inject.py and gemini-google-login.py (Jun 2026).** `PASS_PATH.split('/')` breaks `pass-to` — use the unsplit path as a single argument. Read before writing any script that calls `pass-to`. |
| `references/google-phone-prompt-login.md` | **Google 2FA phone-prompt login flow (Jun 2026).** Step-by-step CDP pattern for Google services that trigger phone notification: email via Runtime.evaluate → password via pass-to pipe → user approves on phone → navigate to target. Includes pitfalls (stale pass passwords, SPA click resistance, target ID expiry). |
| `references/headless-gpg-cache.md` | **Headless cron GPG cache diagnosis (Jun 2026).** `pass` commands fail silently in cron/background because GPG agent cache expired — no tty to prompt for passphrase. Diagnostic steps, permanent fix (gpg-agent.conf), short-term warm-up, and edge cases. |
| `references/cdp-image-download.md` | **Download images from SPA web apps via CDP (Jun 2026).** Blob URLs can't be fetched externally. Technique: canvas.toDataURL('image/jpeg') → chunked retrieval via CDP Runtime.evaluate → base64 decode on disk. Covers Page.captureScreenshot clip approach as fallback. |

---

## 📋 Phase 3 — Verify Before Mutation or Push

Before `pass insert` / `edit` / `mv` / `rm` / `cp` / `generate`:

```text
[ ] Path clearly indicates user + service? (user/service/account)
[ ] Standard schema? (line1=password, login:, url:, otpauth:)
[ ] Will `pass git push` propagate this change?
[ ] TOTP secrets as full `otpauth://totp/...` URIs, not bare base32?
```

Before `pass git push`:

```text
[ ] Announced the change to the user first?
[ ] Commit message descriptive? (e.g. "Move service/account to service/accounts/account")
```

---

## 📁 Credential Storage Policy — Mandatory

**Every static secret that grants access to a service goes in `pass` under a user or service directory.**

### Three-Tier Storage

| Tier | Location | Contents | Lifetime | Encrypted | Git bloat risk |
|------|----------|----------|----------|-----------|---------------|
| **Durable** | `pass <service>/` | Passwords, client secrets, refresh tokens | Months/years | ✅ GPG | Low (rare writes) |
| **Long-lived token** | `pass <service>/tokens` | OAuth token files (e.g. Garmin, APIs w/ no refresh/access split) | Annual re-auth | ✅ GPG | Low — only write back when content **actually changed**, not every invocation |
| **Ephemeral** | `~/.cache/<service>/` | Access tokens, session cookies, frequently-refreshed artifacts | Minutes–hours | ❌ Plain (expiry is the protection) | None (not in pass) |

### Examples

| What | Where | Examples |
|------|-------|---------|
| Passwords | `pass <service>/password` | Service accounts, banking |
| Refresh tokens (long-lived) | `pass <service>/token` | Google OAuth refresh token (months/years) |
| Token files (annual re-auth) | `pass <service>/tokens` | Garmin Connect `garmin_tokens.json` |
| Ephemeral access tokens | `~/.cache/<service>/` | Google access tokens (1hr expiry) |
| API keys / secrets | `pass <service>/<key-name>` | Kraken API key, OpenAI key |
| Client IDs / app secrets | `pass <service>/config` | OAuth client secrets |

### Key Rules by Tier

1. **Durable secrets** (passwords, client secrets, refresh tokens) → `pass` only, read on every invocation.
2. **Ephemeral tokens** (access tokens, session cookies, anything that refreshes on every use) → `~/.cache/<service>/`. **Never in pass.** Unconditional writeback to pass every invocation bloats the password store git history. GPG re-encrypts the same plaintext to a different ciphertext every time, so every write = a git commit even when nothing changed.
3. **Long-lived token files** (single-file OAuth tokens with annual lifespan) → Seed to `pass` on initial auth; cache at `~/.cache/<service>/` for daily use. **NEVER write back to `pass`.** Many providers (Garmin, etc.) rotate tokens on every login, making any diff/hash check fire every time — daily pass git bloat. Cache on disk persists between runs. Cache loss → graceful auth failure, user re-runs `login` once.
4. **Runtime token directory** should be configurable (env var, CLI arg) so scripts control it, not the library's default path which may be unencrypted.

### Google Auth Precedent

Established — the canonical architecture:
- `pass <service>/google/token` → refresh token only (long-lived, months/years)
- `~/.cache/google-tokens/<user>/access.json` → access token + expiry (~1 hour, never in pass)
- Same principle applies to any OAuth flow: split the long-lived from the ephemeral.

### 🚫 NEVER:
- Save tokens to default library paths without vetting (`~/.garminconnect/`, `~/.config/`, etc.) — these are unencrypted
- Store plain env vars or .env files
- Write to any file outside `pass` for durable secrets
- Unconditional writeback to pass on every invocation for refreshable tokens
- Use `pass show` / `pass <path>` (leaks into LLM context — use `pass-to` instead)

**Wrapper pattern for libraries that auto-save tokens (CORRECT):**
1. Use `~/.cache/<service>/` as the runtime token directory (persistent on disk between invocations)
2. Seed it from `pass <service>/tokens` if cache is empty (first run or cold start)
3. Library writes refreshed tokens to cache on every login
4. **NEVER write back to pass.** Many providers rotate tokens on every login — any diff/hash check fires every time. Cache is persistent on disk. Cache loss → graceful auth failure; user re-runs `login` once.
5. Clean up old decrypted temp files — never leave plaintext token files on disk

**🚫 WRONG (what was done for Garmin — took TWO attempts to fix):**
> **First — still wrong:** Added cache + diff/hash check before write. Failed because Garmin rotates tokens on every login, making any diff fire every time. Still daily pass commits.
>
> **Real fix:** NEVER write tokens back to pass. Cache at `~/.cache/garmin-tokens/` persists on disk. Pass is cold-start seed only. Cache loss → graceful auth failure; user re-runs `login` once.

### TOTP Commands

```bash
pass otp <service>/<path>               # Generate TOTP — secret never reaches context
pass otp -c <service>/<path>            # Copy to clipboard
pass otp -q <service>/<path>            # Quiet mode (just the code, no newline)
```

- Extension at `~/.password-store/.extensions/otp.bash`
- `oathtool` at `~/.local/bin/oathtool`
- `PASSWORD_STORE_ENABLE_EXTENSIONS=true` in `~/.bashrc`

### Safe Inspection Scripts

```bash
# Check entry structure (skips first line = secret)
pass-to <path> -- pass-inspect

# If pass-inspect unavailable, inline Python:
pass-to <service>/<path> -- python3 -c "
import sys, re
lines = sys.stdin.read().split('\\n')
for l in lines[1:]:
    if 'secret=' in l: l = re.sub(r'secret=[A-Z2-7=]+', 'secret=HIDDEN', l)
    print(l)
"

# Inline check: count lines, peek at field names
pass-to <service>/<path> -- python3 -c "import sys; lines=sys.stdin.read().strip().split('\\n'); print(f'{len(lines)} lines'); [print(l.split(':')[0]) for l in lines[1:] if ':' in l]"
```

### 📡 Git Sync & Auto-Push Setup

**Default: no auto-sync.** pass commits locally via `pass git commit` but never pushes. Check current state:

```bash
cd ~/.password-store
git log --oneline origin/master..master   # commits ahead of remote
pass git config --list | grep -i push      # any auto-push config
ls .git/hooks/post-commit 2>/dev/null      # auto-sync hook installed?
```

**`pass.git.pullAndPush` is a trap.** pass v1.7.4 accepts the config option (`pass git config pass.git.pullAndPush true`) but the `git_commit()` function in the script never reads it. The option is parsed by newer versions only. Setting it does nothing on v1.7.4.

**The correct approach: a git post-commit hook** that pulls before and pushes after every commit.

| Step | Command |
|------|---------|
| Install | Copy the hook from `references/git-auto-sync-hook.sh` to `~/.password-store/.git/hooks/post-commit` |
| Make executable | `chmod +x ~/.password-store/.git/hooks/post-commit` |
| Verify | Run `pass insert <service>/test-sync <anything>` — check it auto-pushes to `origin/master` |
| Clean up | `pass rm -f <service>/test-sync` (will also auto-push) |

**Pitfalls:**
- The hook skips itself during rebase/merge/cherry-pick (detects via `rebase-merge`, `MERGE_HEAD`, etc.)
- First install may fail if local is behind remote — run `pass git pull --rebase origin master` manually first
- The hook uses `git pull --rebase origin master` then `git push` — handles divergence gracefully

**Verification:**
```bash
cd ~/.password-store
git log --oneline origin/master..master   # should be empty (fully synced)
```

To disable: `rm ~/.password-store/.git/hooks/post-commit`

---

### GPG Cache — Headless Cron / Background Diagnosis

1. **Diagnose:** `pass-to`/`pass` works interactively but fails silently in cron/background? Check `cat ~/.gnupg/gpg-agent.conf`. No config = defaults expire cache in 2h (`max-cache-ttl 7200`).
2. **Fix permanently:** Create `~/.gnupg/gpg-agent.conf` with `default-cache-ttl 86400` and `max-cache-ttl 86400`, then `gpg-connect-agent reloadagent /bye`. Keeps passphrase cached 24h — covers any daily cron window.
3. **Warm up immediately:** `PASSWORD_STORE_GPG_OPTS="--no-tty --batch --quiet" pass show <service>/<path> 2>&1 | head -1 | wc -c` then retry `pass-to`.
4. **Full recipe + edge cases:** `references/headless-gpg-cache.md`.

---

## 🛑 Escalation

If you're tempted to skip any step because "it's just one quick look" or "I already know what's in that file" — **stop**. See `references/leak-postmortem-2026-06-06.md` for why structural enforcement matters.

When in doubt: **do not run the command. Ask the user.**

---

## 🧠 Why This Exists

The password store contains decrypted secrets. The LLM context is a leak surface — any secret that enters it is visible in conversation history, tool outputs, and could theoretically be extracted. The guardrail exists because past breaches proved the "I'll be careful" approach doesn't work. Structural enforcement does.
