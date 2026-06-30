# Profile Bloat — Minimisation Procedure

## When to Use

A specialist profile (`hermes profile list`) has a bloated config (300+ lines), local skill copies, or platform configs (Telegram, Discord, TTS, Bedrock, etc.) that the profile will never use because it runs as a kanban worker — not a user-facing gateway.

## The Pattern

All specialist profiles created via `hermes profile create --clone` inherit the root profile's config.yaml verbatim. This gives them features they don't need: messaging platforms, auxiliary models, TTS, dashboard, personality lists, LSP binaries, code execution sandboxes, streaming settings, etc. Every time a kanban worker starts, it reads this bloated config — wasting tokens and boot time.

## Minimisation Procedure

### 1. Audit the profile
```bash
# What's the profile called?
hermes profile list

# What's in it?
ls -la /opt/data/profiles/<name>/

# How big are the dirs?
du -sh /opt/data/profiles/<name>/*/ | sort -rh

# How big is config.yaml?
wc -l /opt/data/profiles/<name>/config.yaml
```

### 2. Identify what to keep

A kanban worker profile needs only:
- **`model.default` + `model.provider`** — the LLM that reads task bodies and calls scripts
- **`skills.external_dirs: ['/opt/data/skills']`** — shared skill pool (delete any local `skills/` directory)
- **`display.language`** — matching the user's language
- **API keys in `.env`** — only the model provider's key
- **`SOUL.md`** — domain identity (persona)
- **`memory/`** + **`memories/`** — cross-session learnings (keep existing content)
- **`sessions/`** + **`state.db`** — session history (keep for continuity)

Everything else is dead weight.

### 3. Backup then strip config.yaml

```bash
cp /opt/data/profiles/<name>/config.yaml /opt/data/profiles/<name>/config.yaml.bak
```

Write a minimal config:

```yaml
_config_version: 23
agent:
  max_turns: 30
  reasoning_effort: medium
  tool_use_enforcement: auto
approvals:
  mode: auto
display:
  language: en
  persistent_output: true
  personality: helpful
file_read_max_chars: 50000
logging:
  level: WARN
  max_size_mb: 1
memory:
  memory_char_limit: 1100
  memory_enabled: true
  user_char_limit: 700
  user_profile_enabled: true
model:
  base_url: <provider_base_url>
  default: <provider/model>
  provider: <provider>
skills:
  external_dirs: ['/opt/data/skills']
terminal:
  timeout: 180
toolsets:
- hermes-cli
```

### 4. Remove dead directories

```bash
cd /opt/data/profiles/<name>

# Local skill copies (use external_dirs instead)
rm -rf skills/

# Binary directories (not needed for kanban workers)
rm -rf bin/ lsp/

# Cache files
rm -rf audio_cache/ image_cache/
rm -f models_dev_cache.json .skills_prompt_snapshot.json .update_check

# Platform config files
rm -f auth.lock

# Empty/irrelevant dirs
rm -rf pairing/ hooks/ skins/ plans/ workspace/ scripts/ sandboxes/

# Logs (accessed on demand, not on every boot)
rm -rf logs/
```

### 5. Strip platform keys from .env

Remove any keys the profile can't use:
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS`, `TELEGRAM_HOME_CHANNEL`
- `WHATSAPP_MODE`, `WHATSAPP_ALLOWED_USERS`
- `SLACK_*`, `DISCORD_*`, `SIGNAL_*`
- `GATEWAY_ALLOW_ALL_USERS` (this profile won't run a gateway)
- `Environment=TELEGRAM_TOKEN=...` (legacy env injection)

Keep only the model provider's API key:
```
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### 6. Verify the profile boots

```bash
hermes -p <name> status
```

Check for: model configured, API key valid, no Telegram/Discord/Slack platform configs.

### 7. Verify the profile can do its job

If it's a kanban worker:
- Run a dry run of its primary tool (e.g. `python3 /opt/data/scripts/inventory.py list` for inventory-manager)
- Check that kanban tools are available (dispatcher auto-injects them)
- The profile does NOT need a running gateway — the dispatcher spawns it ephemerally

## Pitfalls

- **.env must still have valid API keys.** Stripping the wrong key leaves the profile with no model access. Test with `hermes -p <name> status` which shows which keys have valid values.
- **Don't strip `memory/` or `memories/`.** These hold cross-session learnings and user profile data. Empty them only if the profile has never been used (fresh clone).
- **Don't strip `sessions/` or `state.db`.** Session history lets the profile maintain continuity. A fresh state.db means the profile starts with zero memory of past tasks.
- **Verify after stripping.** Run `hermes -p <name> chat` or dispatch a test kanban task to confirm the profile still functions.
- **Check the associated skill for outdated claims.** The profile's skill (e.g. `inventory-manager`) may say "the gateway MUST be running" or reference directories that no longer exist. After stripping, load and review the skill — patch any info that's now incorrect. The minimisation changed the system; the skill must reflect the new state.

## Risk Profile

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Stripping wrong API key | Low | High (no model access) | `hermes status` before/after |
| Gateway not restarted | Medium | Low (eph spawns work) | Dispatcher handles this |
| State.db removed accidentally | Low | Low (auto-recreates) | Just slower on first boot |
