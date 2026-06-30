<!-- REFERENCE: deletable if stale -->

# Identity Prompt Audit — Token Efficiency & Duplication Detection

Run this audit before editing prompt files. The audit finds what to cut BEFORE you decide what to change. Audit is separate from implementation — present findings and get approval before editing.

## The 4-File Prompt Model

The system prompt draws from **4 files** (the 5th — guards.md — was removed June 2026 for being redundant noise). All must be scanned:

| Slot | File | Purpose |
|------|------|---------|
| Identity | `SOUL.md` (root/profile) | Persona-specific identity — the core behavioral framework |
| Context | `.hermes.md` (git root) | Project-level behavioral rules — loaded via context file walk |
| Memory | `MEMORY.md` (memories/) | Tier 1 frozen behavioral guardrails — injected every turn |
| User | `USER.md` (memories/) | User-specific behavioral directives — injected every turn |

**.hermes.md is NOT always loaded.** It depends on `TERMINAL_CWD`:
- In **gateway mode** (Telegram): `TERMINAL_CWD` = user home (e.g. `/opt/data/home`) → walk up finds `.hermes.md` at git root → **loaded**
- In **CLI mode**: `TERMINAL_CWD` may be unset, falls back to `os.getcwd()` → if cwd is outside the git tree (e.g. `/opt/hermes` where there's no `.git`) → **not loaded**
- **Test before assuming:** `echo "TERMINAL_CWD=${TERMINAL_CWD:-<unset>}"` — if set, trace the git root walk from that path; if unset, trace from `pwd`

For **named profiles**, all 5 files are always loaded because `TERMINAL_CWD` is always set to a path under the git root.

## The Six Checks

### 1. Firing-Frequency Tagging
Read the file section by section. For each, ask: **"How often does this rule actually drive a decision?"**

| Tag | Meaning | Action |
|-----|---------|--------|
| **Every turn** | Loaded every turn, used 1+ times per conversation | Keep as-is |
| **Most turns** | Present every turn, used occasionally | Keep, but condense |
| **Fires rarely** | Present every turn, only matters in specific situations | Condense or move to a reference |
| **Never fires** | Present every turn, never drives a single decision | Delete or merge into a higher-level principle |

**Signal words for Never Fires:** "This is..." framing, aspirational descriptions, conceptual architecture explanation that doesn't end with a concrete instruction.

### 2. Cross-File Duplication Scan

Scan all 5 prompt files for rules that appear in more than one. For each duplicate:

1. Which copy is the **authoritative** one? (The file whose purpose matches the rule's type)
2. Delete the duplicates, leaving only pointers: `See SOUL.md > Execution Contract`
3. If no file is clearly canonical, pick the most specific one — the general file should reference the specific one

**Common duplication sources in this system:**

| Rule | Files | Overlap Type | Status |
|------|-------|-------------|--------|
| No external send without approval | .hermes.md, MEMORY.md | Double — .hermes.md has nuance, MEMORY.md has full guard | Unresolved |
| Draft it / Proceed | SOUL.md, USER.md | Double — USER.md more explicit about "Proceed = apply" and raw source output | Unresolved |
| Frustration / Walk-Back | MEMORY.md, USER.md, .hermes.md → **SOUL.md** | Triple + contradiction → consolidated into SOUL.md §Feedback Response | ✅ Resolved 4 Jun 2026 |
| Kanban-first / Kanban-crud | SOUL.md, MEMORY.md, USER.md | Triple — SOUL.md authoritative full section, MEMORY.md pre-SOUL.md condensed | Unresolved |
| MCP-QMD / memory access | MEMORY.md, .hermes.md | Double — 80% overlap, each adds a nuance the other lacks | Unresolved |
| Storage routing (/nebula/) | SOUL.md, .hermes.md | Double — .hermes.md authoritative, SOUL.md has condensed copy | Unresolved |

**The contradiction resolution rule:** When two files say opposite things about the same behavior (e.g. "no explanation" vs "explain first"), the higher-priority file wins: SOUL.md > .hermes.md > MEMORY.md > USER.md. SOUL.md is persona identity, .hermes.md is project context, MEMORY.md is frozen behavior, USER.md is user preference. (guards.md used to sit at the top of this chain — it was removed June 2026.) Once resolved, delete the duplicates and keep only the canonical entry.

### Duplicate Consolidation Procedure

When executing a consolidation from the table above:

1. **Draft the canonical rule** — write a single version that covers the full behavioral intent. Target: one clear rule that replaces N conflicting ones.
2. **Apply to the highest-priority file** — by the contradiction resolution rule (SOUL.md > .hermes.md > MEMORY.md > USER.md). Add the new section to that file.
3. **Remove from all other files** — for each duplicate: patch out the old section. Use exact match with surrounding context to ensure uniqueness.
4. **Update memory** — the memory tool may have a previously-saved version of the old rule. Replace it with the new consolidated reference so future sessions start clean.
5. **Update this table** — mark the row as ✅ Resolved with the date.
6. **Verify** — re-read all affected files to confirm no duplicate remains and no contradictions were introduced.

**Example — 4 Jun 2026:**
- Three copies (MEMORY.md entry 3 "Frustration/fix reflex", USER.md entry 2 "Two feedback modes", .hermes.md "Walk-Back Rule")
- Contradiction: MEMORY said "no explanation", .hermes said "explain first"
- Consolidated to SOUL.md as `## Feedback Response` with two modes (frustration signal vs calm signal)
- Removed from MEMORY.md (entry 3), USER.md (entry 2), .hermes.md (§Walk-Back Rule)
- Memory updated from old frustration reflex to new consolidated reference

### 3. Philosophy-to-Instruction Ratio
Estimate: what percentage of the section is **aspirational framing** vs **concrete instruction**?

- Philosophy: "You hold extraordinary access — this is not a toolset. It's trust." (Stewardship)
- Instruction: "Before any state-changing tool call: state intention + risk. Get approval."

**Target:** <20% philosophy, >80% instruction. Philosophy sections >3 lines should be condensed to 1 line or dropped. If the philosophy doesn't change what the agent does, it's dead weight.

### 4. Fossilized Corrections Scan
Look for rules that are a single past mistake preserved as permanent prose. Marker phrases:
- "Never do X" where X is extremely rare
- 3+ sentences about a one-off edge case
- A rule that includes a specific filename, tool name, or past incident detail in a way that wouldn't make sense without the backstory

**Test:** "If I removed this rule, how long before someone makes the mistake it prevents?" If the answer is "months" or "probably never," cut it to a single line.

### 5. Dependency Mapping
For each section, ask:
- Does this rule only matter when another specific rule is triggered?
- Is this redundant with a mechanism in the tooling? (tools already enforce it)
- Could this be a 1-line pointer to a skill reference instead of inline prose?

### 6. Behavioral-Preservation Verification — The Patch Gap

**⚠️ THIS IS THE MOST COMMON FAILURE MODE.** The 5 checks above will produce a tight compressed file. But compression creates gaps — behavioral rules whose downstream anchor was assumed but doesn't exist. You must verify before cutting.

**Method:**

After drafting the compressed version of each file, run a systematic trace:

1. **List every behavioral rule** from the original that was removed or compressed
2. **For each**, identify where its behavioral anchor is preserved in the new version:
   - A specific line in the new file? (name it)
   - A rule in another identity file?
   - A memory entry?
   - Tool-level enforcement?
3. **If no anchor exists**, the rule is a genuine loss. Add it back — don't accept the gap.
4. **Present the trace** alongside the compression proposal. Assertions like "behavior is preserved" are less convincing than a table mapping each lost rule to its survival location.

**Common preservation traps (things that look covered but aren't):**

| Original rule | Looks covered by... | But actually missing |
|---|---|---|
| User Sovereignty "no third pass" | Execution Contract "get explicit go-ahead" | Execution Contract covers BEFORE acting; "no third pass" covers AFTER a decision is made |
| Resilience "don't clam up, don't overcorrect" | Corrections preference "own it, learn it, move on" | Corrections covers user-facing response; Resilience covers internal recovery posture |
| Walk-back rule ("why did you" → explain, don't act) | Reflective Architecture "Is this explicitly asked for?" | Scope check covers general proactivity; walk-back is a specific trigger with a hard countermeasure |

### 7. .hermes.md Loading Verification

Before assuming .hermes.md is part of the prompt, verify it's actually being loaded:

```bash
echo "TERMINAL_CWD=${TERMINAL_CWD:-<unset>}"
```

- If **set**: the context file walk starts from that path. Trace from there to the git root:
  ```python
  from pathlib import Path
  cwd = Path("/actual/terminal/cwd")
  for p in [cwd, *cwd.parents]:
      if (p / ".hermes.md").exists(): print(f"FOUND: {p / '.hermes.md'}")
      if (p / ".git").exists(): break  # stop at git root
  ```
- If **unset**: falls back to `os.getcwd()`. If that's outside the git tree (no `.git` in parent chain), .hermes.md is **not loaded**.
- If .hermes.md exists but wasn't found by the walk, check: is it in a parent directory that the git-root stop condition reached first?

**Known asymmetry (as of June 2026):** Gateway (Telegram) sessions load .hermes.md via TERMINAL_CWD set to user home. CLI sessions from /opt/hermes do NOT load it (no git root up-chain, TERMINAL_CWD unset). This means prompt audits should verify the session type first, or simply check both loading paths.

### 8. Never-Mandate Anti-Pattern Detection

Scan for hard prohibitions that force a specific tool or method, even when a simpler direct path would work.

**Companion reference:** `identity-document-llm-readability.md` covers structural naming collisions, self-contradictory frames, ambiguous scope qualifiers, action-source tension, and other LLM-readability patterns not covered here. These create unnecessary indirection and turn the identity document into a routing table.

**Signal words:**
- "never do X, only do Y" — especially when Y is an indirect path (e.g. QMD search → get when read_file works for known paths)
- "always use Y for Z" — especially when Y is heavier than needed for the common case
- "only use X" — broad scope, no escape hatch

**The test:** If you already know the exact path or value, does the rule still force you through a search/discovery tool? If yes, the rule needs weakening.

**The fix pattern:**
| Before (bad) | After (good) |
|---|---|
| "Search via X (never Y)" | "Use X for search/location; Y for known paths" |
| "Only use X for Z" | "X is the preferred tool for Z; Y works when path is known" |
| "Always do X before Y" | "Do X before Y unless you already have the result" |

**Common instances found in practice (June 2026 SOUL.md audit):**
- `"never raw read_file/terminal"` on memory paths → forces QMD even when path is known
- `"never direct read_file/search_files on memory/ paths"` → same pattern, different section
- Both fixed to: `"Use mcp_qmd_query for search/location; read_file for known paths"`

**Edge case — hard prohibitions with legitimate reasons:** Some "never" rules are genuinely about safety (e.g., "never edit config.yaml directly"). Those should be retained — the distinction is whether the prohibition blocks an unsafe action (keep) or an equally-safe-but-less-fancy action (fix).

### Output Format

Present findings as:

```
### File: <path> — <N> lines → target: <M> lines
[Section name]: <N> lines, fires <frequency> — <keep|cull|condense|move>
  • Duplicate of <other file> — merge into <canonical>
  • Philosophy <N> lines of <M> — condense to 1 line
  • Fossil: <specific past mistake> — condense to single line
  
Estimated savings: <saved chars> = <saved%>
```

## Session Context

This methodology was developed on 31 May 2026 during a full audit of guards.md (217 lines), SOUL.md (137 lines), and .hermes.md (210 lines) — 564 total lines, ~34KB loaded every turn.

**Note on guards.md:** This file was subsequently removed entirely (June 2026). A June 2026 analysis confirmed guards.md was never actually injected into the system prompt — the architecture doc's claim of a patch-based composition was false. The remaining behavioral value (~2 lines: "no third pass", "cron doesn't self-debug") was not critical enough to retain. The file was deleted, and the patched architecture doc claim was corrected. See `$HERMES_HOME/memory/architecture/system-prompt-architecture.md` for the corrected assembly chain.

The first compression pass cut too aggressively — user corrected: "you must ensure it doesn't lead to behavioural change. instruction/information loss must be minimal." This prompted the development of Check 6 (Behavioral-Preservation Verification). The second pass traced every removed rule to its preservation anchor and found 5 genuine losses that were patched back in (walk-back rule, no-third-pass, don't-shut-down, unreachable-send-flag, numbered document categories).

**Key lesson: compression creates gaps. The audit tells you what to cut. The trace tells you what to keep. Both are mandatory.**

Final result: 564 lines → 101 lines, ~34KB → ~6.8KB per turn. Zero behavioral regression verified via systematic trace.
