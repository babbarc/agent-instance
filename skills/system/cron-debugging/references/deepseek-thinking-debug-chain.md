# DeepSeek Thinking Debug Chain

Trace whether `[Errno 32] Broken pipe` on a cron job is caused by `reasoning_effort: xhigh` triggering extended thinking mode.

## The Injection Chain

```
config.yaml agent.reasoning_effort: xhigh
  → parse_reasoning_effort("xhigh") → {"enabled": True, "effort": "xhigh"}
    → DeepSeekProfile.build_api_kwargs_extras()
      → maps "xhigh" → "max"
        → sends: "reasoning_effort": "max" + "thinking": {"type": "enabled"}
```

## Evidence Pattern (All Must Be True)

1. All 3 retries die at exactly the stale threshold (120.10s, 120.15s — not varying)
2. Gateway log shows `"No response from provider for 120s"`
3. Morning runs succeed, afternoon peak runs fail (DeepSeek's thinking cluster under load)
4. Request dump body contains `"reasoning_effort": "max"` and thinking headers

## How to Check

```bash
ls -t /opt/data/sessions/request_dump_*.json | head -1
grep reasoning_effort /opt/data/config.yaml
grep "No response from provider" /opt/data/logs/gateways/default/current | tail -5
```
