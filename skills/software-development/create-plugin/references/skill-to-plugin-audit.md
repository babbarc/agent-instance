# Skill-to-Plugin Audit — User Skills Library (Jun 2026)

Audit performed 11 Jun 2026. Source path: `/opt/data/skills/`.

## ✅ Already Converted (4 plugins exist, all enabled)

| Plugin | Source Skill | Kind | Status |
|--------|-------------|------|--------|
| `image_gen/gemini-web` | `gemini-web-images` | Provider backend (image_gen) | Enabled |
| `network-printer` | `network-printer-diagnostics` | Tool plugin | Enabled |
| `onenote` | (standalone — no matching skill) | Tool plugin | Enabled |
| `kanban-crud` | `kanban-crud` → companion reference (v2.0.0) | Tool plugin (kanban toolset) | Enabled — needs `/reset` |

**Note:** `contacts-database` was briefly converted then reverted — it's a cron pipeline concern, not an interactive tool.

## 🟢 Strong Plugin Candidates (CLI/API wrapper, high frequency, not yet converted)

| Skill | CLI/Wrapper | Tool Shape | Priority |
|-------|-------------|------------|----------|
| `life-track-crud` | `life-track.py` (`/opt/data/scripts/life-track.py`) | `life_signal_add`, `life_summary_get`, `life_goal_list` | ★★☆ |
| `fitness-nutrition` | wger API + USDA API | `exercise_search`, `food_lookup`, `macro_calc` | ★★☆ |

## 🔵 Weaker / Niche Candidates (lower frequency or narrow scope)

| Skill | Reason |
|-------|--------|
| `notion` | `ntn` CLI exists but low usage frequency |
| `nano-pdf` | Niche — PDF text edits only |
| `maps` | OpenStreetMap/OSRM — thin wrapper, low frequency |
| `arxiv` | Niche paper search |
| `git` / `git-backup` | Terminal is natural for git; very low tool-call density |
| `himalaya` | Email CLI — email already has multiple access paths |
| `blogwatcher` | Cron-driven RSS monitoring — no interactive tool surface |
| `scrapling` | Rarely used, complex surface |

## ⚪ Already Have Built-in Hermes Tools (no plugin needed)

| Skill | Why Skipped |
|-------|-------------|
| `spotify` | Bundled plugin at `/opt/hermes/plugins/spotify/` + 7 tools |
| `browser-cdp` / `browser-cdp-protocol` / `browser-mechanics` | Built-in browser tools |
| `google-workspace` | `gws` CLI + built-in Gmail/Calendar tools |
| `github-*` | `gh` CLI integration |
| `duckduckgo-search` | Bundled `web/ddgs` plugin |
| `qmd` | Built-in MCP tools |

## 🟤 Not Plugin Candidates (guidance/patterns, no tool surface)

- `one-three-one-rule`, `professional-email`, `send-media-files`, `whatsapp`
- `life-audit`, `reminder-pattern`, `ea-domain-routing`
- `tax-return-filing`, `contract-review`, `legal-research`, `document-ingestion-pipeline`
- `expense-tracking`
- `family-organizer`, `home-manager`, `property-buy-sell`
- `travel-itinerary`, `visa-appointment-monitor`, `visa-tracking`
- `meeting-prep`, `email-triage`
- `manage-appointments`, `log-food-photo`
- `system-architect`, `distill-memory`, `patch-hermes-files`
- `hermes-infrastructure`, `hermes-s6-container-supervision`
- All `software-development/` skills (`plan`, `spike`, `subagent-driven-development`, etc.)
- All `creative/` skills
- `signal-noise-classifier`, `coding-agent-orchestrator`, `web-navigation`
- `a4-printable-documents`, `print-documents`, `pdf-generation`, `ocr-and-documents`
- `teams-meeting-pipeline`, `youtube-content`
- `credential-pre-flight`, `native-mcp`, `recaptcha-solver`
- `yuanbao`, `nutrition-analyzer`, `accounting`
- `create-plugin` (meta-skill about creating plugins)

## 🔴 Installed Skills With Stale Override Copies Under `/opt/data/skills/`

These skills are shipped with Hermes but have override copies under the user path that add nothing and confuse audits. The override directories should be removed.

| Skill | Installed Path | User Override (Remove) | Notes |
|-------|---------------|----------------------|-------|
| `openhue` | `/opt/hermes/skills/smart-home/openhue/` | `/opt/data/skills/smart-home/openhue/` | User doesn't use this skill — override should be deleted |
