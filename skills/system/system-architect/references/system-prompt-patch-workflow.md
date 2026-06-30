# System Prompt Patch Workflow

> How to locate and patch a system-prompt behavioural directive in Hermes.
> **⚠️ IMPORTANT: The patch mechanism uses `patch -p0` with unified diff files, NOT `cp` with full file copies.**
> See "Patching mechanism" below.

## When to use this

The user complains about a behavioural constraint baked into the system prompt — something that fires every turn, feels rigid, or conflicts with another instruction. Not a skill or tool issue — a **system-level behavioural directive**.

## Investigation phase

1. **Extract the gripe phrase** — Take the behaviour the user wants to change and extract a unique string from it. The system prompt sections are verbatim text constants in Python. Search for exact phrasing.

2. **Grep the Hermes install dir:**
   ```
   grep -rn '"<unique-phrase>"' /opt/hermes/
   ```
   Every system-prompt section is a Python constant in `/opt/hermes/agent/prompt_builder.py`. The grep will hit the exact line.

3. **Map the constant** — Read ~10 lines around the match to identify which constant block it belongs to:
   - `WORKFLOW_GUIDANCE` — "## Workflow", "5 phases", "CLARIFY → INVESTIGATE → PROPOSE → EXECUTE → BLOCKED". Replaced `TASK_COMPLETION_GUIDANCE` + `TOOL_USE_ENFORCEMENT_GUIDANCE` in 2026-06-08 patch.
   - `OPENAI_MODEL_EXECUTION_GUIDANCE` — "Execution discipline", "&lt;resolve_ambiguity&gt;" (was `&lt;act_dont_ask&gt;` — renamed 2026-06-08 to distinguish instruction ambiguity from execution context ambiguity)
   - `MEMORY_GUIDANCE` — **As of 2026-06-10: patched to behavioral-reanchor-only routing.** (The `memory_tool.py` description was patched earlier to 'behavioral guardrails only'; the `MEMORY_GUIDANCE` prompt constant was finally updated in this session to match.) Previous state: still used the old frame ('Save durable facts...'), creating an asymmetric patch drift against the already-patched tool description.
   - Model gate list: `TOOL_USE_ENFORCEMENT_MODELS` (tuple of model name substrings — still kept for reference but no longer gates injection; WORKFLOW_GUIDANCE is now universal)
   - `GOOGLE_MODEL_OPERATIONAL_GUIDANCE` — "Google model operational directives", per-model tactics (absolute paths, verify-first, dependency checks)
   
   Some constants are gated by model family (GOOGLE/OPENAI guidance). Others are universal (`WORKFLOW_GUIDANCE`, `MEMORY_GUIDANCE`).

4. **Understand the edit layer** — System prompt sections are Python string literals in a tuple-like assignment. The edit is: modify the string constant in the patch file. No JSON, no YAML, no config. Just the Python source.

## Patching mechanism — `patch -p0` with unified diffs

**The `99-hermes-patches` cont-init script at `/etc/cont-init.d/99-hermes-patches` (mirrored at `/opt/data/home/hermes-agent/99-hermes-patches.sh`) uses `patch -p0` to apply unified diffs.** The actual mechanism:

```bash
# Save originals (first run only — .original files persist)
cp $INSTALL_DIR/agent/prompt_builder.py $PATCHES_DIR/prompt_builder.py.original
# ^ only runs if .original doesn't already exist (2>/dev/null || true swallows the error)

# Apply patches via unified diff
for f in approval.py clarify_tool.py memory_tool.py prompt_builder.py skill_manager_tool.py system_prompt.py; do
    patch_file="$PATCHES_DIR/$f.patch"
    [ -f "$patch_file" ] || continue

    if patch --dry-run -p0 -d "$INSTALL_DIR" < "$patch_file" 2>/dev/null; then
        patch -p0 -d "$INSTALL_DIR" < "$patch_file"
    else
        echo "WARNING: patch failed for $f" >&2
    fi
done
```

**This means:**
- The patches directory needs `.patch` unified diff files, not full replacement `.py` files
- Each `.patch` file is a standard unified diff (`diff -u old new`) with `-p0` paths relative to `/opt/hermes/`
- The script does a `--dry-run` first to catch conflicts before applying
- The `.original` files are ONE-TIME backups captured on the first boot, NOT refreshed on subsequent runs
- If a `.patch` file causes a conflict (dry-run fails), the script warns and skips — the installed file stays unpatched

### How to create a patch

