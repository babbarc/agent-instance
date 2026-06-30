# Profile Skill Seeding — How Bundled Skills Flow Into Profiles

## Root Cause (Three Code Paths)

Bundled skills (skills shipped with Hermes in its `skills/` directory) are auto-seeded into profiles through three distinct paths. There is NO config.yaml flag to control this — the only opt-out is the `--no-skills` CLI flag at profile creation.

### Path 1: `hermes profile create <name>` (default)

**Caller:** `hermes_cli/main.py:11708–11726`
**Executor:** `hermes_cli/profiles.py:829–871` (`seed_profile_skills()`)

After `create_profile()` returns, the caller runs `seed_profile_skills(profile_dir)`. This spawns a **subprocess** with `HERMES_HOME` set to the new profile's directory:

```python
result = subprocess.run(
    [sys.executable, "-c",
     "import json; from tools.skills_sync import sync_skills; "
     "r = sync_skills(quiet=True); print(json.dumps(r))"],
    env={**os.environ, "HERMES_HOME": str(profile_dir)},
    cwd=str(project_root), capture_output=True, text=True, timeout=60,
)
```

The subprocess is necessary because `sync_skills()` caches `HERMES_HOME` at module level.

### Path 2: `hermes profile create <name> --clone` / `--clone-all`

**Executor:** `hermes_cli/profiles.py:770–772`

`create_profile()` itself does:

```python
source_skills = source_dir / "skills"
if source_skills.is_dir():
    shutil.copytree(source_skills, profile_dir / "skills", dirs_exist_ok=True)
```

This copies the **entire** skills directory (bundled + user-installed) from the source profile. Then the caller in main.py STILL runs `seed_profile_skills()` on top (Path 1), which picks up newly-tracked bundled skills the source didn't have.

`--clone-all` uses `shutil.copytree()` with an ignore function that excludes infrastructure artifacts (`hermes-agent`, `.worktrees`, `profiles`, `bin`, `node_modules`, `__pycache__`, `*.pyc`, `*.pyo`, `*.sock`, `*.tmp`).

### Path 3: `hermes update`

**Caller:** `hermes_cli/main.py:10668–10701`

After updating Hermes, the update routine iterates all existing profiles and runs `seed_profile_skills()` on each. This catches new/changed bundled skills shipped with the new version.

```python
all_profiles = list_profiles()
for p in all_profiles:
    r = seed_profile_skills(p.path, quiet=True)
```

## The Sync Mechanism (`tools/skills_sync.py:454–627`)

`sync_skills()` uses a **manifest** at `<profile>/skills/.bundled_manifest` (v2 format: `skill_name:md5_hash` per line).

### Discovery
Scans the repo's `skills/` directory for `SKILL.md` files via `rglob("SKILL.md")`. Each skill's name is read from YAML frontmatter. Category structure is preserved: `skills/mlops/axolotl` → `<profile>/skills/mlops/axolotl`.

### Sync Logic (per skill)

| State | Action |
|---|---|
| **New** (not in manifest, not on disk) | Copy from bundled, record hash in manifest |
| **New but name collision** (not in manifest, exists on disk) | Skip. If hashes match, record. If different, warn. |
| **In manifest + on disk + unmodified** (user hash == origin hash) | Check bundled hash. If different: backup old → copy new → record new hash. If same: skip. |
| **In manifest + on disk + user-modified** (user hash ≠ origin hash) | Skip, don't overwrite. |
| **In manifest but deleted from disk** | Skip (user's deletion is respected). |
| **Curator-suppressed** (in `.curator_suppressed`) | Skip. |

### Modification Detection

Uses `_dir_hash()` — MD5 of all filenames + file contents in the skill directory. When the user edits a skill's files, the hash changes. On next sync, if `user_hash != origin_hash`, the skill is flagged as "user-modified" and never overwritten.

## Opt-Out Mechanism

### `--no-skills` Flag

`hermes profile create <name> --no-skills` writes a `.no-bundled-skills` marker file in the profile root:

```python
(profile_dir / NO_BUNDLED_SKILLS_MARKER).write_text(
    "This profile opted out of bundled-skill seeding "
    "(`hermes profile create --no-skills`).\n"
    "Delete this file to re-enable sync on the next `hermes update`.\n"
)
```

Both `seed_profile_skills()` and `sync_skills()` check for this marker. When present, both return an empty-result dict with `skipped_opt_out: True`.

Re-enable by deleting the marker file.

### No config.yaml Flag

There is NO config.yaml section or key that controls bundled-skill seeding. The only control is the CLI flag `--no-skills` at creation time.

## Design Rationale

Each profile is a fully independent `HERMES_HOME`. Bundled skills provide the baseline agent capabilities. Auto-seeding ensures every profile starts with the same set, without needing to manually install skills.

- `--clone` preserves user-installed + modified skills from the source
- `--clone-all` does a full copy including sessions, cron, state DB
- `--no-skills` creates a minimal, intentionally empty profile
- Hash-based modification detection prevents overwriting user edits during `hermes update`

## Key Source Files

- `tools/skills_sync.py` — Core sync logic, manifest management, hash detection
- `hermes_cli/profiles.py` — `create_profile()`, `seed_profile_skills()`, marker constants
- `hermes_cli/main.py` — Profile creation command handler, update loop
