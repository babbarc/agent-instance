# read_file Pipe Corruption Pitfall

`read_file` returns lines in the format `LINE_NUM|CONTENT` — the `|` is a **display separator**, not part of the content. When you copy lines from a `read_file` output into a `patch` call (old_string/new_string parameters), the `|` and line number bleed into the patch text and corrupt it.

## The failure signature

The `patch` tool produces a unified diff where `---` lines from the original file are replaced by `|---` lines in the display output, and line numbers + pipes from `read_file` are embedded in the patch content instead of the actual file text.

## The fix

Never copy lines from `read_file` output directly into `patch`/`write_file`. Instead:

1. **Use `cat` in terminal** to get raw file content without line numbers or separators
2. **Use `python3 -c`** to extract the exact text from a file
3. **Use `terminal(grep ...)`** without `-n` flag for raw match output

## Example

```bash
# Wrong — copies "42|def foo():|" instead of "def foo():"
# (from read_file output showing "42|def foo():")

# Right — get raw content
cat path/to/file.py | head -50
python3 -c "print(open('path/to/file.py').read())"
```