1. **Know your starting point.** The `.original` backup may be stale — it was captured on the first-ever container start. Since then, other patches may have been applied cumulatively.

   **Key insight — container lifecycle:** Every container boot starts from the clean image. The `99-hermes-patches` init script applies patches at boot. So:
   - **Immediately after a fresh boot before any patches ran:** the installed file = `.original` (clean upstream).
   - **After a boot where the patch failed:** the installed file = `.original` (clean upstream — because no patches were applied).
   - **After a boot where old patches were applied and you want to ADD incremental changes:** diff from CURRENT installed file (which = `.original + old patches`).
   - **After a boot where old patches were applied and you want to REPLACE with a combined patch:** diff from `.original` (because the combined patch will be applied to clean upstream at next boot, replacing the old ones).

   When in doubt, diff from `.original`. A patch that applies to clean upstream always works. A patch built from but meant for a patched file fails at next boot. See `patch-hermes-files` skill's "Diff base strategy" section for the full decision tree. (This reference previously said "always diff from CURRENT installed file" — that was wrong. The correct answer depends on whether you're stacking or replacing.)

2. Create a working copy of the CURRENT installed file:
   ```
   cp /opt/hermes/agent/prompt_builder.py /tmp/pb_current.py
   ```

3. Edit `/tmp/pb_new.py` with your changes (or apply changes programmatically in Python)

4. Generate the unified diff from current to new:
   ```
   diff -u /tmp/pb_current.py /tmp/pb_new.py > /tmp/prompt_builder.py.patch
   ```

5. Fix the paths to use `-p0` style (relative to install dir):
   ```
   sed -i 's|/tmp/pb_current.py|agent/prompt_builder.py|g' /tmp/prompt_builder.py.patch
   sed -i 's|/tmp/pb_new.py|agent/prompt_builder.py|g' /tmp/prompt_builder.py.patch
   ```

6. Save to patches directory:
   ```
   cp /tmp/prompt_builder.py.patch /opt/data/home/.hermes/patches/prompt_builder.py.patch
   ```

7. **Dry-run to verify:**
   ```
   patch --dry-run -p0 -d /opt/hermes < /opt/data/home/.hermes/patches/prompt_builder.py.patch
   ```
   If this succeeds, the patch will apply at next container init. If it fails, the patch doesn't match the current installed file — regenerate from the actual current state.

8. **Container restart** — Patches apply at boot via cont-init.d. No hot-reload. Changes take effect on next container start.

### The cumulative patch problem

When the installed file already has patches applied (from a previous init run), creating a NEW patch requires careful handling:

- **DO NOT** create a diff from `.original` to desired state and expect it to apply to the currently-patched file. The `.original` is the original Hermes code. The installed file is `.original + old patches`. A patch meant for `.original` will fail the dry-run when applied to the already-patched file.
- **DO** create a diff from the CURRENT installed file to the desired new state. This captures only your NEW changes, layered on top of all existing patches.
- After enough cumulative patches, consider replacing the old `.patch` with a combined one: revert the installed file to `.original` (if you have write access), create a single diff from `.original` to the full new state, and update the `.patch` file.

### How to check if patches are active

**Fast method — timestamp comparison:**
```
# Get patch file modification time (epoch)
stat --format '%Y' /opt/data/home/.hermes/patches/prompt_builder.py.patch

# Get container boot time (epoch)
date -d "$(uptime -s)" +%s
```
If patch_epoch > boot_epoch → patch was created AFTER this container boot → NOT applied yet. Needs a restart.
If patch_epoch < boot_epoch → patch existed when the container started → should have been applied (verify with diff).

**Thorough method — diff against original:**

```
diff /opt/data/home/.hermes/patches/<file>.py.original /opt/hermes/<path>/<file>.py
```

Exit code 0 = no differences = patch NOT applied. Exit code 1 = differences = patch IS applied.

To see WHAT was changed (the active patch content):
```
diff /opt/data/home/.hermes/patches/prompt_builder.py.original /opt/hermes/agent/prompt_builder.py | head -40
```

The init script has a limited list of files it patches. To check which files are managed:
```
grep 'for f in' /etc/cont-init.d/99-hermes-patches
```

Currently managed files: approval.py, clarify_tool.py, memory_tool.py, prompt_builder.py, skill_manager_tool.py, system_prompt.py, background_review.py.

**PITFALL: The dry-run passing does NOT verify hunk completeness.** A regenerated combined patch can pass `--dry-run` with zero hunks for a constant that was already patched — because the diff was taken from a state where that change was already applied, so it showed "no difference" and was silently dropped. After container restart, the original text returns. Always verify by counting hunks against expected line ranges, or apply the new patch to `.original` in a temp directory and diff the result against your desired state.

