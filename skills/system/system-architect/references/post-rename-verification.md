# Post-Rename Verification Protocol

When a skill is renamed (via `skill_manage(action='create', name='NEW')` + `delete(absorbed_into='NEW')`),
verify these four things that the rename itself does NOT automatically handle:

## 1 — Scripts in the Old Skill

Old scripts under the old skill directory are NOT migrated by the rename. They remain on disk
under the old category path but are no longer loadable via the skill. Check:

```bash
# List old scripts
ls old-category/old-name/scripts/
# Migrate anything useful
cp old-category/old-name/scripts/*.py new-category/new-name/scripts/
```

## 2 — Hardcoded QUERY_SCRIPT / Path Constants

Other scripts that hardcode the old skill's path must be updated manually. The rename does
not update absolute path references outside the skill directory.

Common offenders:
- `ingest_document.py` — has `QUERY_SCRIPT = "/opt/data/skills/.../old-name/scripts/query.py"`
- Cron prompts that reference `/opt/data/skills/.../old-name/scripts/...`
- Other skills' SKILL.md or reference docs with inline `python3 /opt/data/skills/.../old-name/` paths

## 3 — Reference Docs in Other Skills

Search for stale path references across ALL skills:

```bash
grep -rn "/opt/data/skills/old-category/old-name/" /opt/data/skills/ --include="*.md"
grep -rn "old-name" /opt/data/skills/ --include="*SKILL.md"
```

## 4 — Cron Prompts

Cron prompts live in `/opt/data/cron/jobs.json` (not git-tracked). Cross-reference
the old skill name or path against active cron prompts:

```bash
cronjob action=list | grep old-name
```

If found, update or recreate the cron prompt with the new path/name.

## 5 — Hub Registry

If the skill was published to a hub, unpublish the old name.

## Checklist

- [ ] Scripts migrated from old directory to new
- [ ] `ingest_document.py` `QUERY_SCRIPT` updated
- [ ] All skill reference docs updated (grep for old path)
- [ ] Cron prompts checked for stale references
- [ ] DB path constants checked if changed
