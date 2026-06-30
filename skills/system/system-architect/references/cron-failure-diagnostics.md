# Cron Failure Diagnostics

How to investigate a failing cron job systematically. Use when a cron job shows `last_status: error` during equilibrium checks or when a user reports a cron not delivering.

## Step 1: Collect the Error Details

```python
# Get full job config
cd /opt/data/cron && python3 -c "
import json
data = json.load(open('jobs.json'))
jobs = data.get('jobs', [])
[j for j in jobs if j.get('last_status') == 'error']
"
# Or for a specific job:
cd /opt/data/cron && python3 -c "
import json
data = json.load(open('jobs.json'))
[j for j in data.get('jobs', []) if j['name'] == '<job-name>']
"
```

## Step 2: Determine Job Type

- **no_agent=True + script set** — The script IS the job. Check the script file exists and runs standalone.
- **no_agent=False (agent job)** — The prompt IS the instruction. Check the prompt content and tool availability.

## Step 3: Check Output Logs

Output files live at `/opt/data/cron/output/<job_id>/`. Check most recent run:

```bash
ls -lt /opt/data/cron/output/<job_id>/ | head -3
cat /opt/data/cron/output/<job_id>/<latest>.md
```

Successful runs produce actual content. Failed runs produce the prompt dumped verbatim with an error appended. If the output file equals the prompt size, the agent never executed — it failed during the tool-call phase.

## Step 4: Classify the Error

| Error Pattern | Likely Root Cause | Action |
|---|---|---|
| Exit code 127 | Script references a binary/path that doesn't exist | Check script contents for hardcoded paths. The path in the script is the one that's missing. |
| Broken pipe / "Stream stale for Ns — no chunks received" | Provider-side API streaming issue — the model accepted the request but sent no response chunks within the timeout window | Check errors.log for the exact model + token count. If intermittent, inspect the request dump (see Step 8). If persistent on multiple providers, reduce context: the tool-description overhead alone (e.g. `terminal` at ~1,891 tok) can push past timeouts on slow API days. |
| Tool-call limit | Agent exceeded max turns before completing | Prompt is too complex for a single cron run. Break into simpler steps or increase max turns. |
| reCAPTCHA / vision failures | Model has no vision capability | Cron needs a vision-capable model or manual handling. |
| `last_delivery_error` set | Message sent but delivery failed | Check platform connectivity (gateway state, auth tokens). |

## Step 5: Distinguish Infrastructure vs. Prompt Bug

**Infrastructure (can't fix from here — flag it):**
- Script path doesn't exist (no_agent jobs)
- Model can't solve a vision task
- Runner/pipeline service is down
- Gateway connectivity lost

**Prompt bug (can fix):**
- execute_code blocked in cron mode — rewrite as terminal() commands
- DB-write code blocks are documentary (fenced Python) instead of actionable
- Prompt is too long and hits turn limits
- Broken pipe from complex shell pipelines
- Missing skills list in cron config

## Step 6: Check for Dead-Reference Cascades

If a script references another script or skill path that doesn't exist (like `fetch-intel.sh` → `openclaw-imports/geo-analyst/scripts/fetch-intel.sh`), the dependency is dead. The cron won't work until either:
- The dependency is restored
- The cron is rewritten to use current infrastructure
- The cron is deleted (if the functionality is no longer needed)

## Step 8 — Provider-Side Diagnostics: Request Dump Analysis

For persistent Broken pipe / "Stream stale" errors, the root cause may be context size or provider latency. The cron-workers profile captures request dumps for every failed run:

```bash
ls /opt/data/profiles/cron-workers/sessions/request_dump_cron_<jobid>_<timestamps>*.json
```

Each dump contains the **exact API payload** sent to the provider — system prompt, user message, and tool definitions. Decompose the token budget:

```python
import json
with open("request_dump.json") as f:
    data = json.load(f)
body = data["request"]["body"]
sys_msg = body["messages"][0]["content"]
user_msg = body["messages"][1]["content"]
tools = json.dumps(body.get("tools", []))
# Rough estimate: prose ~4 chars/tok, code/tool defs ~3 chars/tok
print(f"System prompt: {len(sys_msg):>6} chars ~{len(sys_msg)//4} tok")
print(f"User message:  {len(user_msg):>6} chars ~{len(user_msg)//4} tok")
print(f"Tool defs:     {len(tools):>6} chars ~{len(tools)//3} tok")
print(f"Total chars:   {len(sys_msg)+len(user_msg)+len(tools)}")
print(f"Reported tok:  {body.get('estimated_tokens', 'N/A')}")
```

**Common bloat sources in cron context:**

| Source | Typical size | Notes |
|--------|-------------|-------|
| `terminal` tool description | ~1,891 tok | Very verbose — usage guide embedded in description field |
| Kanban active task dump | ~1,900 tok | Largest data contributor — grows with active task count |
| Triage/routing rules | ~1,800 tok | Heartbeat prompt itself |
| Generic Hermes system prompt | ~1,370 tok | CLARIFY/EXECUTE/BLOCKED, tool_persistence, etc. — same as non-cron sessions |

The `errors.log` also records the precise context size at failure time:
```bash
grep "Stream stale" /opt/data/logs/errors.log | grep "cron_<jobid_prefix>"
# → "Stream stale for 180s ... context=~8,371 tokens"
```

Compare this against the request dump analysis. If the terminal tool definition alone is ~1,891 tokens and the system prompt is ~1,370 tokens of generic overhead, that's ~3,260 tokens you may not have considered as bloat.

## Step 9: Decide Fate

| Finding | Recommended Action |
|---|---|
| Intermittent failure (works some days) | Flag as infrastructure issue. Make a note in intervention_log. |
| Persistent failure + dead dependency | Either fix the dependency, rewrite the prompt, or delete the cron. |
| Paused by user | Leave paused — user made a deliberate choice. |
| Blocked by model capability | Pause and note the constraint (e.g. "needs vision"). |
