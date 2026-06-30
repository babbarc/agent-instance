# Consequence of Direct File Editing (June 2026)

**Incident:** A single `patch()` call on `cron/jobs.json` to modify one prompt introduced an escape-sequence mismatch that corrupted the entire 65KB JSON file.

**Impact:**
- Required curator backup restoration
- Prompt reconstruction from 13 git-versioned snapshot files
- Estimated recovery: 45+ minutes of user frustration

**Preventable by:** Running `cronjob(action='update', prompt=...)` instead of direct file editing. See the Wrapper-First Policy in the main SKILL.md.
