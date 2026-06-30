# Violation: Snapshot Mirroring Skipped

**Observed:** A single-line intent edit to the heartbeat cron prompt was applied via `cronjob(action='update')`. The snapshot was not touched. The user asked "did you mirror the snapshot?" — the snapshot existed at `/opt/data/memory/reference/heartbeat-prompt-snapshot.md` but was never checked because cron-rules wasn't loaded before the edit.

**Lesson:** Always load cron-rules and check the snapshot file before making any cron prompt change. See `cron-rules` Step 5 of Pre-Flight.
