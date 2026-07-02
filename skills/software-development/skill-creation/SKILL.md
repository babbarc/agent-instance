---
name: skill-creation
description: Create, review, or audit a Hermes skill. Use when creating a new skill, evaluating an existing one for compliance, or planning edits.
annotation: "Create/review/audit skills: SKILL.md rules, gates"
version: 1.8.0
---

# Creating & Reviewing Skills

Three parts. Use **Part 1** first (should this be a skill?). Use **Part 2** when creating. Use **Part 3** when auditing or preparing edits to an existing skill.

---

## Part 1 — Review Gate

Skip skill creation if ANY of these are true:

- The content is a one-off task narrative (summarise today's market, analyse a single PR)
- The content is an environment-dependent failure (missing binary, fresh install error)
- The lesson is a retry pattern that resolved without structural change
- The content is session-specific transient errors that resolved during the conversation
- The content makes negative claims about tools ("tool X does not work")
- The only fitting name describes today's specific task — update an existing skill instead
- **An existing skill already covers this territory** — search existing skills by keyword before creating. If the description overlaps, extend the existing skill instead.

**If none apply**, proceed to Part 2.

### Disable vs Delete Gate

When the user asks to remove, disable, or delete a skill:

1. **Check for native disable:** Before deleting, look for Hermes' disable mechanisms — `hermes skills config` (interactive, per-platform toggle) or any `disabled_skills` list in `config.yaml`.
2. **Safe preserve path:** If no native mechanism exists, move the skill to `skills-archive/<category>/` instead of deleting. The skill stays intact on disk but Hermes won't load it.
3. **Only delete on explicit confirmation:** Do not delete unless the user explicitly confirms "yes, delete it" or equivalent. "Disable" and "remove" are ambiguous — clarify before acting.

---

## Part 2 — Create the Skill

Follow these steps in order.

### 2.1 Name It

- Format: `verb+noun`, lowercase, hyphen-separated (e.g. `book-restaurant`, `review-pr`)
- **Exception:** umbrella/category skills that collect related procedures may use noun phrases (e.g. `skill-creation`)
- The name must describe a class of tasks, not a single session's work (see Part 1 for examples of what to exclude)

### 2.2 Write Frontmatter

```
---
name: <verb-noun>
description: <WHEN to load and WHAT it does — e.g. "Load when scheduling a cron task.">
version: 1.0.0
---
```

- `description` must include the **trigger condition** so searching LLMs know when to load this skill
- Do NOT set `author` — provenance is tracked separately
- `annotation` — optional, ≤60 chars, LLM-optimised one-liner for the skills index. See Section 2.8
- Do NOT set non-standard frontmatter fields (`license`, `platforms`) — only `name`, `description`, `version`, `annotation`, and `metadata.hermes.*` are standard
- Start at `1.0.0`. Bump the minor version on any substantive update. Bump the major version on breaking structural changes.
- **Validate YAML**: the content between `---` delimiters must parse cleanly with `yaml.safe_load()`. Catch: unclosed quoted strings, `>-`/`|` block scalars with no indented content, stray markdown text inside the frontmatter block, and missing closing `---` delimiter. Test with: `echo "$FRONTMATTER" | python3 -c "import sys,yaml; yaml.safe_load(sys.stdin)"`.

### 2.3 Write the Body

**Numbered steps** for procedures (do A, then B, then C). **Bullets** for criteria lists or check items.

```
1. Do this first
2. Then do this
3. Decision: if X → do Y, else → do Z
```

Rules:
- Every step must map to one unambiguous action or decision
- If a step branches ("if X → Y, else → Z"), both branches must name concrete actions
- Warnings, troubleshooting, and edge cases go in `references/<topic>.md` — never inline
- **Numbered sections (`### N. Title`) in the body must be procedural steps.** Sections whose title describes a failure mode, warning, edge case, or pitfall (e.g. "Stuck Scheduler", "Missing enabled_toolsets") belong in `references/pitfalls.md` as one-line table entries — never as inline numbered sections in the body
- Design rationale, implementation diary, postmortems, and negative tool claims never appear in the body
- When a section references a supporting file, add one line of the exact format `See `references/<topic>.md` for <what it covers>.` after the relevant step.
- When the user expresses a preference about style, tone, format, or workflow, embed it as a numbered step or decision rule — not as a warning, caveat, or memory entry. Skills capture 'how to do this class of task for this user.'

### 2.4 Add References (Optional)

Support files for edge cases, API docs excerpts, and known failure modes:

- Create via `skill_manage(action='write_file', name='<skill>', file_path='references/<topic>.md', file_content='...')`
- Keep each reference under 20 lines unless the topic genuinely requires more
- `references/pitfalls.md` — condensed one-line warnings for failure modes that would block a future run

### 2.5 Add Templates or Scripts (Optional)

- `templates/<name>` — starter files to copy and modify
- `scripts/<name>` — re-runnable verification scripts and generators
- Reference each from the body with one line, e.g. `See `templates/config.yaml` for a starter config.`

### 2.6 Instantiate

- **New skill:** `skill_manage(action='create', name='<name>', content='<full-SKILL.md>', category='<category>')`
- **Existing skill update:** `skill_manage(action='edit', name='<name>', content='<full-updated-SKILL.md>')`
- **Small fix to existing:** `skill_manage(action='patch', name='<name>', old_string='...', new_string='...')`

The `content` parameter must include the full file — frontmatter `---` delimiters and all.

### 2.7 Verify

After creating or editing, confirm the file exists and is loadable:

1. Read the file back: `skill_view(name='<name>')`
2. Confirm frontmatter is present: the output starts with `---`
3. Verify the raw `description` is a meaningful string (not `">-"`, `"|"`, `">+"`, or other YAML syntax tokens)
4. Confirm the first sentence of `description` contains the trigger condition
5. Check that every `references/` or `templates/` path mentioned in the body actually exists under the skill's directory
6. If an `annotation` was set: verify `len(annotation) <= 60` — it must not truncate
7. **Validate YAML syntax**: extract the content between `---` markers and run `yaml.safe_load()`:
   ```sh
   sed -n '1,/^---/p' <skill-path>/SKILL.md | head -n -1 | tail -n +2 | python3 -c "import sys,yaml; yaml.safe_load(sys.stdin)"
   ```
   Must exit 0 with no errors — catches missing closing `---`, unclosed quotes, `>-`/`|` block scalars with no content, stray markdown inside frontmatter.

8. **Check for inline numbered pitfall sections**: Run `grep '^### [0-9]' <skill-path>/SKILL.md` and inspect each match. If any heading describes a warning, failure mode, edge case, or pitfall rather than a procedural step, move the section body to `references/pitfalls.md` and replace with a one-line pointer. Every `### N.` section in the body must be a procedural step.

If any check fails, fix and re-run 2.6.\n\n### 2.8 Add Annotation (Mandatory)\n\nThe `annotation` field replaces the full `description` in the `<available_skills>` index that the LLM scans at session start. Without one, the description is truncated to 57 chars. **Add one to every new skill** — omission is a high-impact defect (wastes discovery tokens every session until fixed).\n\n1. **Length**: ≤57 chars ideal, ≤60 max. Longer values are truncated with `...`.\n2. **Front-load the trigger word**: start with the action, use case, or category the LLM searches for.\n3. **Comma-separated keywords**, not prose sentences. Omit articles (a/an/the).\n4. **Prefer concrete nouns** over vague phrases — name the actual things the skill touches.\n5. **Format**: `annotation: \"<text>\"` in YAML frontmatter, quoted string.\n\nExamples:\n```\nannotation: \"Structural changes: cron, profiles, DB, memory — load first\"\nannotation: \"Create/review/audit skills: SKILL.md rules, gates\"\nannotation: \"Passwords/secrets/tokens: pass-to, CDP inject, never show\"\n```\n\nFull convention reference at `skill-creation/references/annotation-field.md`.

### 2.9 In-Repo Skills

User-local skills (`~/.hermes/skills/`) are created via `skill_manage(action='create')`. In-repo skills (committed with Hermes at `skills/<category>/<name>/SKILL.md`) require:

1. **Extra frontmatter fields** — add `license: MIT` and `metadata.hermes.tags` + `metadata.hermes.related_skills` to the standard frontmatter.
2. **Use `write_file` + `git add`** — `skill_manage` targets the user-local tree; in-repo skills need direct file writes followed by staged commits.
3. **Annotation field** — see `skill-creation/references/annotation-field.md` for the ≤57 char trigger-hint rules.

Procedure:
1. Write the SKILL.md: `write_file(path='skills/<category>/<name>/SKILL.md', content='<full-content>')`
2. Stage it: `git add skills/<category>/<name>/SKILL.md`
3. Commit with a descriptive message

---

## Part 3 — Audit an Existing Skill

Use when evaluating a skill for compliance with the rules in Part 2, or when preparing edits. Produces a ranked list of issues.

### Step 1: Load the rules

```
skill_view(name='skill-creation')
```

Every check below maps to a rule in Part 2.

### Step 2: Load the target skill

```
skill_view(name='<target-skill>')
```

Read the full SKILL.md content and note every `references/` and `templates/` path it mentions.

### Step 3: Run compliance checks

Check each field listed below. For each violation, note the rule from Part 2 that was broken:

1. **Name**: Is it verb+noun (or noun-phrase for umbrellas)? Does it describe a class, not a single session?
2. **Frontmatter**: Does it have `name`, `description` (with trigger condition), `version`, and `annotation`? Are non-standard fields like `license`, `platforms` absent? Is `annotation` ≤60 chars? **Is the YAML syntactically valid** — extract frontmatter content between `---` markers and `yaml.safe_load()` without error? Check the closing `---` delimiter is present (not just the opening one).
3. **Inline postmortems**: Search for phrases like "observed", "violation pattern from", "this session proved", "this is how", "past sessions" — these signal narrative history that belongs in `references/`.
4. **Inline edge cases and numbered pitfalls**: Search for troubleshooting, warnings, corner cases exceeding one line. Also search for `### \d+\.` patterns whose heading describes a failure mode (e.g. "Stuck Scheduler", "Missing enabled_toolsets", "Credential Leakage") — these belong in `references/pitfalls.md`, not the body as numbered sections.
5. **Broken references**: Check every `references/` or `templates/` path mentioned in the body actually exists as a linked file. Also check the reverse: every file in the `references/` directory must be listed in the body or reference table. Run: `for f in <skill-dir>/references/*.md; do grep -q "$(basename $f)" <skill-dir>/SKILL.md || echo "UNLISTED: $f"; done`
6. **Numbering**: Are section numbers sequential? No orphaned "2b" without "2a", no duplicate numbers?
7. **Redundant content**: Check for the same instruction appearing twice verbatim.
8. **Design rationale / implementation diary**: Any paragraph that explains *why* something was done rather than *how* to do it.
9. **Scope creep**: Does this skill overlap with another? Load at least 2 skills in the same or adjacent categories with similar descriptions. Compare body sections — if >50% of sections are identical (same structure, same principles, same verbatim text), the skills should be merged. Record the overlap direction.
10. **Cross-reference health**: Check that every skill name mentioned in `related_skills` still exists. If a referenced skill was absorbed into another, update the reference to point to the survivor. Also check the reverse: if the body references other skills by name (e.g. `see \`<skill-name>\``), verify those skills appear in `related_skills`. Missing related_skills hides companion skills from the LLM's discoverability scan.
11. **Absorbed skills**: If this skill was previously merged from another (`merged_from` in metadata), verify all stale references to the old name have been updated across all other skills. Search: `grep -rn '<old-name>' /opt/data/skills/ --include='SKILL.md'`.

### Step 4: Get second opinions

Before finalising any fix plan, run findings through at least two independent AI models:

1. Route the findings to one model, including the raw compliance check results and the rules from Part 2.
2. Route the same findings to a second model.
3. Note areas where reviewers agree (consensus) and disagree (variance). Include both when presenting to the user.

**Consensus items** are safe to fix without further debate. **Variance items** (e.g. "is broken numbering low or medium impact?") — present both opinions and let the user decide.

### Step 5: Rank issues by impact

Order from most damaging to least:

1. Critical: Missing version, broken reference paths, inline postmortems that pollute agent reasoning, inline numbered pitfall sections that should live in `references/pitfalls.md`, scope creep that duplicates effort
2. High: Redundant content wasting context tokens, missing trigger condition in description, non-standard frontmatter fields
3. Medium: Duplicate section numbers, broken numbering schemes
4. Low: Long body (not a spec violation, just efficiency)

### Step 6: Present findings — fix self-evident violations immediately

Output: skill name → issue list with severity rank → reviewer consensus/variance.

**Self-evident violations (fix immediately, no approval needed):**
- Inline postmortems, inline numbered pitfall sections (`### N.` failure-mode headings)
- Broken reference paths
- Missing version or annotation
- Non-standard frontmatter fields

For these, apply the fix alongside the findings. Include the diff in your output so the user sees what changed.

**Subjective or ambiguous changes (ask for approval):**
- Renaming, restructuring, merging skills
- Scope creep decisions
- Changes that affect cron jobs or other profiles

For these, present findings and wait for explicit go-ahead before executing.

### Step 7: Execute fixes in priority order

1. Apply patches for the highest-ranked issues first using `skill_manage(action='patch', ...)`. **If rebuilding a file via `execute_code`:** `hermes_tools.read_file` returns line-number-prefixed content — strip them before writing (see `references/tool-quirks.md` Q1).
2. Create any new `references/` files using `skill_manage(action='write_file', ...)`
3. Re-read the modified skill and run Step 2.7 verification
4. Commit and push after each logical batch of changes

---

## Preference Order (Modifying Existing Skills)

When asked to create a skill but relevant content already exists:

1. **Patch a skill already loaded this session** — if it covers the territory, use `action='patch'`
2. **Update the closest existing umbrella skill** — extend it rather than creating another
3. **Add a support file** to an existing umbrella that is close but missing edge-case detail
4. **Create a new skill** — only when nothing exists that covers the class of task

---

## Cross-Reference Maintenance

After renaming a skill or absorbing one into another:

- Search for stale references: `grep -rn <old-name> /opt/data/skills/ --include='SKILL.md' /opt/data/.hermes.md /opt/data/memory/`
- Check `related_skills` in ALL skills that referenced the old name — update to point to the survivor
- Verify the body text of every skill that mentioned the old name (grep for it in body, not just file paths)
- Verify any cron jobs referencing the old name still resolve
- Check the Pitfalls Index or any numbered index tables in related skills for stale references
- Run `skill_manage(action='delete', name='<old-name>', absorbed_into='<survivor>')` for absorbed skills
- Re-scan: run the search again after all changes to confirm zero stale refs remain
