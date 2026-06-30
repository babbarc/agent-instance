# Ghost DB Remediation

## The Problem
Two life-tracking.db paths existed:
- **Canonical:** `/opt/data/life/life-tracking.db`
- **Ghost:** `/opt/data/memory/life/life-tracking.db` (zero-byte stale copy)

Crons that resolved `$HERMES_HOME` differently wrote to different databases. Queries showed missing data because they read the other copy.

## Detection
```bash
find /opt/data -name "life-tracking.db"
# Expected: exactly /opt/data/life/life-tracking.db
```

## Remediation Protocol
When touching life-tracking.db from any cron:
1. Fix the prompt to use `/opt/data/life/life-tracking.db` (not `$HERMES_HOME/memory/life/`)
2. Update the snapshot
3. Scan ALL crons for the same stale pattern:
```python
import json
with open('/opt/data/cron/jobs.json') as f:
    jobs = json.load(f)
for job in jobs.get('jobs', []):
    prompt = job.get('prompt', '') or ''
    if '/opt/data/memory/life/life-tracking.db' in prompt:
        print(f'STALE PATH: {job.get("name")} ({job.get("id")})')
    if 'cron-persist.py' in prompt:
        print(f'STALE WRAPPER: {job.get("name")} ({job.get("id")})')
```
4. Fix every match. Zero hits before declaring done.
