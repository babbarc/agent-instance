# Skill Design Principles

> When creating, updating, or merging a skill, run the skill gate in .hermes.md first. These principles expand on that foundation.

## Principles

### 1. Generic Procedural Steps
A skill is a repeatable procedure, not a reference doc or a data dump. It tells the LLM *how* to do something. The *what* (specific facts: names, dates, account numbers, discovered balances) belongs in profile memory trees indexed by QMD.

**Test:** If you remove every personal fact from the skill, does it still contain complete steps? If no, the facts belong in a profile memory file.

### 2. Skills Own Their Own Data

Every service-specific credential path, config reference, or integration detail lives in that service's skill — never in a shared/cross-cutting skill.

**Why:** A shared table means every new service needs an update to a file that shouldn't change. It duplicates the source of truth. If a credential path changes, you have to find and update it in multiple places.

**Exception:** Truly cross-cutting tools (like `pass` itself) — the protocol for *how* to use them safely belongs in the security skill. The *specific paths* for each service belong in their own skills.

### 3. Clean, Simple, Straightforward
No friction for the LLM reading it. Tight sections. Clear headings. Exact commands the agent can copy-paste. No essays, no multi-paragraph explanations of why something works.

**Test:** Read the skill aloud. Every sentence earns its place. If a paragraph makes you think "this could be 1 line", distill it.

### 4. Distilled Aggressively
- No session-specific commentary ("Real scenario 31 May 2026:...") — that's a changelog, not a procedure
- No edge-case essays — condense to a one-line warning
- No "Update these figures when filing starts" — that's a note-to-self, not a step
- No personal data (Chase £3,300, IBKR £1,073.41, "User is UK resident")

**Test:** Can you delete 30% of the content without losing a procedural step? If yes, do it.

### 5. Deterministic Output
The LLM following the procedure should produce the same quality of output every time. This means:
- Fixed phases/steps (not "consider doing X")
- Exact commands and SQL queries where applicable
- Tables for reference data (tax rates, deadlines, form numbers)
- Checklists for verification

**Test:** Load the skill and follow the steps blind. Do you get a usable output without backtracking or guessing?

### 6. One Concern Per Skill

A skill should do one thing well. If a skill has "and also" sections that don't relate to its core concern, split them out.

### 7. Skills Document Their Dependencies

Each skill should explicitly note:
- Required Python packages (and install method)
- Pass entries it reads/writes
- Other skills it depends on
- System tools it needs

### 8. No Duplication — Check Before Creating

Before creating a new skill, search existing skills via `skills_list()` and check: does a skill for this class of work already exist? If yes:
- **Merge** your new content into the existing skill (patch or edit)
- Don't create a parallel skill with a different name for the same workflow

This rule exists because sprawling flat skill lists create discovery friction (too many choices), maintenance cost (updating the same workflow in N places), and a false sense of completeness (a skill that exists but isn't the canonical one is noise).

## Merge Protocol

When merging Skill A into Skill B:

1. **Identify what's personal/factual** in both skills — names, dates, account numbers, discovered balances, session-specific numbers
2. **Move facts to the appropriate profile memory tree** (`/opt/data/profiles/<profile>/memory/`) — indexed by QMD as that profile's collection
3. **Keep only generic procedure** in the merged skill — steps, formulas, exact commands, tables
4. **Delete Skill A** with `absorbed_into="Skill-B"`
5. **Verify** the merged skill passes all principle tests

**Concrete example (2026-06-04):** Merging `tax-return-prep` into `uk-self-assessment`:
- First attempt created a 19.9KB file with personal facts (Chase, IBKR, Kraken credentials)
- Corrected version: 11.4KB — pure procedure. 8.5KB of facts moved to `/opt/data/profiles/ca-expert/memory/accounts/ibkr.md`, `accounts/kraken.md`, `tax/2025-26-notes.md`
- Result: skill is generic, memory is queryable, both are focused

## Trigger Signals for Skill Updates

Any of these warrants an update — do not default to "nothing to save":

- User corrected style, tone, format, legibility, or workflow approach → update the relevant skill to embed the preference
- User corrected a sequence of steps → update the procedure, condense edge cases to one-line warnings
- A genuine fix or workaround that would block a future run → capture it as a concise procedural step
- A skill has broken commands, stale paths, or factual errors → patch it
- Preference order: currently-loaded skill first → existing umbrella → support file under umbrella → new umbrella

## Anti-Patterns

| Anti-Pattern | Symptom | Fix |
|---|---|---|
| **Skill as data dump** | Skill contains personal facts (Chase £3,300, IBKR £1,073) | Move to profile memory, keep procedure only |
| **Skill as changelog** | "Real scenario 31 May 2026: the heartbeat's pre-run script..." | Strip to the one-line rule. Archive scenario in `references/` |
| **Skill as essay** | Multi-paragraph explanation of a simple edge case | Condense to one-line warning |
| **Skill as personal profile** | "User is UK tax resident, employed at..." | Replace with "Subject is UK tax resident" or omit entirely |
| **Skill as note-to-self** | "Update these figures when actual filing starts" | Delete. This is not a procedural step |
| **Skill as example output with real data** | Report template showing user's actual May 2026 spending (£8,500 income, £3,242.69 spend), subscription list with user's real providers (Netflix £14.99, PureGym £15.00), DEFAULT_BUDGET with real budget targets | Use clearly fictional example data — round numbers, generic merchant names, placeholder dates. Real data belongs in `$HERMES_HOME/memory/`. Example output blocks are templates, not data snapshots |
| **Skill as completion ritual / implementation diary** | Writing a 98-line reference doc with design rationale and implementation narrative for a code change that's already committed — the work IS the deliverable | Before creating a skill or reference, ask: "Will anyone load this to execute a procedure?" If the answer is no (because the code change is done and there's nothing left to proceduralise), do nothing. A code change is not skill material |
|