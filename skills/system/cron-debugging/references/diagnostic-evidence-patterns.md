# Diagnostic Evidence Patterns — Thinking Mode vs Transient Latency

## Pattern A: Thinking Mode (all must be true)
- All 3 retries die at exactly the stale threshold (e.g. 120.10s, 120.15s)
- Gateway log: `"No response from provider for 120s"` — connection alive, no first byte
- Morning success, afternoon peak failure (thinking cluster under load)
- Request dump: `"reasoning_effort": "max"` + thinking headers

## Pattern B: Stale Stream Timeout (not thinking mode)
- Die at exactly the stale threshold, not varying
- Same "No response" log pattern — connection alive
- Morning success, afternoon failure
- Request dump has thinking headers

## Expanded Diagnostic Flow
1. Read request dump, inspect body for thinking headers
2. Check `grep reasoning_effort /opt/data/config.yaml`
3. If thinking mode confirmed → fix is per-job model override (not timeout tuning)
4. Apply override, verify via request dump that thinking is absent
