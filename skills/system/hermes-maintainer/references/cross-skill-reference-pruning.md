# Cross-Skill Reference Pruning

Systematic workflow for pruning references to a deprecated tool, path, or approach across the entire skill library. When the user says "check for references and prune them carefully," follow this protocol.

## Trigger Conditions

- User says "prune references" / "remove references to X" / "delete all mentions of Y"
- A tool, binary, or integration path is confirmed dead and all instructions to use it must be removed
- An approach is superseded and old instructions must be swept from every skill

## Pre-flight

1. **Clarify scope** — Ask the user what exactly to prune. Get the canonical name (exact binary name, path, skill name, or pattern). Confirm whether the deprecated thing's own skill should stay (e.g. the guide-claude-code skill for coding is fine, but references to using it for vision must go).

2. **Identify the pattern** — Decide on search terms. Cover: exact binary name (`claude`), hyphenated (`claude-code`), compound phrases (`Claude Code`), inline commands (`claude -p`), and unique flags (`--allowedTools "Read"`).

## Phase 1 — Broad Search

Search across ALL skills and references. Use multiple search patterns — don't settle on one.

```python
# Example pattern set — adapt to your target
for pattern in [
    "claude.*(image|screenshot|photo|vision|visual|look|see)",
    "(image|screenshot|photo).*claude",
    "claude -p.*--allowedTools|--allowedTools.*claude",
    "claude.*Read.*-p",
]:
    search_files(pattern=pattern, path="/opt/data/skills")
```

**Check these locations:**
- `/opt/data/skills/` — main skill tree
- Memory entries in `memory` tool output
- `$HERMES_HOME/memory/` tree (user profile files)

## Phase 2 — Triage Each Hit

For each match, classify:

| Type | What it looks like | Action |
|------|--------------------|--------|
| **Standalone reference file** | A file whose only purpose is documenting the deprecated tool/path for vision (e.g. `references/image-analysis-via-claude.md`) | Delete entirely via `skill_manage(action='remove_file')` |
| **Section in a skill body** | A subsection titled "Claude Code CLI fallback" or similar, with explicit instructions to use the deprecated path | Remove the section. Renumber surrounding sections. |
| **Pitfall mentioning the deprecated path** | `- **Claude CLI may be rate-limited** — ...` | Rewrite to reference the alternative approach or remove entirely |
| **Cross-reference** | `See x skill` or `ref: y skill for vision patterns` | Remove the cross-ref line |
| **Inline command example** | Code block showing `claude -p "analyze..."` | Replace with equivalent using the replacement approach (e.g. `vision_analyze`) |
| **Reference list entry** | `references/claude-prompts.md` listed in ## Reference Files section | Remove from the list |

## Phase 3 — Execute

**Order:** Delete standalone files first, then patch skill bodies, then fix references.

**For deletion:**
```bash
skill_manage(action='remove_file', name='<skill>', file_path='references/<file>.md')
```

**For patching skill bodies:**
- Read the affected lines with context around each match before writing the patch
- Use targeted `patch()` with enough surrounding lines for uniqueness
- One logical change per patch — don't batch block-replaces
- After deletion, renumber sections if needed (D → C, E → D, etc.)

**For reference files:**
- Check `references/` directories separately — they're easy to miss in a body-content search
- Look for both the deprecated name AND the replacement strategy in the same file

## Phase 4 — Verify

**First sweep:** Rerun the original search patterns. Expect zero matches.

**Second sweep:** Use DIFFERENT search angles — broader patterns, alternative phrasings, partial matches:

```python
for pattern in [
    # Broader — catch edge cases
    "claude.*(analy|look|read|see|check|examine)",
    "(Read|analy|look).*claude",
    # The flags unique to the deprecated usage
    "allowedTools",
    # Alternative references to the same thing
    "vision.*fallback|fallback.*vision",
]:
    search_files(pattern=pattern, path="/opt/data/skills")
```

**Third pass — visual scan** (optional for small searches): skim the changed files to confirm edits look clean.

## Phase 5 — Report

Deliver a terse summary organized by action type:

```
Deleted files (N):
- skill-a/references/x.md
- skill-b/references/y.md

Patched skills (N):
- skill-a — removed Section B, cross-refs, 3 pitfalls
- skill-b — collapsed redundant content, removed 5 clauses
```

## Phase 6 — Commit

Always finalize a pruning session by committing and pushing. The user expects the cleanup to be persisted.

**Individual commits per skill area** — never one catch-all commit. Each skill change is self-contained and should tell its own story:

1. Group changed files by skill area (guide-claude-code, health, recaptcha-solver, etc.)
2. Stage and commit each group separately
3. Commit message pattern: `prune: remove <deprecated thing> from <skill name>`
4. Push when all commits are clean

```bash
git add skills/<skill-area>/ && git commit -m "prune: remove <deprecated thing> from <skill-name>"
# repeat for each skill area touched
git push
```

**Why individual commits:** granular rollback (revert one skill without losing others), precise commit messages, and the user can see exactly which skills were touched. Cross-cutting cleanup across N skills should produce N commits, not 1.

## Pitfalls

- **Do NOT add memory entries about the pruning** — the cleanup IS the fix. Adding a behavioral anchor ("Claude Code CLI is NOT to be used for vision") creates a persistent constraint that will fire every turn even after all references are gone. The user asked for cleanup, not a permanent new rule. Just do the work and verify.
- **Don't assume you caught everything on the first pass.** Use at least two search passes with different pattern angles. The second pass always finds something the first missed.
- **Check reference lists in SKILL.md footers separately.** `## Reference Files` sections are ordinary markdown body text — search tools find them, but it's easy to miss an entry that names a deleted file. Re-read the reference list after deleting files.
- **One logical change per patch.** Editing three adjacent bullet points? One patch. Editing three sections across the file? Three separate patches. The patch tool gets confused on large multi-section replacements.
- **Read surrounding context before patching.** The line you want to change may be part of a numbered list, a code block, or a section that needs renumbering after the edit. Understand the structure before you modify it.
- **The deprecated thing's own skill may still be legitimate** for its primary purpose. Don't delete `guide-claude-code/SKILL.md` because it describes how to use Claude Code for coding — only remove the vision-analysis parts.
- **Untracked (`??`) directories can hide hits.** `search_files` finds files on disk regardless of git tracking, but a directory that was added by a previous session and never committed may contain references to the deprecated thing. After deleting/changing such files, they need `git add` to be committed. Run `git status --short` alongside `search_files` to spot untracked directories that also need pruning.
