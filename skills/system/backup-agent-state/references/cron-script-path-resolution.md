# Cron Script Path Resolution

Hermes resolves cron script paths differently depending on whether the job uses `no_agent: true` or `no_agent: false` (the default).

## Resolution Rules

- **no_agent: false (agent runs)** — `~/.hermes/scripts/`. Symlinks allowed.
- **no_agent: true (shell script)** — `$HERMES_HOME/scripts/`. Symlinks blocked.

## Common Error Patterns

### Error: "Script not found: $HERMES_HOME/scripts/scripts/script.sh"

```
"last_error": "Script not found: $HERMES_HOME/scripts/scripts/brain-sync.sh"
```

**Cause:** Script path contains a `scripts/` prefix that creates double nesting.

**Fix:** Remove the `scripts/` prefix:
```bash
cp $HERMES_HOME/scripts/brain-sync.sh $HERMES_HOME/scripts/brain-sync.sh
cronjob update {job_id} script=brain-sync.sh
```

### Error: "Blocked: script path resolves outside the scripts directory"

```
"last_error": "Blocked: script path resolves outside the scripts directory ($HERMES_HOME/scripts): 'scripts/brain-sync.sh'"
```

**Cause:** A symlink in `$HERMES_HOME/scripts/` points outside that directory.

**Fix:** Replace the symlink with a direct file copy:
```bash
rm $HERMES_HOME/scripts/scripts/brain-sync.sh
cp $HERMES_HOME/scripts/brain-sync.sh $HERMES_HOME/scripts/brain-sync.sh
cronjob update {job_id} script=brain-sync.sh
```

### Error: "Script not found" for agent-based cron

For `no_agent: false` jobs, scripts resolve to `~/.hermes/scripts/<filename>`. If the file doesn't exist:

```bash
mkdir -p ~/.hermes/scripts
ln -s /path/to/canonical/script.sh ~/.hermes/scripts/script.sh
```

Symlinks are fine here — only `no_agent: true` jobs block them.

## Verification

After fixing a cron script path:

1. Run `cronjob action=list` and check `last_status` and `last_error`
2. Trigger a manual run: `cronjob action=run job_id=<id>`
3. Wait for the next tick or check `jobs.json`:
   ```bash
   python3 -c "import json; j=json.load(open('/opt/data/cron/jobs.json')); [print(f'{x[\"name\"]}: {x.get(\"last_status\")} | {x.get(\"last_error\",\"\")[:80]}') for x in j['jobs']]"
   ```

## Preventive Check

When fixing one cron job's script path, always check ALL cron jobs for the same issue.
