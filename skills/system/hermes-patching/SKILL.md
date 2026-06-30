---
name: hermes-patching
description: "Apply, validate, and upgrade Hermes source patches via the s6 overlay. Load before modifying patches at ~/.hermes/patches/, upgrading Hermes, or auditing patch health."
annotation: "Patch Hermes source: s6 overlay, dry-run, verify"
version: 1.0.0
metadata:
  hermes:
    related_skills: [system-architect]
---

# Hermes Patching — s6 Overlay Patch Workflow

**Load before:** investigating or modifying Hermes source patches under `~/.hermes/patches/`, upgrading Hermes and validating patches against new upstream, or auditing patch health.

For system-prompt-specific patches (behavioural directives in `prompt_builder.py` constants), see `system-architect/references/system-prompt-patch-workflow.md` — this skill covers the general patching mechanism.

---

## Pre-flight: Check Existing Patches First

Before investigating a suspected issue in Hermes source code:

1. Check `ls ~/.hermes/patches/<file>.py.patch` — if a patch exists, read it before making claims about the code.
2. The installed file may be the **patched** version; the `.original` backup shows upstream state.
3. A patch applied to disk but not yet picked up (Python module caching) can make the live system appear different from the file on disk — verify both.

See `references/pitfalls.md` for the most common patch-state misreading.

---

## Apply or Update a Patch: Copy → Patch → Verify → Diff → Validate → Dry-run → Forward-verify → Save → Verify saved

