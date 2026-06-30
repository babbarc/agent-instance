# Cron Operational Health Audit

Systematic method for checking a cron's runtime health.

## Audit Sequence

### 1. Locate and Capture State
```bash
cronjob action=list
python3 -c "
import json
d = json.load(open('/opt/data/cron/jobs.json'))
for j in d['jobs']:
    if j.get('name') == '<job-name>':
        print(json.dumps(j, indent=2))
"
```

### 2. Load Snapshot (If One Exists)
```bash
read_file path=/opt/data/memory/reference/<name>-prompt-snapshot.md
```

### 3. Config Comparison
Compare every field against snapshot: schedule, script, skills, toolsets, prompt text.

### 4. Status Field Integrity
Compare `last_run_at`, `last_status`, `completed`:
- Empty status with completed > 0 = ⚠️ corruption signal
- If corrupted: restore from curator_backups or output logs

### 5. Output Log & Tool-Turn Check
```bash
ls -lt /opt/data/cron/output/<job_id>/ | head -10
grep "<job_id>" /opt/data/logs/agent.log | grep "Turn ended" | tail -5
```

| tool_turns | Meaning |
|-----------|---------|
| > 0 | Tool calls attempted |
| = 0, response = [SILENT] | Nothing to route — correct idle |
| = 0, response > 8 chars | Items silently skipped — investigate |

### 6. Script & Dependency Check
```bash
ls -la /opt/data/scripts/<script>.sh
cat /opt/data/.cache/<name>-last-ok
```
