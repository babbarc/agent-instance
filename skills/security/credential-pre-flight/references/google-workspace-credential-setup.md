# Google Workspace Credential Architecture

## Overview

This Hermes instance uses a **pass-based Google OAuth credential architecture**. All credentials are fetched at runtime via `hermes_creds.py` — no credential JSON files (e.g., `google_token.json`, `google_client_secret.json`) are stored on disk or read directly.

This is the key difference from the base skill, which stores OAuth tokens and client secrets as plain JSON files under `~/.hermes/`.

## How It Works

1. **Client secrets** are retrieved from the system password store (`pass`) at runtime
2. **OAuth tokens** are managed programmatically — the setup script handles the PKCE flow
3. **No credential files** are ever written to or read from the filesystem directly
4. The underlying `google_api.py` wrapper expects credentials to be passed from `hermes_creds.py`, not loaded from JSON paths

## Multi-Account Pattern

Two Google accounts are configured on this instance:
- **Primary account** — used by default for all operations
- **Secondary account** — accessed via the `--account` flag

The `--account` flag is a **global flag** placed before the subcommand:

```bash
# Default account
$GAPI gmail search "is:unread" --max 10

# Specific account
$GAPI --account partner-account gmail search "is:unread" --max 10
```

This pattern applies consistently across all Google services (Gmail, Calendar, Drive, Contacts, Sheets, Docs).

## Re-Auth / First-Time Setup

If authentication issues arise (`NOT_AUTHENTICATED`, token expiry), refer to:
`references/first-time-setup.md`

That guide covers the OAuth setup workflow including:
- Verifying current auth status (`$GSETUP --check`)
- Generating authorization URLs
- Exchanging the OAuth code
- Revoking and re-authorizing

## Pre-Flight Check

Before every send or create/delete operation, verify the sending account:

```bash
$GAPI gmail search "from:me" --max 1          # default account
$GAPI --account partner-account gmail search "from:me" --max 1
```

Check the `from` field in the response matches the expected sender. Tokens can silently map to a different account — always verify.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `NOT_AUTHENTICATED` | Run `$GSETUP --check` → re-auth if failed |
| `HttpError 403: Insufficient Permission` | Missing scope — `--revoke` then re-auth with correct scopes |
| `HttpError 403: Access Not Configured` | Enable API in Google Cloud Console |
| `ModuleNotFoundError` | Check Hermes venv: `python3 -c "import google.auth"` |