**PITFALL: Combined-patch dry-run WILL fail against the live installed file — this is expected.** When you create a combined patch (diff from `.original` to desired state), and the live file already has old patches applied, `patch --dry-run -p0 -d /opt/hermes` will report "Hunk #N FAILED" because the context lines in the patch (from clean upstream) don't match the live file (which has old patches stacked on top). This is NOT a problem — at next boot, the init script applies to the clean upstream where the patch works. To verify a combined patch, always test against `.original` (clean baseline), not the live file.

**PITFALL: Git-history detection of lost hunks.** When a user says "we already fixed this" but the fix isn't in the current patch file, the fix was likely lost during a previous patch regeneration. Detect this with git:
```bash
# Check the patch file's history
cd ~/.hermes
git log --all --oneline -- patches/prompt_builder.py.patch

# View an old version to find the dropped hunk
git show <commit_hash>:home/.hermes/patches/prompt_builder.py.patch | grep -A40 'MEMORY_GUIDANCE ='

# Diff the old and new patch files to see what was dropped
git diff <old_commit> <new_commit> -- home/.hermes/patches/prompt_builder.py.patch | head -100
```
Patch files in `.hermes/patches/` are git-tracked in this repo. Every regeneration creates a new commit. Never assume a regeneration was a superset of the old one — hunks that showed "no diff" during generation (because the live file already had them applied) get silently dropped.

**PITFALL: When patching Python constants with escape sequences, extract the old text programmatically.** Hand-typing Python string literals with embedded `\"`, `\\n`, `\\'`, `\\u2014`, and triple-quoted strings into a `patch()` or `replace()` call is error-prone — the escaping at the Python-source-code level (inside a .py file) differs from the escaping at the string-content level (what the constant produces). Always use `extract_block()` or `find()` on the actual file content to get the precise old text, then construct the replacement from there. See this session's `patch_mem_skills.py` for the extract_block pattern.

## Diagnosing a failed patch

When `patch --dry-run` shows `Hunk #N FAILED at line M`, the patch context doesn't match the current installed file. Three possible causes:

**Cause 1: The patch was created against an older version** — The installed Hermes image was rebuilt (new container image) and the source file changed. The patch expects context lines that no longer exist.

**Cause 2: Cumulative patches shifted the file** — A previous `99-hermes-patches` run applied patches that changed the file, and the new patch was created against the `.original` backup instead of the current installed state.

**Cause 3: The patch was created against an already-patched version** — A previous patch had already modified the file (e.g., added an `EXCEPTION` header to `TOOL_USE_ENFORCEMENT_GUIDANCE`). The NEW patch was generated FROM that already-patched state, so it expects context lines from the patched version — not the clean upstream. This is the most insidious cause because the dry-run fails silently in `99-hermes-patches` (it warns to stderr and skips — no user-facing alert).

### How to diagnose

```bash
# 1. Run dry-run and capture the exact failure
patch --dry-run -p0 -d /opt/hermes < ~/.hermes/patches/prompt_builder.py.patch 2>&1
# Expected: "checking file agent/prompt_builder.py" (exit 0)
# Failure: "Hunk #1 FAILED at 244." (exit 1)

# 2. Read the patch header to see what context it expects
head -20 ~/.hermes/patches/prompt_builder.py.patch
# The @@ offset tells you which line of the source file the hunk targets.
# The --- lines show the source file the patch was MADE from.

# 3. Inspect the context around the failed offset in both files
# If @@ -244,23 means "start at line 244 in the original file":
sed -n '240,260p' /opt/hermes/agent/prompt_builder.py
# Compare with what the patch expects (the - lines before the ---)

# 4. Check if the .original backup matches the installed file
diff ~/.hermes/patches/prompt_builder.py.original /opt/hermes/agent/prompt_builder.py | head -10
# If no diff → patch was never applied.
# If diff exists → something was applied, or the image was rebuilt.
```

### How to regenerate a stale patch

When the upstream file has drifted from what the patch expects:

1. **Copy the CURRENT installed file as your base:**
   ```bash
   cp /opt/hermes/agent/prompt_builder.py /tmp/pb_current.py
   ```
   Always use `/opt/hermes/agent/...` (the actual installed file), NOT the `.original` backup. The `.original` may be from a previous image version.

2. **Create your modified version** — edit `/tmp/pb_new.py` with the desired new constant content.

