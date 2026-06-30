# Cumulative Patch Rebuild

Use when an existing patch needs one line changed and you must preserve all other hunks.

1. Copy `.original` → `~/scratch/cumulative/current.py`
2. Apply existing patch to it:
   `mkdir -p ~/scratch/cumulative`
   # Replace the exact path from the patch header (grep the first line for it, e.g. `agent/prompt_builder.py` or `tools/memory_tool.py`)
   `sed 's|<exact-path-from-patch-header>|current.py|' ~/.hermes/patches/<file>.py.patch > ~/scratch/cumulative/work.patch`
   `cd ~/scratch/cumulative && patch -p0 < work.patch`
   (Do NOT use `/tmp/` — `patch` treats `/tmp` paths as "dangerous" and enters interactive prompting, hanging the process.)
3. Copy patched → `~/scratch/cumulative/new.py`, make your change
4. `diff -u ~/scratch/cumulative/current.py ~/scratch/cumulative/new.py > ~/scratch/cumulative/fix.patch`
5. Fix paths: `sed -i 's|~/scratch/cumulative/current.py|<path/to/file.py>|g; s|~/scratch/cumulative/new.py|<path/to/file.py>|g' ~/scratch/cumulative/fix.patch`
6. Dry-run against `.original` (not installed file). Match the directory structure the diff expects:
   ```
   mkdir -p /tmp/verify_cumulative/tools  # or agent/ depending on the file
   cp ~/.hermes/patches/<file>.py.original /tmp/verify_cumulative/<path/to/file.py>
   cd /tmp/verify_cumulative && patch --dry-run -p0 < ~/scratch/cumulative/fix.patch
   ```
   Use `-p0` (same as the init script), and place `.original` at the exact path the patch header uses.
7. Count hunks: `grep -c '^@@' ~/scratch/cumulative/fix.patch`. Verify against old count: `grep -c '^@@' ~/.hermes/patches/<file>.py.patch` + 1 (the new hunk).
8. Save: `cp ~/scratch/cumulative/fix.patch ~/.hermes/patches/<file>.py.patch`
