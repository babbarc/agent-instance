# Diagnosing Zero-Tool-Call Cron Runs

> When a cron prompt is correctly structured but the LLM produces text output instead of executing routing actions via terminal(), use this workflow to isolate the cause.

## Quick Diagnostic (30 seconds)

### A. Session DB — read what the LLM actually said (preferred)

Check `state.db` for the cron session and read the LLM's verbatim output. This is the most direct approach — you see exactly what the LLM responded, no log parsing needed:

```bash
# Find the cron session(s) for this job
sqlite3 /opt/data/state.db "SELECT id, started_at, message_count, end_reason \
  FROM sessions WHERE id LIKE '%<job_id>%' \
  ORDER BY started_at DESC LIMIT 5;"
```

Then read the messages:

```bash
sqlite3 /opt/data/state.db "SELECT id, role, content \
  FROM messages WHERE session_id = '<session_id>' ORDER BY id;"
```

| Pattern | Diagnosis |
|---------|-----------|
| Only user message, no assistant response | LLM call failed or job was killed mid-flight |
| Assistant response = `[SILENT]` | Correct behavior — nothing worth reporting |
| Assistant response = descriptive text, no tool calls | Data existed but LLM chose text over tools |

**When to use this vs agent.log approach:** Use session DB when you want the full verbatim output to read, or when agent.log rotation has removed the relevant entries. Use agent.log (below) when you only need tool_turns counts and don't need the full text.

### B. Agent log — check tool_turns

```bash
# Check the most recent run's tool_turns
grep "<job_id>" /opt/data/logs/agent.log | grep "Turn ended" | tail -5
```

**Output:** `tool_turns=N last_msg_role=assistant response_len=M`

| Pattern | Diagnosis |
|---------|-----------|
| `tool_turns=0, response_len=8` | Nothing to route — `[SILENT]` correct behavior |
| `tool_turns=0, response_len>8` | Data existed but LLM chose text over tools |
| `tool_turns>0` | LLM is making tool calls — check if the RIGHT calls were made |

**Second signal: check output token volume against response length.**

```bash
# Check the API call's output token count
grep "<job_id>" /opt/data/logs/agent.log | grep "API call #1" | tail -5
```

Look for `out=N` tokens vs `response_len=M`. If `out > 5000` and `response_len < 500` with `tool_turns=0`, the model spent **heavy reasoning tokens** thinking through the prompt's decision tree but never broke out to call tools. This is a signature of a reasoning model (DeepSeek v4 Flash) getting stuck in internal deliberation instead of acting. High output tokens + zero tool calls = the model is thinking, not doing.

## Full Investigation Sequence

### Step 1: Verify the assembled prompt is clean

Read the latest output file:

```bash
ls -lt /opt/data/cron/output/<job_id>/ | head -3
cat /opt/data/cron/output/<job_id>/<latest>.md
```

**What to check:**
- The data ` ``` ` block must close cleanly before the instruction body starts
- The 💥 instruction marker (or equivalent) should be on its own line after the closing ```
- No extra characters, missing newlines, or formatting artifacts between data and instructions

**The correct transition looks like:**
```
```
(kanban data...)
```

💥 You are Joy executing...
```

**A corrupted transition causes the LLM to treat part of the instruction as data, or part of the data as instruction — both lead to erratic tool call behavior.**

### Step 2: Compare across multiple runs

```bash
grep "<job_id>" /opt/data/logs/agent.log | grep "Turn ended" | tail -20
```

**Look for a pattern:**
- Do runs with MORE data (more WhatsApp lines, more emails) make tool calls?
- Do runs with LESS data (1-2 items, mostly noise) default to text-only?

**If yes, the issue is model inconsistency —** the model (DeepSeek v4 Flash in particular) routes correctly under high data volume but defaults to text generation on sparse data. The preamble is a contributing factor but not the sole cause.

**Volume thresholds observed (empirical, DeepSeek v4 Flash):**
- 150+ WhatsApp lines + multiple emails → likely routes (16 tool turns)
- 3-7 WhatsApp lines + 2-5 emails → may not route (0 tool turns)
- Single actionable item among noise → may not route

### Step 3: Check the routing logic for structural blockers

Read the prompt's decision flow from `jobs.json`:

```python
python3 -c "
import json
d = json.load(open('/opt/data/cron/jobs.json'))
for j in d['jobs']:
    if j.get('name')=='<name>':
        print(j['prompt'])
        break
"
```

**Check Step 1 of the routing decision tree:**

| Step 1 Wording | Effect on Purchase Confirmations |
|---------------|----------------------------------|
| "Does this need tracking across cycles?" | **BLOCKED** — one-shot purchases have no deadline, no multi-day steps → ALL false → D (output only). The routing table is never reached. |
| "Is the item's type in the routing table?" | **CORRECT** — purchase confirmations are in the routing table → Yes → proceed to routing. |

**Fix for blocked prompts:** Change Step 1 from tracking-based to routing-table-based. See `references/routing-table-authority.md` for the full pattern.

### Step 4: Test with a different model

If steps 1-3 check out and the model still won't call tools on low-volume data, try:

