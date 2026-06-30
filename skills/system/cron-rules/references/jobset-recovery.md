# Jobset Recovery — Reconstructing jobs.json

When `cron/jobs.json` is corrupted (broken JSON, stale backup restored over current jobs), reconstruct it from available snapshots. Sequence:

## 1. Restore job structure from curator backup

The curator at `/opt/data/skills/.curator_backups/` creates dated full-file snapshots of `cron-jobs.json`:

```bash
ls /opt/data/skills/.curator_backups/
# Pick the most recent ISO-datetime directory
cp /opt/data/skills/.curator_backups/<latest>/cron-jobs.json /opt/data/cron/jobs.json
```

This gives you all job configs (id, name, schedule, deliver, toolsets, skills, profile, scripts) at the snapshot date. Verify the JSON is valid:

```bash
python3 -c "import json; json.load(open('/opt/data/cron/jobs.json')); print('OK')"
```

## 2. Identify current vs stale jobs

Cross-reference the restored jobs against running jobs by comparing to cron output directories:

```bash
python3 -c "
import json, os

output_dirs = set(os.listdir('/opt/data/cron/output/'))
with open('/opt/data/cron/jobs.json') as f:
    data = json.load(f)
file_ids = set(j['id'] for j in data['jobs'])

missing = output_dirs - file_ids  # running jobs missing from file
extra = file_ids - output_dirs    # stale jobs in file
print(f'Missing (need to add): {missing}')
print(f'Extra (stale): {extra}')
"
```

- **Missing jobs** that have no output dirs may be newer jobs added after the snapshot date. Add them from prompt snapshots (see step 3).
- **Extra jobs** without output dirs are stale. Remove them from the `jobs[]` list.

## 3. Override prompts from prompt snapshots

Job structure (id, schedule, deliver, etc.) comes from the curator backup. Prompt content comes from memory tree reference files:

```python
SNAPSHOTS_DIR = '/opt/data/memory/reference'
name_to_snapshot = {
    'job-name-in-cron': 'job-name-prompt-snapshot.md',
    # ... map each job to its snapshot file
}

import os, json

with open('/opt/data/cron/jobs.json') as f:
    data = json.load(f)

for job in data['jobs']:
    name = job.get('name', '')
    if name in name_to_snapshot:
        snap = os.path.join(SNAPSHOTS_DIR, name_to_snapshot[name])
        with open(snap) as f:
            content = f.read()
        # Extract prompt after the --- separator
        idx = content.find('\n---\n')
        if idx != -1:
            job['prompt'] = content[idx + 5:].strip()

with open('/opt/data/cron/jobs.json', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
```

No_agent jobs (garmin-daily-snapshot, cron-output-cleanup, auto-sync, qmd-auto-embed) should keep their empty prompts — they don't have snapshots.

## 4. Verify

```bash
python3 -c "
import json
with open('/opt/data/cron/jobs.json') as f:
    data = json.load(f)
print(f'{len(data[\"jobs\"])} jobs, JSON valid')
"
```

Then check each job's prompt length against its snapshot to confirm the override applied.
