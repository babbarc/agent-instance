---
name: backup-agent-state
description: Set up and maintain git-based versioning and backup of agent state — memory, skills, scripts, kanban, contacts.
annotation: "Git-based versioning & backup of agent state and config"
trigger: When the user asks about backing up agent state, setting up git-based sync, configuring SSH remote, or restoring from backup.
domain: devops
---

# Backup Agent State

Back up the agent's persistent state to a remote git repo using a whitelist-inverted `.gitignore` at `$HOME`, with periodic no_agent cron for auto-sync.

## Setup

### 1. Initialize repo at home

```bash
cd $HOME
git init
git branch -m main
```

### 2. Create whitelist .gitignore

Ignore everything by default, then un-ignore specific directories:

```gitignore
*
.*

!.gitignore

!/memory/
!/memory/**
!/skills/
!/skills/**
!/scripts/
!/scripts/**
!/kanban/
!/kanban/**
!/contacts/
!/contacts/**
!/bin/
!/bin/**

**/__pycache__/
**/*.pyc
**/node_modules/
**/node_modules/**
**/.package-lock.json
skills/.usage.json
skills/.usage.json.lock
skills/.bundled_manifest

.DS_Store
*.swp
*.swo
*~
```

Gotcha: `!/dir/` only un-ignores the directory entry. Add `!/dir/**` to un-ignore contents.

### 3. Handle skills (git won't follow symlinks)

If `skills/` lives outside `$HOME`, git tracks symlinks as pointer strings, not content. Copy instead:

```bash
rm -rf ~/skills
cp -a /path/to/skills ~/skills
```

### 4. Configure SSH remote

SSH config (`~/.ssh/config`):
```
Host alps
    HostName alps
    Port 2222
    User git
    IdentityFile /abs/path/to/.ssh/id_ed25519_alps
    IdentitiesOnly yes
```

If system HOME differs from shell HOME, also copy SSH assets:
```bash
cp ~/.ssh/config /real/home/.ssh/config
cp ~/.ssh/known_hosts /real/home/.ssh/known_hosts
ln -s ~/.ssh/id_ed25519_alps /real/home/.ssh/id_ed25519_alps
```

### 5. Set remote and push

```bash
cd $HOME
git config user.email "<email>"
git config user.name "Joy Brain"
git add -A
git commit -m "🎉 initial brain dump"
git remote add origin alps:namespace/repo.git
git push -u origin main
```

## Auto-sync Cron

Two modes:

- **Agent-based (no_agent: false)** — script filename resolved relative to `~/.hermes/scripts/`. Symlinks work.
- **no_agent (no_agent: true, zero token cost)** — script filename resolved relative to `$HERMES_HOME/scripts/`. No nested paths, no symlinks. Copy the file directly.

Sync script (`$HERMES_HOME/scripts/brain-sync.sh`):
```bash
#!/bin/bash
cd $HOME
rm -rf skills
cp -a /path/to/skills skills
git add -A
if ! git diff --cached --quiet; then
    git commit -m "auto-sync: $(date '+%Y-%m-%d %H:%M %Z')"
    git push
fi
```

## Restoration

### Restore from git remote

```bash
cd /desired/home
git clone alps:namespace/repo.git .
cp -a ~/skills /original/skills/path
```

### Restore cron configs from curator snapshots (when jobs.json is corrupted)

Use the first available source in this order:

  1. **Curator backup snapshots** at `/opt/data/skills/.curator_backups/<ISO-DATE>Z/cron-jobs.json` — most recent date first
  2. **Prompt snapshots** at `/opt/data/memory/reference/<job-name>-prompt-snapshot.md` — git-versioned, contains the exact prompt text after the first `---` delimiter
  3. **Cron output files** at `/opt/data/cron/output/<job-id>/<ISO-DATE>.md` — the prompt header in each output file is the exact prompt used for that run

Steps:

  1. Copy the most recent curator backup to `/opt/data/cron/jobs.json`
  2. Verify JSON: `python3 -c "import json; json.load(open('/opt/data/cron/jobs.json'))"`
  3. Apply prompt snapshots: for each job with `memory/reference/<name>-prompt-snapshot.md`, extract the prompt (content after first `---` line) and set `job['prompt'] = text` via Python json module
  4. Restore per-job config: all production jobs use `"profile": "cron-workers"` with scripts at `profiles/cron-workers/scripts/`. Verify `script`, `enabled_toolsets`, `deliver`, `schedule` for every job — not just the affected one
  5. Commit snapshot files changes to git before verifying restoration

## Reference files

- `references/pitfalls.md` — edge cases and failures to avoid
- `references/ssh-config-resolution.md` — SSH config path resolution
- `references/cron-script-path-resolution.md` — cron script path resolution
