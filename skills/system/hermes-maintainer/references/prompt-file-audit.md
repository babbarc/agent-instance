# Prompt File Cross-Profile Audit

## Purpose

Audit ALL files that build the system prompt for the default profile and every named profile. Detect overlaps, contradictions, stale content, and consolidation opportunities. This is distinct from the consistency audit (file-by-file correctness check) and the brain architecture audit (system health) — this is a cross-file, cross-profile composition audit.

## Discovery Phase

### 1. Find All Prompt Files

Find every file that feeds into the system prompt:

| File type | Loaded by | Search pattern |
|-----------|-----------|---------------|
| SOUL.md | `load_soul_md()` | `find $HERMES_HOME -name 'SOUL.md' -not -path '*/memory/*'`; `find /opt/data/profiles -name 'SOUL.md'` |
| MEMORY.md | `memory_tool` | `find $HERMES_HOME -name 'MEMORY.md'`; `find /opt/data/profiles -name 'MEMORY.md'` |
| USER.md | `memory_tool` | `find $HERMES_HOME -name 'USER.md'`; `find /opt/data/profiles -name 'USER.md'` |
| .hermes.md | `build_context_files_prompt()` | Walk from cwd up to git root |

### 2. Understand Loading Mechanics

**load_soul_md()** — reads only SOUL.md from `get_hermes_home()`:
- Default profile (HERMES_HOME root): loads `SOUL.md` from `/opt/data/`
- Named profiles (HERMES_HOME inside `profiles/`): loads `SOUL.md` from profile dir

**memory_tool** — reads MEMORY.md + USER.md from `get_hermes_home() / "memories/"`:
- Default: `/opt/data/memories/MEMORY.md` and `/opt/data/memories/USER.md`
- Named profile: `/opt/data/profiles/<name>/memories/MEMORY.md` and `USER.md`

**build_context_files_prompt()** — loads .hermes.md / AGENTS.md / CLAUDE.md / .cursorrules:
- Uses TERMINAL_CWD env var if set, falls back to `os.getcwd()`
- **Gateway (Telegram) mode:** TERMINAL_CWD = user home dir (e.g. `/opt/data/home`), walks up to git root → finds `/opt/data/.hermes.md`
- **CLI mode:** TERMINAL_CWD unset, falls back to `os.getcwd()` (e.g. `/opt/hermes`), walk may not reach .hermes.md
- **Implication — .hermes.md loads for ALL profiles:** The gateway sets TERMINAL_CWD once at startup. Named profiles (spawned via kanban dispatcher) and cron jobs inherit this env var from the gateway process. Every session that routes through the gateway finds `.hermes.md` at the git root — including worker profiles and cron agents. Only local CLI sessions launched outside the gateway (no TERMINAL_CWD) are exempt.
- Priority: .hermes.md > AGENTS.md > CLAUDE.md > .cursorrules (first match wins, only one loaded per session)

### 3. Hash Analysis

Check for identical content across profiles:

```python
import hashlib, os

profiles_dir = "/opt/data/profiles"
profiles = [d for d in os.listdir(profiles_dir) if os.path.isdir(os.path.join(profiles_dir, d)) and d != "_shared"]

for filename in ["USER.md", "MEMORY.md"]:
    hashes = {}
    for p in profiles:
        path = os.path.join(profiles_dir, p, "memories", filename)
        if os.path.exists(path):
            with open(path) as f:
                h = hashlib.md5(f.read().encode()).hexdigest()
            hashes.setdefault(h, []).append(p)

    print(f"{filename}: {len(hashes)} unique variants")
    for h, ps in sorted(hashes.items(), key=lambda x: -len(x[1])):
        print(f"  [{h[:8]}] {' '.join(ps)}")
```

## Analysis Phase

### 4. Cross-Reference Matrix

For each concept, check how many files mention it and whether they agree or contradict:

1. **Read all files** into a dict keyed by filename
2. **Search for key phrases** across all files: kanban, frustration, draft, qmd, send/approval, storage, security
3. **Flag contradictions** — same concept, different instructions (e.g. "no explanation" vs "first response must be verbal explanation")
4. **Flag duplicates** — same concept, different wording, same intent (e.g. "Draft it" in both SOUL.md and USER.md)
5. **Flag stale facts** — dates in the past, expired deadlines, references to things that no longer exist

### 5. Consolidation Strategies

**A. Move canonical rule to SOUL.md (identity — fires every turn):**
Best for behavioral responses: how to handle frustration, draft/proceed protocol, communication rules. These are about how the agent responds to the principal.

**B. Move canonical rule to SOUL.md (universal — applies to every profile):**
Best for universal constraints: security, no external send, bounded autonomy. Apply to every agent regardless of persona.

**C. Move canonical rule to .hermes.md (context — conditional on cwd):**
Best for project-level instructions: storage routing, install rules, memory access patterns. Only loaded when the cwd is under the git root.

**D. Keep unique content in MEMORY.md (frozen — fires every turn):**
Best for behavioral re-anchor rules that must fire every turn but are not identity-level. Includes: MCP-QMD first instinct, INFORMATION = NOT ACTION, food photo protocol.