1. **Copy** — `cp /opt/hermes/<path>/<file>.py /opt/data/work_patch.py` (not `/tmp/` — the `patch` tool's write guard blocks `offset/limit`-read files there).

2. **Patch** — `patch(path='/opt/data/work_patch.py', old_string='...', new_string='...')`. Never Python string manipulation, heredocs, or raw strings — `\\b` (0x5C 0x62) corrupts via any other method.

3. **Verify syntax** — `python3 -c "c=open('/opt/data/work_patch.py','rb').read(); assert b'\x08' not in c"` then `python3 -c "import ast; ast.parse(open('/opt/data/work_patch.py').read())"`.

4. **Diff against .original** — `diff -u ~/.hermes/patches/<file>.py.original /opt/data/work_patch.py > /opt/data/fix.patch`. Then `sed -i 's|/opt/data/work_patch.py|<path>/<file>.py|' /opt/data/fix.patch`. Always diff against `.original`, not the installed file — that creates a patch that breaks on clean boot.

5. **Validate hunk headers** — `python3 scripts/validate-patch.py /opt/data/fix.patch` (must print "All hunks valid."). Catches header/body count mismatches.

6. **Dry-run** — `patch --dry-run -p0 -d /opt/hermes < /opt/data/fix.patch`. Must exit 0. No "FAILED", "offset", or "fuzz".

7. **Forward-apply syntax verify** — dry-run checks context matching but NOT syntax validity:
   ```
   mkdir -p /tmp/verify-patch/agent
   cp ~/.hermes/patches/<file>.py.original /tmp/verify-patch/<path>/
   patch -p0 -d /tmp/verify-patch < /opt/data/fix.patch
   python3 -c "import ast; ast.parse(open('/tmp/verify-patch/<path>/<file>.py').read())"
   rm -rf /tmp/verify-patch
   ```

8. **Save** — `cp /opt/data/fix.patch ~/.hermes/patches/<file>.py.patch`. Takes effect on next container restart.

9. **Verify saved patch** — `grep "unique-text-from-your-change" ~/.hermes/patches/<file>.py.patch`. If the text doesn't appear, the diff was generated from a stale working copy — the patch file saved the old version, not your edits. Fix: restart from step 1 with a clean copy.

10. **Cross-reference hunk count against previous version** — Count hunks in the NEW patch: `grep -c '^@@' ~/.hermes/patches/<file>.py.patch`. Compare against the previous version from git: `git show HEAD:home/.hermes/patches/<file>.py.patch | grep -c '^@@'`. If the count DROPPED, hunks were silently lost: the regeneration combined fewer changes than the old patch contained.

    **When the hunk count drops, run this cross-reference to identify which sections were lost:**
    ```bash
    echo "=== OLD patch hunks ==="
    git show HEAD:home/.hermes/patches/<file>.py.patch | grep '^@@'
    echo "=== NEW patch hunks ==="
    grep '^@@' ~/.hermes/patches/<file>.py.patch
    echo "=== Sections in OLD but NOT in NEW ==="
    diff <(git show HEAD:home/.hermes/patches/<file>.py.patch | grep '^@@') <(grep '^@@' ~/.hermes/patches/<file>.py.patch) | grep '^<'
    ```

    If one section (e.g. MEMORY_GUIDANCE, WORKFLOW_GUIDANCE) appears in the old patch but not the new, that change must be re-added. A patch that passes dry-run with fewer hunks than the previous version is **incomplete**, not safe.

    **Also check if dropped changes moved to OTHER patch files:**
    ```bash
    # grep all patch files for the constant name of a dropped section
    for f in ~/.hermes/patches/*.patch; do
      grep -q 'MEMORY_GUIDANCE\|WORKFLOW_GUIDANCE\|<act_dont_ask>' "$f" && echo "FOUND in $(basename $f)"
    done
    ```

    If the change isn't found in any other patch, it's genuinely lost and must be restored.

---

## Version-Upgrade Validation

When upgrading Hermes, existing patches may fail against new upstream code. Validate **before** upgrading:

1. **Fetch upstream files** from the new release tag on GitHub.
2. **Set up dry-run tree** — copy upstream files to `/tmp/v<N>-dryrun/` matching the patch paths.
3. **Dry-run each patch** — iterate over `~/.hermes/patches/*.patch` against the upstream tree.
4. **Interpret results:**
   - PASS with offset only — context lines still match, line numbers shifted. Safe to keep.
   - PASS with fuzz 1+ — works but fragile. Regenerate when practical.
   - FAIL (1+ hunks) — code region rewritten upstream. ALL hunks in that file must be regenerated.
5. **Regenerate a failed patch:**
   1. Copy upstream file to working copy.
   2. Read the old patch to understand the *intent* of each hunk (not the exact text).
   3. For passing hunks — apply them directly with `patch -p0` (accept partial failure).
   4. For the failed hunk — apply the change manually using find-and-replace.
   5. Verify syntax: `python3 -c "import ast; ast.parse(open('/tmp/work.py').read())"`.
   6. Diff against the upstream file, fix header paths, save.
6. **.original lifecycle:** The init script recaptures `.original` from the new installed version on boot. Old `.patch` files (made against old `.original`) will NOT apply to the new `.original`. The new `.patch` must be made against the new upstream code.
7. **Semantic check:** After all patches regenerate cleanly, assess whether the upstream change made any patch obsolete or if new capabilities need acknowledging.

---

## Post-Apply Audit: Patch Quality & Contradiction Review

After creating, updating, or upgrading patches — or when auditing an existing set:

1. **Cross-layer contradiction check** — Compare each patch against every other layer it touches (tool schemas, guidance constants, other patches).
2. **Dead config scan** — Check `~/.hermes/config.yaml` for settings the patched code no longer reads. Flag to user — don't silently leave them.
3. **Dead code scan** — Check for constants or imports the patch renamed/removed but didn't fully delete.
4. **Unicode consistency check** — Scan for mixed literal-vs-escape-sequences. Pick one style per codebase. Escape sequences are safer — they survive patch rebase without byte normalization.
5. **Regex battery test** — For every new regex pattern, run a harness that verifies matches, rejects non-targets, uses `\b` boundaries, and doesn't false-positive.
6. **Determinism assessment** — Does this make LLM behaviour MORE predictable or LESS? If it adds ambiguous instructions or contradictory signals, rewrite.

See `references/patch-review-checklist.md` for the full checklist and example contradictions.

---

## Files Tracked

All live at `~/.hermes/patches/<file>.py.patch`:
- `agent/background_review.py`
- `agent/prompt_builder.py`
- `agent/skill_utils.py`
- `agent/system_prompt.py`
- `tools/approval.py`
- `tools/clarify_tool.py`
- `tools/memory_tool.py`
- `tools/skill_manager_tool.py`

---

## Adding a New File

1. `cp /opt/hermes/<path>/<file>.py ~/.hermes/patches/<file>.py.original`
2. Create patch via steps 1–9 above.
3. Register in `99-hermes-patches.sh` — add `<file>` to the `for f in` loop and a `cp` backup line.
4. Add to the Files tracked list above.

---

## Revert

`cp ~/.hermes/patches/<file>.py.original /opt/hermes/<path>/<file>.py`

---

## Reference Files

See `references/<topic>.md` for:

| File | Purpose |
|------|---------|
| `approval-regex-pitfalls.md` | `\b` corruption, CLI flag boundaries, the `\/` trap |
| `cumulative-patch-rebuild.md` | Preventing silent hunk drops during rebuilds |
| `diagnosis.md` | Patch failure diagnosis (hunk failures, import chain, AST stale-reference scan) |
| `init-script-mechanics.md` | Bind mount details for the s6 overlay |
| `patch-review-checklist.md` | Full post-apply checklist |
| `pitfalls.md` | Common patch-state misreading, bad assumptions about patched files |

**Script:**
- `scripts/validate-patch.py` — validate unified-diff hunk headers match body counts

For system-prompt-specific patching context (behavioural directives in prompt_builder.py constants), see `system-architect/references/system-prompt-patch-workflow.md`.