1. Run a manual heartbeat test with a model known to be reliable at tool use (Claude, GPT-4o)
2. If the other model routes correctly, the issue is model-specific — DeepSeek v4 Flash is inconsistent on low-data tool calls
3. Mitigations:
   - Switch the cron to a more reliable model
   - Accept the inconsistency (it will route correctly on high-volume runs)
   - Increase data volume artificially (not recommended — wastes tokens)

### Step 5: Check for system-level changes (patches, restarts)

Three things can silently change cron behavior without touching the prompt:

**A. Patches folder.** Check `/opt/data/home/.hermes/patches/` for `.patch` files related to prompt_builder, agent init, or tool registration:

```bash
ls -lt /opt/data/home/.hermes/patches/
```

Key patches to look for:
- `prompt_builder.py.patch` — changes how SOUL.md is loaded into the system prompt
- `memory_tool.py.patch`, `skill_manager_tool.py.patch` — changes tool descriptions that affect the LLM's understanding
- `approval.py.patch` — changes threat detection patterns that could silently block commands

Verify whether each patch was actually APPLIED or just saved (the `.patch` file may exist but the live `.py` file may still be the original). The patch file records a diff — it does not prove the patch was applied. This is important: **a saved-but-unapplied patch is not active.** Check the live file's modification date against the patch's creation date:

```bash
stat --format '%y' /opt/hermes/agent/prompt_builder.py
stat --format '%y' /opt/data/home/.hermes/patches/prompt_builder.py.patch
```

Compare also against `cron/output/<job_id>/<date>.md` timestamps — did the zero-tool-call pattern start before or after the patch was saved?

**B. Gateway restarts.** Check agent.log for gateway restart events:

```bash
grep "Gateway Starting" /opt/data/logs/gateways/default/current | tail -5
```

A gateway restart clears in-memory state and resets the credential pool. If the restart coincides with the first zero-tool-call run, it may have caused a credential pool reset that affected the API connection.

**C. API failure preceding the pattern.** If a run failed with `Broken pipe` or `ReadError` (the API stream dropped mid-response), the next run — even if successful — may have different model behavior. This is not a code bug but a model-side phenomenon. To check:

```bash
grep "<job_id>" /opt/data/logs/agent.log | grep "Turn ended" | tail -20
```

If the first zero-tool-call run follows immediately after a failed run (Broken pipe / ReadError), note the correlation. The failure itself is not the root cause, but it marks a point where the model's response pattern shifted.

### Step 6: Check the scheduler preamble

The scheduler injects this preamble BEFORE every cron run:

```
[IMPORTANT: You are running as a scheduled cron job. DELIVERY: Your final response will be
automatically delivered to the user — do NOT use send_message or try to deliver the output
yourself. Just produce your report/output as your final response and the system handles the rest.
```

This frames the task as "write text." Your prompt must actively counter this frame. See Pitfall 20 for mitigation techniques.

**However, be aware:** Even strong counter-framing may not be enough on models prone to text-over-tools behavior (DeepSeek v4 Flash). The preamble is a factor, not the root cause.

## Summary Decision Tree

```tool_turns > 0?```
├── Yes → Check if the RIGHT calls were made (correct routing, no missed items)
└── No →  Check output token volume vs response length
           ├── out > 5000, response < 500 → Model spent heavy reasoning but didn't act
           │   └── Check: was there a recent API failure (Broken pipe)?
           │       ├── Yes → API failure may have shifted model behavior (next section)
           │       └── No → Model-specific: routes high-volume, not low-volume
           └── out ~ response → Normal text output
                ├── Check assembled prompt format
                │   ├── Corrupted → Fix format (extra chars between data and instructions)
                │   └── Clean → Check data volume across runs
                │                ├── High-volume routes, low-volume doesn't → Model inconsistency
                │                └── Never routes → Check routing logic (Step 1 gate?)
                │                                     ├── Blocked at Step 1 → Fix routing gate
                │                                     └── Correct logic → Check system changes
                │                                                          ├── Patches applied? → Check patches/
                │                                                          ├── Gateway restarted? → Check agent.log
                │                                                          └── Tools available? → Check enabled_toolsets

## API Failure Pattern

When a cron run fails mid-stream with a Broken pipe error (the connection dropped while the model was generating), the **next** run may exhibit `tool_turns=0` even on data that previously routed correctly. This is not caused by a code change, prompt change, or system patch — it coincides with the API failure.

**Evidence (DeepSeek v4 Flash, heartbeat-watchdog):**
- Runs before API failure: 9 tool_turns (12:57), 2 tool_turns (13:25)
- First failure: 14:09 — Broken pipe after 547s
- Runs after API failure: consistently 0 tool_turns (14:17, 15:18, 15:36) even with new prompt versions

**What to do about it:**
1. Verify the prompt is correctly framed (action-first, terminal() notation, no conflicting gates)
2. Accept that low-volume runs may not route — the model routes correctly when data volume is high
3. If reliable routing is critical, switch to a model with better tool-use consistency (Claude, GPT-4o)
4. Do NOT keep rewriting the prompt — the prompt is not the root cause for post-failure runs