3. **Generate the diff against the current installed file:**
   ```bash
   diff -u /tmp/pb_current.py /tmp/pb_new.py > /tmp/fix.patch
   sed -i 's|/tmp/pb_current.py|agent/prompt_builder.py|g; s|/tmp/pb_new.py|agent/prompt_builder.py|g' /tmp/fix.patch
   ```

4. **Save and verify:**
   ```bash
   cp /tmp/fix.patch ~/.hermes/patches/prompt_builder.py.patch
   patch --dry-run -p0 -d /opt/hermes < ~/.hermes/patches/prompt_builder.py.patch
   # MUST exit 0 with no "FAILED" output
   ```

5. **Update the `.original` backup** (optional — keeps future diagnostics honest):
   ```bash
   cp /opt/hermes/agent/prompt_builder.py ~/.hermes/patches/prompt_builder.py.original
   ```
   This is a one-shot backup from the FIRST boot; updating it means future diffs will compare against the correct baseline.

6. **Container restart** — the new patch applies at next boot via `99-hermes-patches`.

### Preventing stale patches

- **Choose your diff base correctly.** See "How to create a patch" above for the container-lifecycle-aware decision tree. The old advice "always diff from CURRENT installed file" is only half the picture — it applies when stacking incremental patches, not when replacing or creating a first-time patch.
- **After regenerating a patch, verify the `.original` backup is also updated** so timestamp-based checks remain accurate.
- **Test the dry-run before and after** — the old dry-run should fail, the new one should pass.

## Key pitfalls

- **Don't assume something cannot be patched.** System prompt sections are Python source in the Hermes install dir. Anything in that directory can be patched via the `99-hermes-patches` mechanism. The only things that truly can't change are: (a) the Hermes Go gateway binary and (b) the Python engine's tool-schema definitions (tool names, required/optional params, schema shapes) — because the engine validates tool calls against the schema before the LLM even sees them.
- **Don't confuse "frozen for the current session" with "frozen permanently."** The system prompt is cached per-session, but the source file (prompt_builder.py) is mutable. A new session after restart will see the patched version.
- **Don't try to edit installed files directly.** The Hermes install dir is owned by uid 10000; the agent runs as uid 1003 (hermes). Direct writes get "Permission denied." The ONLY way to patch installed files is through the `99-hermes-patches` mechanism: create `.patch` files in `~/.hermes/patches/`.
- **Don't confuse patchable files with directly-editable files.** SOUL.md, MEMORY.md, and USER.md are loaded from HERMES_HOME (owned by uid 1003) and CAN be edited directly via `patch` tool or `write_file`. The only installed files requiring the patch mechanism are those under `/opt/hermes/` (owned by uid 10000).
- **MEMORY.md loads every turn but changes require explicit `memory()` tool calls to persist.** The patching workflow in prompt_builder.py handles the system-level constants. MEMORY.md handles behavioral re-anchors (per-turn corrections). Don't conflate the two layers.
- **After patching a constant that was gated by model family**, verify your model substring is in `TOOL_USE_ENFORCEMENT_MODELS`. If you add a carve-out to `TOOL_USE_ENFORCEMENT_GUIDANCE` but your model isn't in the gating tuple, the carve-out never fires.
- **`patch --dry-run` does NOT verify Python syntax.** A patch can pass dry-run with perfect context matching but produce an invalid Python file (e.g., unterminated string literal from mixed `'...'`/`"..."` delimiters). Always apply the patch to a temp copy of the `.original` and verify the result compiles:
  ```bash
  cp /opt/hermes/agent/background_review.py /tmp/test_patch.py
  patch -p0 /tmp/test_patch.py < ~/.hermes/patches/background_review.py.patch
  python3 -c "import py_compile; py_compile.compile('/tmp/test_patch.py', doraise=True)"
  ```
  If this fails, the patch will crash Hermes at boot.
- **String delimiter consistency:** The Hermes codebase uses `"..."` (double-quoted) strings for all Python string continuations. When constructing replacement text, never use `'...'` single-quoted strings for continuation lines — they're valid Python but easy to leave unterminated, and mixing quote styles is visually confusing. Always match the surrounding style.
- **If a patch doesn't take effect after restart**, check: (a) the `.patch` file exists in the patches directory, (b) it's a `.patch` file (not a `.py` file — those are ignored), (c) the filename matches the `for f in ...` list in `/etc/cont-init.d/99-hermes-patches`, (d) run `patch --dry-run -p0` manually to check for conflicts, (e) verify the diff paths are relative to `/opt/hermes/` with `-p0` style (e.g., `agent/prompt_builder.py`).
