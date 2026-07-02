# Per-Profile Cron Worker Architecture

## Background

Hermes cron jobs run inside a profile-scoped gateway process. Each gateway has its own `InProcessCronScheduler` daemon thread that ticks every 60 seconds, reads `cron/jobs.json` from its own HERMES_HOME, and fires due jobs. This is per-profile by design (#4707).

When a cron job needs to execute under a **different** profile's config, `.env`, skills, or credentials than the gateway it was created under, the correct approach is to run a separate gateway for that profile — **not** to patch the scheduler to switch profiles mid-flight.

## Why the Scheduler-Patch Approach is Wrong

A proposed patch to `cron/scheduler.py::run_one_job()` added a `profile` field to job definitions. When firing a job, it used `set_hermes_home_override()` (ContextVar-based, from `hermes_constants`) to temporarily switch the active HERMES_HOME to the target profile's directory. Claude Opus reviewed and rejected this approach. Below are the specific failure modes.

### 1. Subprocess Blindness

`ContextVar` only changes what `_get_hermes_home()` returns within the current Python thread. `os.environ` is **process-global**. Any subprocess the cron job spawns (and every cron job agent session does — it shells out to run prompts) reads `os.environ["HERMES_HOME"]`, which still points to the **gateway's** profile. The subprocess sees the wrong `.env`, config, and credentials.

This gap is unfixable within the ContextVar approach: two different HERMES_HOME values cannot coexist in a single process's `os.environ`.

### 2. Read/Writes Split Across Profiles → Infinite Refire

The sequence inside `run_one_job()`:

1. `tick()` reads due jobs from the **gateway's** `cron/jobs.json` (ContextVar override not yet applied)
2. `advance_next_run()` writes next_run_at to the **gateway's** `cron/jobs.json` (before dispatch)
3. `run_one_job()` sets the ContextVar override to the target profile
4. `claim_dispatch()` / `mark_job_run()` execute **under the target profile's** HERMES_HOME

If those writes anchor to `_get_hermes_home()`, job scheduling state (next_run_at, last_status) is read from profile A but written to profile B. Profile A's `next_run_at` for that job never advances → the job **re-fires every tick**. Profile B accumulates status entries for a job it doesn't own.

### 3. Lock Mismatch

`.tick.lock` is resolved at tick level using `_get_hermes_home()` — the gateway's profile. If a real per-B gateway also runs (the correct configuration), both the patched gateway (A) and the real gateway (B) try to coordinate using **different lock files** — they never synchronise → **double execution** of B's jobs.

### 4. Fail-Open on Profile Resolution Error

The patch catches `Exception` during profile resolution and falls back to the gateway's default profile:

```python
except Exception as exc:
    logger.warning("...falling back to default")
```

A job meant to run under isolated profile B with its own API keys silently executes under profile A's credentials. This is a security boundary violation — the mechanism should fail closed (skip the job, record the error).

## Correct Approach: One Gateway Per Profile

### Architecture

```
┌─ Gateway (profile: A) ──────────────────┐
│  hermes -p A gateway run                 │
│  InProcessCronScheduler (60s tick)       │
│  cron/jobs.json → jobs under profile A   │
│  HERMES_HOME = ~/.hermes/profiles/A/     │
└──────────────────────────────────────────┘

┌─ Gateway (profile: B) ──────────────────┐
│  hermes -p B gateway run                 │
│  InProcessCronScheduler (60s tick)       │
│  cron/jobs.json → jobs under profile B   │
│  HERMES_HOME = ~/.hermes/profiles/B/     │
└──────────────────────────────────────────┘
```

Each gateway:
- Runs as a separate OS process
- Has its own cron ticker (no shared lock — `.tick.lock` per profile)
- Reads/writes only its own `cron/jobs.json`
- Spawns subprocesses with the correct HERMES_HOME in `os.environ`
- Can be supervised independently (systemd per profile, s6 per slot)

### Resource Considerations

| Resource | Single patched gateway | One gateway per profile |
|---|---|---|
| Memory | One process | One per profile |
| CPU | One ticker | One ticker per profile |
| Adapter init | One set of platform connections | Per-profile platform connections |
| Skills loading | Shared module cache | Independent per process |
| Failure isolation | One crash kills ALL jobs | One crash kills one profile's jobs |

The resource cost is higher per profile, but each gateway is boringly correct — no cross-cutting invariants to maintain.

## Telegram Delivery for Worker Profiles

### The Token Sharing Question

When both the default gateway and a worker-profile gateway use the same Telegram bot token for cron delivery, two processes share one token. This works correctly because Telegram's Bot API has two independent channels:

| Channel | API | Exclusivity |
|---|---|---|
| **Inbound** | `getUpdates` (polling) or `setWebhook` | **Exclusive** — one poller OR one webhook per token |
| **Outbound** | `sendMessage` (and friends) | **None** — stateless HTTPS POST, unlimited concurrent callers |

Sending is a bare authenticated HTTP POST — ten processes can call `sendMessage` with the same token simultaneously. The only limits are Telegram's rate limits (~30 msg/s global, ~1 msg/s per chat), not connection exclusivity.

### What Happens When a Worker Profile Enables Telegram

1. The worker-profile gateway starts and iterates its configured platforms.
2. For `telegram`, it calls the Telegram adapter's `connect()` (in `plugins/platforms/telegram/adapter.py`).
3. `connect()` calls `_acquire_platform_lock('telegram-bot-token', <token>, ...)` — defined in `gateway/platforms/base.py:2729`. This calls `acquire_scoped_lock()` in `gateway/status.py:933`, which writes a PID-based lock file keyed by scope + token hash.
4. The default profile's gateway **already holds this lock**. `acquire_scoped_lock` detects the existing live process → returns `(False, existing_record)`.
5. The Telegram adapter logs `"Telegram bot token already in use (PID X). Stop the other gateway first."` → sets a fatal error → `connect()` returns `False`.
6. The adapter is **NOT** added to `self.adapters[telegram]` — the gateway continues without Telegram.
7. **Result**: the worker-profile gateway has no live Telegram adapter. It logs one warning line at startup and runs without inbound polling.

### Delivery Still Works (Standalone Path)

When a cron job fires in the worker-profile gateway and needs to deliver to Telegram:

1. `_deliver_result()` in `cron/scheduler.py:1220` resolves the delivery target.
2. `pconfig = config.platforms.get(telegram)` — the platform IS configured and enabled in the worker profile's gateway config, so the config object is found.
3. `runtime_adapter = (adapters or {}).get(telegram)` — returns `None` (adapter failed to connect).
4. Falls through to the standalone path at line 1688:
   ```python
   if not delivered:
       coro = _send_to_platform(platform, pconfig, chat_id, ...)
   ```
5. `_send_to_platform` (in `tools/send_message_tool.py:723`) branches on platform:
   ```python
   if platform == Platform.TELEGRAM:
       return await _send_telegram(pconfig.token, chat_id, message, ...)
   ```
6. `_send_telegram` creates a one-shot bot client, calls `bot.send_message()` (a single HTTP POST to Telegram's `sendMessage` API), and returns. **No polling, no webhook, no exclusivity requirement.**

**Net result**: the worker-profile gateway needs Telegram configured in its `config.yaml` and the token in its `.env`, but the live adapter never connects (gracefully blocked by the lock). Delivery works via the standalone HTTP path without any token conflict.

### Minimal Config

The gateway config loader's `_apply_env_overrides()` (in `gateway/config.py:1250`) auto-discovers Telegram from `TELEGRAM_BOT_TOKEN` — it creates a `PlatformConfig(enabled=True)` internally if the env var is set. No `config.yaml` `gateway.platforms.telegram` section needed.

```bash
# Worker profile .env additions (ALL that's needed)
TELEGRAM_BOT_TOKEN=<same token as default profile>
TELEGRAM_HOME_CHANNEL=<chat_id>
```

No `enabled: true` in config.yaml, no `allowed_users`, no webhook config, no polling setup. The adapter starts (triggered by the auto-created platform config), hits the lock, fails, and the delivery code falls through to standalone sends.

### Separate Bot Token (Alternative)

If you want the worker-profile gateway to have its own full Telegram adapter (e.g., for separate inbound handling), use a different bot token. Different token → different lock scope → no conflict. The worker-profile gateway polls independently with its own bot, and deliveries arrive from a different bot name.

## Migrating Jobs Between Profiles

### Pre-Migration Checklist

Before transferring a cron job from one profile to another, verify parity for every job:

1. **Model parity** — the target profile's `config.yaml` and `.env` must have the model and API key the job's prompt was tuned for. A prompt validated against Claude produces different output on DeepSeek.

2. **Env secret parity** — data-collection scripts need credentials (Garmin, fitness APIs, Google, etc.). Copy the required env vars to the target profile's `.env`. Scripts being physically present in the target's `scripts/` dir does not mean they will run — the env vars they read must also be present.

3. **Script parity** — scripts referenced by the job (`script: <name>.sh`) must exist in the target profile's HERMES_HOME/scripts/ directory. Cron resolves scripts relative to `$HERMES_HOME/scripts/`.

4. **Skill/toolset parity** — if the job has `enabled_toolsets: ['terminal', 'file', 'skills', ...]`, verify the target profile has those skills installed. A missing skill is not an error — the agent simply lacks the tool and the job may degrade or fail.

5. **Workdir validity** — if the job has a `workdir`, verify that absolute path exists from the target profile's process. Relative paths resolve from the profile's HERMES_HOME.

### Convert `deliver: origin` to Explicit Targets

Jobs created from a CLI session stamp `origin: {platform: "cli"}`. When the job fires under the new profile, `deliver: origin` resolves to this CLI origin and delivery fails — there is no CLI adapter to send through.

**Fix**: for every migrated job, set an explicit delivery target:
- Jobs that should deliver to Telegram: change `deliver` from `origin` to `telegram:<chat_id>`
- Jobs that deliver to a specific chat: keep the explicit target
- Jobs with `deliver: local`: no change needed (they save locally only)

### Per-Job Migration Sequence

**Do NOT bulk-create then bulk-remove.** Between create (step B) and remove (step C), both profiles' tickers hold the same job. Both fire it → double delivery, and for jobs with side effects (state writes, API calls), double execution.

Correct sequence for each job:

```
1. Create the job in the target profile's cron
   (via cronjob tool or hermes -p <target> cron create)

2. Verify the job appears in target: hermes -p <target> cron list

3. Remove the original from the source profile:
   cronjob(action='remove', job_id=<id>)

4. Verify removal: cronjob(action='list')

5. Verify the next scheduled fire (optional):
   cronjob(action='run', job_id=<id>) — triggers on next tick
```

This is one job at a time. For N jobs, this takes N×3 tool calls (create, verify, remove). There is no batch-JSON-import path in the cronjob tool — each job must be created individually with its full prompt/script/config.

### Post-Migration Verification

- Source profile `hermes cron list` shows only jobs that should stay (0 if fully migrated)
- Target profile `hermes -p <target> cron list` shows all transferred jobs with correct schedules, deliver targets, and scripts
- No stale `deliver: origin` entries in migrated jobs
- Next scheduled fire for each job delivers correctly to the intended chat

## s6 Container Deployments

In the s6-overlay Docker image, each profile gateway becomes a supervised `longrun` service under `/run/service/gateway-<name>/`. The boot reconciler (`02-reconcile-profiles` → `hermes_cli.container_boot`) walks profile directories and re-registers s6 service slots:

1. Profile presence key: presence of `SOUL.md` in the profile directory
2. Auto-start condition: `gateway_state.json` has `prior_state == "running"`
3. Run script (rendered by `S6ServiceManager._render_run_script`):
   ```sh
   exec s6-setuidgid hermes hermes -p <name> gateway run --replace
   ```
4. Logs: s6-log routes to `$HERMES_HOME/logs/gateways/<name>/current`

Inspect: `docker exec <c> /command/s6-svstat /run/service/gateway-<name>`

## Systemd Host Deployments

```
hermes -p <name> gateway install      # Creates user-level systemd unit
hermes -p <name> gateway start        # Starts the service
hermes -p <name> gateway status       # Via profile-scoped PID detection
```

The systemd unit auto-starts on boot (`--start-on-login`). The profile's `gateway.pid` is written on startup for cross-profile process detection.

## References

- `cron/scheduler.py::_get_hermes_home()` docstring — explicit per-profile design (#4707)
- `cron/scheduler.py::_deliver_result()` — delivery flow with adapter → standalone fallback
- `cron/scheduler.py::_resolve_delivery_targets()` — how deliver field and origin resolve
- `plugins/platforms/telegram/adapter.py::connect()` — Telegram adapter startup + lock acquisition
- `gateway/platforms/base.py::_acquire_platform_lock()` — scoped token lock
- `gateway/status.py::acquire_scoped_lock()` — PID-based cross-process lock
- `tools/send_message_tool.py::_send_telegram()` — standalone HTTP send (no polling)
- `hermes_cli/service_manager.py::S6ServiceManager._render_run_script` — s6 profile gateway run script generation
- `hermes_cli/gateway.py::run_gateway()` — foreground gateway runner (profile-scoped)
- `hermes_cli/container_boot.py::reconcile_profile_gateways()` — boot-time s6 reconciliation
- `hermes_constants.py::set_hermes_home_override` / `reset_hermes_home_override` — the ContextVar mechanism the rejected patch used
