# Divergent Snapshot Recovery

| Pitfall | Diagnosis | Fix |
|---------|-----------|-----|
| Snapshot says step was removed but live prompt still has it | Snapshot metadata was updated but `cronjob action='update'` was never called for the stored prompt. Next session trusts the snapshot and misses the real state. | Always update `jobs.json` FIRST via `cronjob action='update'`, THEN update the snapshot. The snapshot is a reference copy, not a source of truth — it must always lag reality. |
| Data script was rewritten but prompt references old terminal() steps | The data script changed, but the prompt still instructs the LLM to call terminal() for data the script now collects. | After rewriting a data script, audit the prompt's Actions section for now-redundant terminal() calls. |
| Snapshot `Last updated` date unchanged after a patch | The snapshot was edited but the date line wasn't bumped. Future maintainer can't tell if the snapshot reflects pre- or post-change state. | Update the `Last updated: YYYY-MM-DD` line on every snapshot change. Include what changed in parentheses. |
| Prompt updated but snapshot deleted (false clean state) | Snapshot was deleted instead of updated, removing any record of the previous state. | Keep the snapshot. Update it. A stale snapshot can be corrected; a deleted one loses all context about what the prompt used to look like. |
