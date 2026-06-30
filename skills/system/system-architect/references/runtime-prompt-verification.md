# Runtime Prompt Verification

## When to Use

A documentation file claims a file/feature is loaded in the system prompt. You need to know if it's *actually* loaded, not just *claimed* to be loaded.

**Example:** `system-prompt-architecture.md` said `guards.md` was composed via a patched `load_soul_md()`. Runtime proved it wasn't — the patch file never contained the composition logic.

## Three-Source Cross-Reference

Never trust a single source. Check all three:

| Source | What to check | Pitfall |
|--------|---------------|---------|
| **Documentation** | `system-prompt-architecture.md`, `prompt-assembly.md`, skill references | Docs describe what was *planned*, not what was *implemented*. Docs can be stale for months. |
| **Code/Patch** | Actual patch files (`~/.hermes/patches/`), source code (`/opt/hermes/agent/`), grep for filename | Patches can be partial — only certain hunks applied. Grep the patch DIFF, not just the patch file list. |
| **Runtime** | Call the actual function and inspect its output | The only source of truth. If code and runtime disagree, runtime wins. |

### Verification Procedure

```bash
# 1. Check doc claims
grep -n "guards\.md\|filename" /opt/data/memory/architecture/system-prompt-architecture.md

# 2. Check if patch actually contains the composition
grep "guards" ~/.hermes/patches/prompt_builder.py.patch
# If empty → composition was never patched

# 3. Check the source function
python3 -c "
from prompt_builder import load_soul_md
content = load_soul_md()
# Look for the claimed file's content signature
has_target = 'signature string from target file' in (content or '')
print(f'Contains target file: {has_target}')
print(f'Total chars: {len(content) if content else 0}')
"

# 4. Check diff between original and installed (no patch-based change)
diff ~/.hermes/patches/prompt_builder.py.original /opt/hermes/agent/prompt_builder.py | grep "load_soul\|filename"
```

### Exit Criteria

- **Doc says X, code confirms X, runtime returns X** → file is loaded, docs are current. No action needed.
- **Doc says X, code shows X attempted, runtime returns Y** → patch was partially applied or failed silently. Fix the doc to match runtime.
- **Doc says X, code shows no X, runtime returns Y (no X)** → the composition was never implemented. Fix the doc and delete the dead file.

## Post-Removal Stale-Ref Sweep

After deleting a file that was claimed to exist:

```bash
# 1. Find ALL references across the entire system
grep -rn "filename" /opt/data/ --include='*.md' --include='*.yaml' --include='*.yml' --include='*.py' --include='*.json'

# 2. Categorize matches:
#    - Factual claims: "load_soul_md() composes guards.md" → needs correction
#    - Design guidance: "Universal rules go in guards.md" → redirect to SOUL.md
#    - Historical context: "guards.md was removed in June 2026" → leave as-is
#    - Anti-pattern tables referencing old state → leave if they describe historical fixed state

# 3. For each factual/guidance match, determine the fix:
#    - If file was composed → describe as "planned but never implemented"
#    - If file was a design target → redirect to the actual file (SOUL.md)
#    - If file was in path lists → remove the entry

# 4. Check .gitignore
grep "filename" /opt/data/.gitignore
# If there's a !/filename entry, remove it (file no longer exists)

# 5. Verify no active loading mechanism exists (re-run step 3)
python3 -c "..."
```

### Typical Reference Distribution

After removing a dead file from a mature system (~20K files scanned), you'll typically find:

- ~60% of references are in files that also need other unrelated updates — fix only the stale ref
- ~25% are in design/reference docs — redirect to the actual mechanism
- ~15% are in historical analysis docs — leave as-is if they describe a fixed/removed state

## Common Patterns

| Symptom | Most Likely Cause | Fix |
|---------|-------------------|-----|
| Doc describes composition that doesn't appear in any patch file | The feature was designed/planned but never coded | Correct the doc, delete the orphan file |
| Doc and patch file agree but runtime disagrees | Patch file was written but never deployed (99-hermes-patches didn't apply it) | Apply the patch or correct the doc |
| Multiple docs describe the same composition differently | Forked documentation — one is authoritative, others are stale copies | Find the authoritative copy, fix it, update copies to point to it |
| Skill references describe a file as loaded when runtime says it's not | Skill reference was written when file existed or was planned, never updated after removal | Fix the reference, add a note about the removal if the reference is design guidance |