**E. Keep behavioral directives in USER.md (frozen — fires every turn):**
Best for stable user preferences that don't change: communication style, thinking style, problem-solving approach. NOT for durable facts (address, property details, deadlines) — those go in QMD-indexed files.

**F. Cross-profile deduplication via symlinks:**
When all named profiles have identical USER.md or MEMORY.md content, consolidate to a single file:
1. Create `/opt/data/profiles/_shared/<filename>` with the shared content
2. `rm` each profile's local copy
3. `ln -s ../../_shared/<filename>` each profile's memories/ directory
4. Keep ca-expert's MEMORY.md independent if it has unique entries

### 5b. Oversized SOUL.md Check

Named profile SOUL.md files tend to accumulate generic Joy identity content that's already in the default `/opt/data/SOUL.md`. Flag any profile SOUL.md that's >3x the size of other profiles' SOULs (~1,400 chars). Common balloon content:

- **Life Flow Philosophy / Goals** — generic agent-purpose language, belongs in default SOUL.md
- **Tool Discipline / Pause Before Every Call** — universal agent behavior, belongs in SOUL.md or MEMORY.md
- **Full DB schemas embedded in markdown** — belongs in the referenced skill, not SOUL.md
- **Python code blocks for procedural steps** — belongs in the skill's scripts/ or references/

**Trim target:** ~30-35 lines, matching other named profiles. Keep only: identity, domain, core principles, memory scope, key facts, triggers, memory tree.

### 5c. DESCRIPTION.md Coverage Audit

The skills index prompt shows each category's description when a `DESCRIPTION.md` file exists in the category directory. Categories without descriptions just show the bare name, making it harder to route to the right skill:

```bash
# Check coverage
for d in /opt/data/skills/*/; do
  name=$(basename "$d")
  if [ -f "$d/DESCRIPTION.md" ]; then echo "  HAS: $name"
  else echo "  MISSING: $name ($(find "$d" -name 'SKILL.md' | wc -l) skills)"
  fi
done
```

Create missing ones with `write_file` following the existing format:
```yaml
---
description: Clear one-liner explaining the category's domain and the class of skills it contains.
---
```

Prioritize categories with ambiguous names (dogfood, red-teaming, architecture) over self-explanatory ones (travel, health). A good description helps the LLM route tasks accurately without loading the wrong skill.

### 6. Stripping Durable Facts from USER.md

USER.md's purpose per memory_tool.py: "compact behavioral directives that do not change session to session."

Facts that DON'T belong in USER.md:
- Property addresses, title numbers, lease terms
- Agent names, fee deadlines, purchase prices
- Any data that already exists in QMD-indexed files (property-sale.md, life-goals.md, etc.)

Move these to:
- `contacts/pallav-vasa.md` for personal identity facts
- `life/property-sale.md` for property transaction facts
- Kanban task body for active workstream facts

### 7. Verifying .hermes.md Loading

After changes, verify whether .hermes.md is actually injected:

```python
from pathlib import Path

def trace_hermes_md_loading(cwd_str, label):
    cwd = Path(cwd_str).resolve()
    stop_at = None
    for parent in [cwd, *cwd.parents]:
        if (parent / ".git").exists():
            stop_at = parent
            break
    for directory in [cwd, *cwd.parents]:
        if (directory / ".hermes.md").is_file():
            return f"{label}: LOADED from {directory / '.hermes.md'}"
        if stop_at and directory == stop_at:
            break
    return f"{label}: NOT LOADED (walked from {cwd})"

print(trace_hermes_md_loading("/opt/data/home", "Gateway (TERMINAL_CWD)"))
print(trace_hermes_md_loading("/opt/hermes", "CLI (os.getcwd())"))
```

## Pitfalls

- Don't assume duplicates are harmful. Some repetition across files is intentional (Tier 1 reinforcement). Only flag duplicates when they contradict each other or waste significant tokens without adding reinforcement value.
- Don't delete from SOUL.md what's also in USER.md. Consolidate to one source, then remove from the other.
- SOUL.md is off-limits for direct edits per the MEMORY.md guard. Flag candidates only — the user must approve SOUL.md changes explicitly.
- The memory tool's drift detection checks file content round-trip. A symlink is fine for stable files (USER.md, MEMORY.md) that rarely change. If a profile tries to write to a symlinked file, the write goes to the shared target.
- Expired deadlines in USER.md: Always check dates against today before flagging as stale. A fee deadline that has passed is silently misleading — every session re-reads it as current.
- **Context-to-identity migration:** When a rule exists in `.hermes.md` (project context, conditional load) AND MEMORY.md (frozen, always loaded), ask *"Is this about how the agent responds to the principal?"* If yes, the canonical home is SOUL.md (identity). Example from June 2026: the Walk-Back Rule (`.hermes.md`) and Frustration/fix reflex (MEMORY.md) were the same concept — "how to react when the user questions a past action" — consolidated into a single `## Feedback Response` section in SOUL.md.
