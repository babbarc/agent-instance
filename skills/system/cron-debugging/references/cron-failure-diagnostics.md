# Cron Failure Diagnostics

## Common Failure Patterns

| Symptom | Likely Cause | Action |
|---------|-------------|--------|
| Empty last_run_at/status, completed > 0 | Data corruption or manual edit | Restore from curator_backups or output logs |
| Schedule :00 but output at :09, :17 | Manual run or backlog | Check for duplicates; verify scheduler health |
| Output files show scheduler preamble in prompt | Prompt updated with headers included | Strip `[IMPORTANT]` and `## Script Output` |
| Script exits on any single-source failure | `set -euo pipefail` without fallbacks | Check if failure cascade is intentional |
| last_run_at/status self-heal after scheduled run | Fields populated by next tick | No manual intervention needed |
| Cursor file timestamp not changing | Cursor advancement guarded by broken condition | Fix status fields or advancement logic |
