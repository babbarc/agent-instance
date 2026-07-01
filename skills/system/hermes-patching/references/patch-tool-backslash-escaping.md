## Backslash Escaping: When NOT to use the `patch` tool

### The problem

The `patch` tool's `old_string`/`new_string` parameters pass through JSON encoding, which interprets `\\` as an escaped backslash. When editing Python source that contains raw strings with backslash sequences (`\\b`, `\\s`, `\\u00a7`, `\\U0001f9e0`), the tool doubles every backslash.

### The fix

For any replacement involving backslash-rich content, use a Python heredoc via `terminal` or a `write_file`-then-execute pattern. The script reads the file, matches exact text (no escaping layer), and writes the result.

### Unicode escape vs literal character

When editing Python source files, `\\u00a7` in Python string data is NOT a unicode escape — just literals. To write a literal `\\u00a7` escape sequence (6 chars) into a `.py` file, use `\\u00a7` in your edit script's string literal (double backslash = one backslash in output). `\\u2014` in a Python string literal IS interpreted (becomes `—`). For literal `\\u2014` in output, use `\\\\u2014`.

### Detection

Check for backslash corruption after editing: `python3 -c "c=open('work.py','rb').read(); assert b'\\x08' not in c"` then `python3 -c "import ast; ast.parse(open('work.py').read())"`. First catches backspace bytes from corrupted `\\b`; second catches doubled-backslash syntax errors.
