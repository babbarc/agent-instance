---
name: cron-debugging
description: "Diagnose and fix failing cron jobs — finish_reason analysis, thinking mode debug chain, profile isolation, health audit procedure. Load when a cron job misbehaves or reports errors."
annotation: "Cron failure diagnosis: thinking debug, health audit"
version: 1.0.0
metadata:
  hermes:
    related_skills: [cron-rules, cron-prompt-design, cron-script-design, system-architect]
---

# Cron Debugging

> Load when a cron job misbehaves, reports errors, or you need to trace a failure. Not for normal chat sessions.

## Procedure

### 1. List and Locate the Job

```bash
cronjob action=list
```

Find the target cron by name or job_id. Capture its full state:

```python
import json
d = json.load(open('/opt/data/cron/jobs.json'))
for j in d['jobs']:
    if j.get('name') == '<job-name>':
        print(json.dumps(j, indent=2))
```

Fields to capture: `id`, `name`, `prompt`, `script`, `skills`, `enabled_toolsets`, `schedule`, `last_run_at`, `last_status`, `last_error`, `repeat.completed`, `state`.

### 2. Check Status Field Integrity

Compare `last_run_at`, `last_status`, and `repeat.completed` for internal consistency:

| Pattern | Meaning |
|---------|---------|
| `last_run_at` set, `last_status: "ok"`, completed: N | Healthy |
| `last_run_at` set, `last_status: "error"` | Last run failed — investigate |
| Empty `last_run_at`/`status`, completed > 0 | ⚠️ Corruption — run was recorded but status fields cleared |

### 3. Read Recent Output Logs

```bash
ls -lt /opt/data/cron/output/<job_id>/ | head -5
```

Check the most recent output file for:
- `[SILENT]` → correct idle behavior
- Tool calls were attempted (check for terminal() calls)
- Scheduler preamble present but should be stored prompt only? (see cron-prompt-design Step 1)

### 4. Diagnose the Failure

#### 4a. Finish_Reason Analysis

Before changing any prompt, check the API `finish_reason`:

| `finish_reason` | Meaning | Fix Path |
|----------------|---------|----------|
| `stop` / `end_turn` | Model decided to stop | Prompt fix needed |
| `length` | Token limit hit | Increase `max_tokens` |
| Missing / timeout | Stream died before completion | Non-streaming, larger timeout, stale-stream threshold |

#### 4b. Thinking Mode Debug Chain

If the cron fails with `[Errno 32] Broken pipe`, trace whether extended thinking causes timeout:

**Evidence for thinking-mode timeout (all must be true):**
1. All 3 retries die at exactly the stale threshold (e.g. 120.10s, 120.15s)
2. Gateway log shows `"No response from provider for 120s"`
3. Morning runs succeed, afternoon peak runs fail (thinking cluster under load)
4. Request dump body contains `"reasoning_effort": "max"` and `"thinking": {"type": "enabled"}`

**Check command:**
```bash
ls -t /opt/data/sessions/request_dump_*.json | head -1 | xargs python3 -c "
import json, sys
d = json.load(open(sys.argv[1].strip()))
b = d['request']['body']
print('reasoning_effort:', b.get('reasoning_effort'))
print('thinking:', b.get('extra_body', {}).get('thinking'))
"
```

**Fix:** Apply per-job model override — see Step 5.

#### 4c. Script and Dependency Verification

```bash
ls -la /opt/data/scripts/<script-name>.sh
# Check every dependency referenced in the script:
for dep in whatsapp_delta.py gmail_delta.py resolve-email-senders.py; do
    ls -la "/opt/data/scripts/$dep" || echo "MISSING: $dep"
done
```

Check cursor file if the script uses one:
```bash
cat /opt/data/.cache/<name>-last-ok
stat /opt/data/.cache/<name>-last-ok
```

### 5. Apply Per-Job Model Override (If Thinking Mode Is the Cause)

If extended thinking is causing >120s TTFT on routine cron jobs:

**Decision tree:**
- Routine triage / scoring / routing? → Override needed
- Deep analysis required? → Keep global config

**Option A — Disable thinking globally (recommended if most crons are routine):**
Set `reasoning_effort: none` in `config.yaml`.

**Option B — Lower thinking effort:**
Set `reasoning_effort: low` or `medium` in `config.yaml`.

**Option C — Profile-based isolation (best for mixed workloads):**
Create a dedicated cron profile with reduced reasoning_effort:
```bash
hermes profile create cron-workers --no-skills
rm /opt/data/profiles/cron-workers/SOUL.md
```
Set `reasoning_effort: medium` in profile's `config.yaml`.

See `references/profile-based-isolation.md` for full steps and verification.

### 6. Run the Health Audit

When asked to verify a cron is in good state, see `references/cron-ops-health-audit.md` for the full audit sequence (config comparison, status integrity, output logs, tool-turn verification).

### 7. Cross-Cron Systemic Scan

When you fixed a stale path, outdated pattern, or broken reference in one cron, scan ALL crons for the same pattern:

```bash
python3 -c "
import json
with open('/opt/data/cron/jobs.json') as f:
    jobs = json.load(f)
for job in jobs.get('jobs', []):
    prompt = job.get('prompt', '') or ''
    if '<stale-pattern>' in prompt:
        print(f'{job.get(\"name\")} ({job.get(\"id\")}): stale ref')
"
```

Where `<stale-pattern>` is the string you just fixed. Fix all matches before moving on.

## References

- `references/deepseek-thinking-debug-chain.md` — Full injection chain debug from config.yaml to API body
- `references/diagnostic-evidence-patterns.md` — Distinguishing thinking-mode TTFT from transient latency
- `references/v0.17.0-profile-removal.md` — Upstream history, two failure modes, and workarounds
- `references/broken-pipe-debug-chain.md` — System-specific Broken pipe debug
- `references/cron-ops-health-audit.md` — Full operational health audit procedure
- `references/cron-failure-diagnostics.md` — Additional failure patterns and fixes
- `references/hermes-patches-system.md` — Hermes patch system reference
- `references/scratchpad-offloading-techniques.md` — Research backing and decision tree for scratchpad alternatives
- `references/profile-based-isolation.md` — Full profile creation steps, reasoning_effort tuning, verification
