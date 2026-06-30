# Broken Pipe Debug Chain

## Symptom
`[Errno 32] Broken pipe` on cron jobs during peak hours.

## Diagnostic Flow
1. Check if thinking mode is the cause: `ls -t /opt/data/sessions/request_dump_*.json | head -1` and inspect body for `reasoning_effort` and `thinking` keys.
2. Check `grep reasoning_effort /opt/data/config.yaml` — if xhigh, cron inherits extended thinking.
3. Check gateway log: `grep "No response from provider" /opt/data/logs/gateways/default/current | tail -5`

## Root Causes

| Cause | Pattern | Fix |
|-------|---------|-----|
| Thinking mode TTFT | All retries die at exactly stale threshold (120s) | Per-job model override (see profile-based-isolation.md) |
| Stale stream timeout | Timeout misconfigured or too low for context size | Increase timeout or switch to non-streaming |
| Transient API issue | Varying failure times, not clustered at threshold | Retry (already handled by scheduler) |
