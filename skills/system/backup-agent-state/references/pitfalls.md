# Pitfalls

- **Whitelist needs `/**`**: `!/dir/` only un-ignores the directory entry. Without `!/dir/**`, files inside are still ignored by the catch-all `*`.
- **Symlinks lose content**: git tracks symlinks as pointer strings, not their target's contents. Copy the directory instead.
- **SSH `~` resolution**: In SSH config files, `~` expands relative to the system HOME from `/etc/passwd`, not your shell environment. Always use absolute paths for `IdentityFile`.
- **SSH URL formats**: `host:path` (SCP-style) uses SSH config. `ssh://git@host:port/path` (URL-style) may not. Prefer SCP-style when SSH config `Host` blocks are set up.
- **First push needs verification**: Test `git ls-remote` before push. Empty repos return empty output + exit 0; missing repos return errors.
- **Known_hosts**: Add the host key early with `ssh-keyscan -p <port> <host>`. Without it `Host key verification failed` blocks `git push`.
- **no_agent cron script path**: Script paths resolve relative to `$HERMES_HOME/scripts/` (NOT `~/.hermes/scripts/`). Use a flat filename, not `scripts/brain-sync.sh`.
- **no_agent cron blocks cross-directory symlinks**: The cron system blocks symlinks whose targets lie outside `$HERMES_HOME/scripts/`. Always copy the file directly.
- **Check ALL cron jobs when fixing one path issue**: If one cron has a script path problem, others likely have the same class of issue.
- **Never use replace_all on jobs.json**: The patch tool's replace_all matches across ALL jobs indiscriminately. Use Python json.load/dump for surgical edits.
- **Restore verify ALL jobs, not just the target**: After restoring from a stale backup, every job's profile, script path, and prompt are from the backup date — each must be individually updated to current.
- **Duplicate JSON keys**: A job with two `profile` keys passes json.load but the last one wins. Always check for duplicate keys after scripted edits.
- **Curator backups don't include cron job state**: The `.curator_backups/` files capture prompts only — you must also restore `script`, `profile`, `enabled_toolsets`, `deliver`, `schedule` from a recent known-good reference.