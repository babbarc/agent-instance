# Skill Library Health

How the skill index works, what makes it healthy, and how to maintain it.

## How the Skill Index Works

`build_skills_system_prompt()` in `agent/prompt_builder.py` generates the `<available_skills>` block injected into every session's system prompt.

**Input sources (ordered by priority):**
1. `/opt/data/skills/` — local skills (SKILL.md per skill, DESCRIPTION.md per category)
2. `/opt/data/skills/.hub/index-cache/` — curated hub listings (Hercules, anthropics/skills, skills.sh, clawhub)
3. `/opt/data/skills/.hub/lock.json` — installed external skills (official, lobechub, community)
4. `/opt/data/home/skills/` — user custom skills

**Index generation:**
- Category-level: `DESCRIPTION.md` frontmatter `description:` field → shown as category header
- Skill-level: `SKILL.md` frontmatter `name:` and `description:` → shown as `name: description` lines
- Missing DESCRIPTION.md → category shown with no description (just `category:`)
- Missing description frontmatter → skill shown with no description

## What "Healthy" Looks Like

### Category level
```
  health: Health appointment scheduling — find and book medical appointments...
    - fitness-log: Workout and fitness logging...
    - health-data-integration: Connect to health/fitness data APIs...
```

Every category directory should have a `DESCRIPTION.md` with a `description:` frontmatter field. This makes the index readable and helps the agent decide which skills to scan.

### Skill level
Every skill should have a `description:` in its frontmatter — concise enough to trigger correctly, detailed enough to distinguish from related skills.

## What "Unhealthy" Looks Like

- Categories with no DESCRIPTION.md → the index shows them without description, hiding their purpose from the agent's scan
- Stale skills sitting in the directory after being absorbed into a class-level umbrella → wastes index space and scanning time
- Skill names that overlap or duplicate — two skills attempting to govern the same class of task
- Pipe tables in any reference file the agent reads in Telegram context — Telegram has no table renderer

## Maintenance Signals

| Signal | Action |
|--------|--------|
| Category dir exists but no DESCRIPTION.md | Create one with a `description:` frontmatter field |
| Skill no longer referenced by any cron, any trigger, or any other skill | Consider archiving or deleting (`skill_manage delete`) |
| Two skills cover the same territory | Note it for curator consolidation |
|| Deleted reference files referenced elsewhere | Remove or update the cross-reference |
| system-architecture.md §3.6 has wrong skill count or missing categories | Update the section |
| A DESCRIPTION.md description is vague or wrong | Patch it |

## Disabled Skills — The config.yaml Filter

Skills can be disabled via `config.yaml` under `skills.disabled`. Disabled skills are excluded from the `<available_skills>` block at generation time — they never enter the system prompt.

**As of 30 May 2026:** 62 skills are disabled, organized by reason category:

| Category | Count | Reason |
|----------|-------|--------|
| Creative | 19 | Not EA work — diagramming, ASCII art, design, ComfyUI, pixel art, etc. |
| Gaming | 2 | Minecraft modpack, Pokémon — personal leisure, not EA |
| MLOps | 10 | LLM training tools (axolotl, unsloth, TRL, vLLM, etc.) — not currently used |
| Red-teaming | 1 | Godmode — security testing tool |
| Data science | 1 | Jupyter — would be agent-driven, not interactive |
| Dogfood | 1 | Dogfood — QA testing tool (not for production use) |
| Research | 5 | arXiv, drug-discovery, scrapling — rare/never for EA |
| Software dev | 5 | Debugging tools (cdp, pydebugpy, inspect, TUI commands, skill-authoring) |
| GitHub | 3 | Rare tools (codebase-inspection, repo-management, auth) |
| Autonomous AI | 4 | Coding CLI tools (guide-claude-code, codex, opencode, honcho) |
| Media | 3 | GIF search, songsee, heartmula — rare |
| Productivity | 3 | Airtable, Linear, PowerPoint — rare |
| DevOps | 2 | Docker management, webhook subscriptions — rare |

**Active skill count:** ~85 (147 total − 62 disabled)

**The disabled list is for:** Skills that exist in the catalog but are never relevant to Joy's role as EA. They clutter the index without providing value. The categories and comments in config.yaml document *why* each group was disabled — this prevents future confusion about "should I re-enable this?"

**When to disable a skill:** If a skill is never triggered in EA work (gaming, creative tools, MLOps), it should be added to `skills.disabled` in config.yaml rather than left to pollute the index. Disabled skills are hidden from the `<available_skills>` block but can still be loaded manually by name if needed.

