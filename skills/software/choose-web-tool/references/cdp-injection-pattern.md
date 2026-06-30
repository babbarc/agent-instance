# CDP Password Injection

CDP-based password injection for login forms is documented in the `credential-pre-flight` skill:

- **Script:** `scripts/cdp-pass-inject.py` — reads credentials from `pass-to` internally (never exposes to tool params), auto-discovers CDP WebSocket URL, attaches to target via `Target.attachToTarget`. Usage: `pass-to <service>/<path> -- python3 cdp-pass-inject.py`
- **Alternatives:** OAuth cookie injection (`references/oauth-cookie-injection.md`) for passwordless login; Google phone-prompt login (`references/google-phone-prompt-login.md`)

Load `skill_view('credential-pre-flight')` before any CDP credential injection.
