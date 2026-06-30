# Post-Step Ordering Anti-Pattern

## The Trap

Some cron prompts include a "Post-Step" section that instructs the LLM to:

1. Compose the full deliverable (briefing, summary, report)
2. Run a `terminal()` call for a side-effect (logging to life-track, persisting a cursor, sending a status update)
3. THEN output the deliverable

**This does not work reliably.** The agent loop operates in two separate phases per turn — the LLM either makes tool calls OR returns text, but not both in a sequential "do X, then Y, then output Z" pattern within one response.

## What Actually Happens

| LLM attempts | Agent loop behavior |
|---|---|
| Outputs text with a terminal() call appended | The text is interpreted as the final response; the terminal() call is lost or executes in a different turn |
| Outputs terminal() first, then text | The text after the tool call becomes the next turn's message (separate user message), not a paired response |
| Tries to do both in one response | Only one phase is honored — typically the text phase wins as the "final response" and the tool call is dropped |

## The Root Cause

The prompt violates the **Action-First Delivery** principle from cron-rules:

> "Complete all tool calls, then produce output."

A Post-Step that says "run terminal(), then output the briefing" reverses this: it asks for the briefing first, then the tool call. The LLM either reorders the steps unpredictably or drops one.

## The Fix

**Move side-effects to the data script.** Any deterministic IO (logging, persistence, cursor advancement) belongs in the pre-run data script, not in the LLM prompt:

```bash
# In the data-collection script — NOT in the LLM prompt
python3 /opt/data/scripts/life-track.py signal add daily_pulse briefing \
  delivered 'goals | calendar | kanban | health'

# Then INJECT that signal response alongside the other data sections
echo "=== BRIEFING SIGNAL ===
pulse logged at $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
```

If the side-effect depends on LLM judgment (e.g. "log the goal pulse the LLM identified"), there are two options:

**Option A — Output-first with post-hoc log:** Have the LLM output the briefing including the judgment call in a structured section. A follow-up no_agent script or a second cron job parses and logs it.

**Option B — Data script pre-logging (preferred):** Log `delivered ''` (empty note) from the data script so the pulse timestamp is recorded. The LLM doesn't need to log — it just delivers the briefing. The timestamp is already proof of delivery.

## Detecting This Pattern

Search cron prompts for any instruction that places a `terminal()` call AFTER a "compose" or "output" section:

```
grep -l "Post-Step\|post-step\|Then output\|then present\|finally output" /opt/data/cron/jobs.json
# Or scan prompts:
python3 -c "
import json, sys
with open('/opt/data/cron/jobs.json') as f:
    jobs = json.load(f)
for j in jobs.get('jobs', []):
    p = j.get('prompt', '') or ''
    if 'terminal()' in p.split('## Output')[-1:] if '## Output' in p else False:
        print(f'{j[\"name\"]} ({j[\"id\"]}): post-step terminal() detected')
"
```
