# Diagnosis

## Dry-run fails
`patch --dry-run` → "Hunk #N FAILED" or "Only garbage found":
- "garbage" = patch format corrupted (leading `|` on lines). Regenerate via `diff -u`.
- "FAILED" = context lines don't match target. Check: was patch built from `.original` or from a patched file? Regenerate against correct base.

Check if the installed file differs from `.original`:
`diff ~/.hermes/patches/<file>.py.original /opt/hermes/<path>/<file>.py`

## Silent hunk drop (cumulative patches)

Dry-run passes but a change is missing after restart. Two distinct causes:

**Cause 1: Diff taken from already-patched file.** The diff was generated against the installed file (which already had old patches applied). A hunk that was already present shows "no diff" and gets silently omitted from the new combined patch. At next boot, the combined patch applies to clean upstream — the "no diff" hunk is never applied. See `cumulative-patch-rebuild.md`.

**Cause 2: Combined patch built from an already-simplified intermediate commit.** A previous regeneration commit replaced the old multi-hunk patch with a smaller patch, and a subsequent "combine against original upstream" commit was built from that smaller version without restoring the dropped hunks. Dry-run passes (the patch is valid for the hunks it has) but the patch is incomplete.

### Diagnosing Cause 2 — git-based hunk count cross-reference

When a patch was committed and then further modified, check whether hunks were lost across commits:

```bash
cd /opt/data
# List all commits that touched this patch file
git log --oneline -- home/.hermes/patches/<file>.py.patch

# For each commit, count hunks
for commit in $(git log --oneline -- home/.hermes/patches/<file>.py.patch | awk '{print $1}'); do
  count=$(git show $commit:home/.hermes/patches/<file>.py.patch 2>/dev/null | grep -c '^@@')
  echo "$commit: $count hunks"
done
```

If the hunk count drops between two commits without a corresponding increase in another patch file, changes were silently lost and must be restored.

### Cross-referencing lost sections across patch files

Hunks that were dropped from one patch may have moved to another. Check:

```bash
cd /opt/data
for f in home/.hermes/patches/*.patch; do
  git show HEAD:"$f" 2>/dev/null | grep -q 'MEMORY_GUIDANCE\|WORKFLOW_GUIDANCE\|<act_dont_ask>\|<resolve_ambiguity>' && echo "FOUND in $f"
done
```

(Replace the grep pattern with the constant or XML tag that was dropped.)

If no hit in any patch file, the change is genuinely lost and must be re-added to the correct patch. Reconstruct the desired content from the old commit:

```bash
# View the lost hunk
git show <old_commit>:home/.hermes/patches/<file>.py.patch | grep -A40 'MEMORY_GUIDANCE ='
```

Then regenerate the patch via the Standard Workflow (section 2b) with the content restored.

## Git rescue — restore patches from version control

When patches are known wrong and the user says "restore from git":

1. Find the repo: patches live in `/opt/data/` git repo (tracked under `home/.hermes/patches/`). Check with `cd /opt/data && git log --oneline -- home/.hermes/patches/`.
2. Restore: `git checkout HEAD -- home/.hermes/patches/<file>.patch` for specific files, or `git checkout HEAD -- home/.hermes/patches/` for all.
3. Test: `patch --dry-run -p0 -d /opt/hermes -f < ~/.hermes/patches/<f>.patch` — note that already-applied patches fail forward but pass reverse: `patch --dry-run -p0 -d /opt/hermes -R -f < <patch>`.
4. Diagnose any remaining failures via the sections below.
5. Regenerate with the Standard Workflow once the intended changes are understood.

Do NOT skip step 3 — a git-restored patch may still be wrong (committed in a bad state). Always verify.

## "malformed patch at line N" — hunk header count mismatch

`patch --dry-run` says "malformed patch at line N" followed by a code snippet from the file. The patch is syntactically valid (lines start with +, -, space) but the hunk header counts don't match the body.

**Detect:**

Run the validation script before the dry-run:
```\npython3 scripts/validate-patch.py /tmp/fix.patch\n```
This prints the exact hunk, the header count, and the actual removed/added/context counts.

**The mismatch pattern:**
- old-side header = removed + context (lines that differ in the original file)
- new-side header = added + context (lines in the result)
- If either sum ≠ header, `patch` rejects it as "malformed"

**Root causes:**
1. Patch was hand-edited (copy-pasted, AI-generated) after `diff -u` output — never do this. Always regenerate via `diff -u`.
2. `diff -u` was run against the WRONG file — e.g. against an already-patched installed file instead of the clean `.original`. The context lines match but the body drifts from the intended base.
3. sed substitution on the path line accidentally matched hunk body content — check with `grep` before `sed`.

**Fix:** Regenerate the patch from scratch via Standard Workflow. Do NOT hand-fix the header numbers — they're derived from the actual lines. If you're recovering existing content, see `cumulative-patch-rebuild.md`.

## Stale references (import chain breakage)
After patching a file, check consumers can still import:
`python3 -c "from agent.prompt_builder import <symbol>; print('OK')"`

Run AST stale-reference scan on the patched file (catches symbols in function bodies that imports alone miss):
```
python3 -c "
import ast
names = {n.id for n in ast.walk(ast.parse(open('/tmp/work.py').read())) if isinstance(n, ast.Name) and n.id[0].isupper()}
for sym in ['REMOVED_SYMBOL']: print(f'{sym}: {\"STALE\" if sym in names else \"clean\"}')"
```
