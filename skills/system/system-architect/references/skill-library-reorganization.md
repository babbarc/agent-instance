# Skill Library Reorganization Protocol

When a skill library accumulates skills in wrong categories (dumping grounds, scattered single-skill categories, or renamed skills at stale paths), a full reorganization is needed.

## When to Reorganize

- A category has 8+ unrelated skills across different domains
- A category has exactly 1 skill that fits naturally into another existing category
- Skills were renamed but their category directories weren't updated
- Categories were deleted but their DESCRIPTION.md files remained on disk
- An LLM would struggle to guess which category a skill lives in

## The Procedure

### Phase 1 — Plan the New Structure

1. **List current categories:** `ls -d /opt/data/skills/*/`
2. **For each category with learned skills, ask:**
   - Does this name clearly describe what the skills DO? (noun-based, activity-referencing)
   - Are the skills related? Or was it a dumping ground?
   - Could it merge into a broader one without losing clarity?
3. **Design principles:**
   - Use single-word nouns: `finance`, `health`, `home`, `legal`, `travel`, `system`, `software`
   - Prefer action domains over abstract concepts: `contacts` not `personal-network`
   - Avoid vague names — `life-management` is a dumping ground signal
   - Merge single-skill categories unless genuinely distinct
   - Target 2-6 skills per category for LLM scan-ability
4. **Document the mapping:** old category → new category for each skill

### Phase 2 — Execute Moves

```bash
cd /opt/data/skills
mkdir -p system personal contacts software
mv old-category/skill-name new-category/
```

After each batch, verify: `test -f new-category/skill-name/SKILL.md`

### Phase 3 — Clean Up Empty Categories

Old categories often retain DESCRIPTION.md files after skills are moved:
```bash
ls emptied-category/           # If only DESCRIPTION.md → safe to remove
rm emptied-category/DESCRIPTION.md
rmdir emptied-category         # Only if now empty
```

Do NOT remove categories that still contain installed base Hermes skills.

### Phase 4 — Create DESCRIPTION.md for New Categories

```bash
echo "System governance — architecture, auditing, crons, git, kanban" > system/DESCRIPTION.md
```
Keep descriptions short (80-120 chars) — they appear in skills_list() category headings.

### Phase 5 — Fix Stale Cross-References

Category moves do NOT break `skill_view(name=...)` references (those use names, not paths). But they DO break inline script paths like `python3 /opt/data/skills/<old-category>/<skill>/scripts/...`. Find and fix these:

```bash
grep -rn "/opt/data/skills/<old-category>/" skills/ --include="*SKILL.md"
```

Also verify frontmatter `category:` fields point to the correct parent:

```bash
grep -rn "^category:" skills/ --include="*SKILL.md"
```

**After any rename, run the full post-rename verification protocol:**

### Script Migration — The Hidden Gap

When a skill is renamed or merged, its `scripts/` directory does NOT automatically move. This creates a silent breakage: reference docs and cron prompts may be updated to point to a new path, but the actual script file stays in the old directory and becomes unreachable.

**Three outcomes, one correct:**

| Path type | What to do |
|-----------|-----------|
| **Shared/central script** — referenced by other skills, cron prompts, or `ingest_document.py`-style constants | Copy to `/opt/data/scripts/` first, then update all references to point there |
| **Internal script** — only used by the skill's own SKILL.md or references | Move to the new skill's `scripts/` directory |
| **Abandoned script** — not referenced anywhere | Leave or delete during cleanup |

**Verification checklist after any rename or merge:**

1. `ls old-skill-dir/scripts/` — does the old skill have scripts?
2. `grep -rn "old-skill-dir/scripts/" /opt/data/ --include="*.py" --include="*.md"` — who references them?
3. For each reference found in (2): is the path correct for the new location?
4. For each script found in (1): if external code depends on it, copy to `/opt/data/scripts/`; if not, move to new skill's `scripts/`
5. `test -f` each script at its new path to confirm the file actually arrived
6. Test-run: `python3 /path/to/script.py <test-args>` — does it still work?

**Common failure mode:** Reference docs get updated to `/opt/data/scripts/query.py` but the script is never copied there. The next cron run produces fabricated data because the LLM can't find the real script — but reports "ok" because it fills in plausible-looking numbers rather than failing loudly.

External path constants (e.g. `ingest_document.py`'s `QUERY_SCRIPT`) and cron prompt paths are NOT changed by the rename itself — they must be updated separately.

### Phase 6 — Verify

```bash
# All skills present
test -f "skills/system/cron-rules/SKILL.md" || echo "MISSING"

# No stale path references
grep -rn "/opt/data/skills/<old-category>/" skills/ --include="*SKILL.md" || echo "Clean"

# Empty dirs removed
find skills -empty -type d
```

## Common Failure Modes

| Failure | Symptom | Fix |
|---------|---------|-----|
| DESCRIPTION.md blocks rmdir | `rmdir: Directory not empty` on empty-looking dir | `rm <dir>/DESCRIPTION.md` first, then rmdir |
| Broken script paths | File not found errors at runtime | Grep SKILL.md files for old category path pattern |
| Moved but not found | Skills_list shows nothing in new category | mv may have failed silently — check with `ls` |
