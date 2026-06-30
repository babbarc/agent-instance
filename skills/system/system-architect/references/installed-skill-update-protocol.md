# Installed Skill Update Protocol

When an installed (base Hermes) skill is modified, it must be reverted to base AND the custom content must be preserved. Never patch an installed skill — extract the custom content, revert, then save it elsewhere.

## Phase 0 — Clarify "Upstream"

When asked "why does skill X differ from upstream," "upstream" is ambiguous. Disambiguate before acting:

1. **Git remote** (joy-brain.git) — `git diff origin/main -- skills/<path>` shows uncommitted local changes
2. **Hermes base installed** (`/opt/hermes/skills/`) — skills shipped with the Hermes agent, always write-protected
3. **Hermes optional-skills** (`/opt/hermes/optional-skills/`) — official addons, not loaded by default, also write-protected
4. **Skills Hub latest** — the upstream registry version from `hermes skills search`

**Ask the user if unclear.** "Do you mean the git repo, the Hermes base skill, or something else?" saves a wrong diff direction.

## Phase 0.5 — Prefer external_dirs Over User Copies

The cleanest way to keep base/optional skills available without maintaining user copies:

1. Add `/opt/hermes/skills/` and/or `/opt/hermes/optional-skills/` to `skills.external_dirs` in config.yaml
2. Delete any user copy at `/opt/data/skills/<path>/` that shadows a base/optional skill
3. The skill loader resolves from `external_dirs` when no user copy exists

This avoids the copy-divergence problem entirely. Only create user copies for genuinely new skills you authored.

**How resolution works:** `_find_all_skills` scans HERMES_HOME/skills/ first, then each dir in `external_dirs`. First name seen wins — user copies always shadow base/optional. `seen_names` dedup prevents duplicates.

**When NOT to use external_dirs:** when you need to patch a base skill with env-specific customizations (credential setup, local paths, workflow tweaks). In that case, keep the user copy and use the revert-extract-rehost protocol below.

## Full Protocol

### Phase 1 — Discover

```bash
# Find ALL modified installed skills (base pack + optional pack)
for f in $(find /opt/hermes/skills -name 'SKILL.md' | sed 's|/opt/hermes/skills/||'); do
  [ -f "skills/$f" ] && diff -q "/opt/hermes/skills/$f" "skills/$f" 2>/dev/null || echo "MODIFIED: $f"
done

for f in $(find /opt/hermes/optional-skills -name 'SKILL.md' | sed 's|/opt/hermes/optional-skills/||'); do
  [ -f "skills/$f" ] && diff -q "/opt/hermes/optional-skills/$f" "skills/$f" 2>/dev/null || echo "MODIFIED: $f"
done
```

### Phase 2 — Classify the Modification

Run `diff -u <base> <modified>` for each modified skill. Classify each diff hunk:

| Category | Examples | Action |
|----------|----------|--------|
| **Version tracking** | CLI flag changes (`-q`→`-k`), command renames, platforms field removal | Revert. Upstream has since updated to match. |
| **Instance config** | Custom paths, account names, credential methods | Extract to reference file under a learned skill, then revert. |
| **Workflow improvements** | Added debugging steps, pitfall docs, useful patterns | Extract to reference file under the same skill's references/, then revert. |
| **Reference files added** | Custom .md files in references/ or templates/ | Move to a learned skill's references/, then revert. |
| **Cosmetic** | Description changes, tag additions, minor wording | Revert. Not worth saving. |

### Phase 3 — Extract Custom Content

For instance config: write to a reference under the most relevant learned skill.
For workflow improvements: write to a reference under the SAME skill's own references/ directory (these are still accessible after revert).
For reference files: move to a learned skill that covers the same domain.

Best extraction targets:

| Skill Domain | Learned Skill to Host Custom Content |
|-------------|--------------------------------------|
| google-workspace, OAuth, credentials | `security/credential-pre-flight/references/google-workspace-credential-setup.md` |
| Playwright, browser paths | Usually not needed — default path `~/.cache/ms-playwright` works unless HOME is non-standard |
| Scrapling, scraping | `software/web-navigation` |
| QMD, knowledge base | `mcp/native-mcp/references/qmd-container-setup.md` |
| System architecture docs | `system/system-architect/references/` |
| Debugging methodology | `software-development/systematic-debugging/references/` |
| Image analysis patterns | `software/browser-mechanics/references/` |
| OCR patterns | `productivity/ocr-and-documents/references/` |

### Phase 4 — Bridge the Documentation Gap

After reverting an installed skill to base, the base SKILL.md may describe a setup that doesn't match the instance (e.g., base says "use JSON token files" but instance uses pass-based OAuth). The agent will follow the base skill and do the wrong thing.

Fix: in the learned skill that hosts the custom reference, add an inline bridge note. Example:

```
> **Google Workspace note:** This instance uses pass-based OAuth — credentials fetched
> via `hermes_creds.py` at runtime, not from JSON files. Load
> `references/google-workspace-credential-setup.md` before using google-workspace.
```

The bridge note goes in the learned skill's SKILL.md body, under the section most relevant to the gap. Verify discoverability: the note should appear when the agent loads the learned skill during credential or web work.

### Phase 5 — Revert + Update

```bash
# Revert to base
cp /opt/hermes/skills/<path>/SKILL.md /opt/data/skills/<path>/SKILL.md
# Or from optional pack
cp /opt/hermes/optional-skills/<path>/SKILL.md /opt/data/skills/<path>/SKILL.md

# Check for upstream updates
hermes skills check

# Apply specific updates
hermes skills update <name>
hermes skills install <name> --force # if the skill was previously disabled

# Re-enable if disabled by update
# Remove from config.yaml 'disabled:' list
sed -i '/  - <name>/d' /opt/data/config.yaml
```

### Phase 6 — Verify

```bash
# Verify all installed skills now match base
for f in $(find /opt/hermes/skills -name 'SKILL.md' | sed 's|/opt/hermes/skills/||'); do
  diff -q "/opt/hermes/skills/$f" "skills/$f" 2>/dev/null || echo "STILL DIFFERS: $f"
done
```

## What NOT to Save

- Environment-dependent failures (missing binaries, unconfigured credentials) — these are setup state, not durable rules
- Negative claims about tools ("X tool is broken") — these become self-imposed refusals
- Session-transient errors that retry fixed — save the retry pattern, not the failure
- Default paths that match the instance's actual setup — if `~` resolves to the same path, an override is debt
