# Signal Noise Pitfalls

| Pitfall | Diagnosis | Fix |
|---------|-----------|-----|
| Pipeline-completion signal with no reader | Writes `signal add` for "collected" / "pipeline-ran" / "done" with no downstream query or dashboard consuming it | Delete the signal line. The cron's output file and `last_status` already prove delivery. |
| Life-track signal duplicating cron's own state | Same data stored in both `life_signals` table and cron's `last_status`/output log | Keep it in one place. DB signals are for cross-cron data sharing, not per-job logging. |
| "Running" / "started" signal before collection | Writes a `started` signal at the top of the script, then a `completed` one at the end | Remove both. Exit code 0 is the only "completed" signal you need. |