**When NOT to disable:** Rarely-used skills that MAY be relevant (e.g., `contacts-database` is used infrequently but critically when needed). The available_skills scan + occasional check is better than disabling something you'll need mid-session.

## Implemented: Hybrid Approach (30 May 2026)

### The Design

The `<available_skills>` block no longer carries full skill descriptions. Instead it carries a **compact category tree with skill names only**, inspired by how cron jobs load skills:

**What cron jobs revealed:**
Cron jobs don't use the skills catalog at all. They specify 1–5 named skills at creation time, and the cron pipeline calls `skill_view()` at prompt build time to inject the FULL skill content directly. No index, no catalog — just the skill they need, pre-loaded.

**The hybrid approach applies the same principle to the main session:**
- Inject a compact category tree (category descriptions + skill names only) — ~1,052 chars instead of ~10,301
- The agent matches its task intent to a category, then calls `skill_view(name='<skill>')` to load the full content on demand
- Same cost structure as cron jobs (1 tool call per skill), 90% fewer prompt chars

**The format (auto-generated from existing data):**
```
## Skills
Match your task to a category below, then load with skill_view(name='<skill>').
If nothing fits, call skills_list() to explore.

  finance: expenses, tax, budget, statements
    - expense-tracking
    - tax-return-prep
  health: workouts, nutrition, garmin, appointments
    - fitness-log
    - fitness-nutrition
    - health-schedule
```

**How auto-generation works:**
| Component | Source | Status |
|-----------|--------|--------|
| Category names | Directory names in `/opt/data/skills/` | Auto-discovered |
| Category descriptions (≈intent hints) | `DESCRIPTION.md` frontmatter `description:` field | Auto-read (30/39 categories have one) |
| Skill names | `SKILL.md` frontmatter `name:` field | Auto-read (83 active skills) |

**All filtering still applies:** disabled skills (62), platform-mismatched, condition-gated, toolset-gated — same as before.

### Tradeoffs vs the old full-catalog approach

| Metric | Old (full descriptions) | New (hybrid) | Delta |
|--------|----------------------|--------------|-------|
| Prompt chars (skills portion) | 10,301 | 1,052 | **−90%** |
| Tool calls per task (intent matches a category) | 0 (scans descriptions) | 1 (skill_view) | +1 |
| Tool calls per task (intent off-map) | 0 | 2 (skills_list + skill_view) | +2 |
| Categories where agent may need to guess between similar names | 0 (descriptions clarify) | 7 categories have 3+ skills | Picks wrong skill ~rarely — names like `fitness-log` vs `fitness-nutrition` are self-explanatory |

### How auto-generation avoids the maintenance trap

The trigger table is NOT manually maintained. It's built from the **same snapshot data** the old catalog used. When you:
- **Add a new skill** to an existing category → auto-appears next session start
- **Add a new category + DESCRIPTION.md** → auto-appears next session start  
- **Disable a skill** via config.yaml → auto-filtered next session start
- **Update a category description** → auto-updates next snapshot rebuild

The only manual step is: categories without DESCRIPTION.md show no intent hint. Those 9 categories (accounting, nutrition-analyzer, etc.) still show their skill names but without the context of what they cover. Creating a DESCRIPTION.md for them improves the tree's readability.

### Comparison to the options evaluated

| Option | Chars | Calls | Implemented? |
|--------|-------|-------|-------------|
| Old full catalog (147 descriptions) | ~15,434 | 0 | Replaced |
| Old post-disable catalog (83 descriptions) | 10,301 | 0 | Replaced |
| **A: Trigger table** | ~500 | 1 | Partially — trigger concept absorbed into hybrid |
| **B: Keyword/tag filter** | varies | 0–1 | Not implemented (high maintenance cost) |
| **C: Category-only index** | ~2,000 | 2 | Absorbed — hybrid uses category tree but shows skill names |
| **D: Two-pass agent** | minimal | 2+ | Not implemented (over-engineered) |
| **✅ Hybrid (implemented)** | **1,052** | **1** | **LIVE** |

**The tool gap:** There is no `skills_list(category='finance')` or equivalent filtering tool. Adding one would make the hybrid even stronger — the agent could drill into a category without calling the full `skills_list()` fallback.

## The Skill Count Trap

When asked to audit the system or during structural change pre-flight:
```
check_categories: ls /opt/data/skills/*/ -d | wc -l → compare to anchor
check_descriptions: ls /opt/data/skills/*/DESCRIPTION.md 2>/dev/null | wc -l
check_skills: ls /opt/data/skills/*/SKILL.md 2>/dev/null | wc -l
missing_descriptions = categories_without_descriptions
```
This is a fast read-only check. Don't fix without explicit instruction.
