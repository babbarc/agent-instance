#!/usr/bin/env python3
"""Validate a unified-diff .patch file's hunk headers match body counts.

Usage: python3 scripts/validate-patch.py [path/to/file.patch ...]

Reads each .patch file, parses every hunk, and verifies:
  - old-side count (removed + context) matches header's -old_count
  - new-side count (added + context) matches header's +new_count

Exits 0 if all hunks are valid. Prints one error per mismatch to stderr,
exits 1 if any hunk is malformed.

Call THIS SCRIPT after `diff -u` / `sed -i` (step 4) and before
`patch --dry-run` (step 5) in the patch-workflow. It catches header/body
mismatches that `patch` silently labels "malformed patch" only at apply time.
"""

import sys
import re

HUNK_HEADER_RE = re.compile(
    r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@'
)

def validate(path: str) -> list[str]:
    errors: list[str] = []
    with open(path, 'rb') as f:
        raw = f.read()

    # Parse as text lines, preserving CRLF/EOL as-is
    lines = raw.split(b'\n')
    # Remove trailing empty from split if file ends in newline
    if lines and lines[-1] == b'':
        lines = lines[:-1]

    in_hunk = False
    hunk_removed = 0
    hunk_added = 0
    hunk_context = 0
    hunk_line = ''   # the @@ header line for error messages
    hunk_start_idx = 0  # line index in the file

    for idx, line in enumerate(lines):
        decoded = line.decode('utf-8', errors='replace')

        if line.startswith(b'@@'):
            # Validate previous hunk if we were inside one
            if in_hunk:
                _check_hunk(errors, path, hunk_line, hunk_start_idx,
                            hunk_removed, hunk_added, hunk_context)

            # Parse new hunk header
            m = HUNK_HEADER_RE.match(decoded)
            if not m:
                errors.append(
                    f"{path}:{idx+1}: unparseable hunk header: {decoded[:60]}"
                )
                in_hunk = False
                continue

            in_hunk = True
            hunk_line = decoded
            hunk_start_idx = idx
            hunk_removed = 0
            hunk_added = 0
            hunk_context = 0

        elif in_hunk:
            if line.startswith(b'-') and not line.startswith(b'---'):
                hunk_removed += 1
            elif line.startswith(b'+') and not line.startswith(b'+++'):
                hunk_added += 1
            elif line.startswith(b' '):
                hunk_context += 1
            elif line.startswith(b'\\'):
                # "\ No newline at end of file" — ignore
                pass
            else:
                # Blank line or unexpected — end of hunk
                in_hunk = False

    # Validate the last hunk
    if in_hunk:
        _check_hunk(errors, path, hunk_line, hunk_start_idx,
                    hunk_removed, hunk_added, hunk_context)

    return errors


def _check_hunk(errors, path, header, start_idx,
                hunk_removed, hunk_added, hunk_context):
    m = HUNK_HEADER_RE.match(header)
    if not m:
        return  # already flagged

    old_count_str = m.group(2)
    new_count_str = m.group(4)
    # diff defaults missing count to 1 — but a bare line number without
    # comma implies count=1 at that position.  The match groups capture
    # the comma+digits or None.
    old_header = int(old_count_str) if old_count_str else 1
    new_header = int(new_count_str) if new_count_str else 1

    old_actual = hunk_removed + hunk_context
    new_actual = hunk_added + hunk_context

    ok = True
    if old_actual != old_header:
        ok = False
        errors.append(
            f"{path}:{start_idx+1}: old-side count mismatch: "
            f"header says -{old_header}, body has "
            f"removed={hunk_removed}+context={hunk_context}={old_actual}"
        )
    if new_actual != new_header:
        ok = False
        errors.append(
            f"{path}:{start_idx+1}: new-side count mismatch: "
            f"header says +{new_header}, body has "
            f"added={hunk_added}+context={hunk_context}={new_actual}"
        )


def main():
    if len(sys.argv) < 2:
        print("Usage: validate-patch.py <file.patch ...>", file=sys.stderr)
        sys.exit(2)

    all_errors = []
    for arg in sys.argv[1:]:
        all_errors.extend(validate(arg))

    if all_errors:
        for e in all_errors:
            print(e, file=sys.stderr)
        sys.exit(1)
    else:
        print("All hunks valid.")


if __name__ == '__main__':
    main()
