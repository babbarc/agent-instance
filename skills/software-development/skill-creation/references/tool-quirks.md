# Hermes Tool Quirks (execute_code context)

## Q1 — `hermes_tools.read_file` returns line-number-prefixed content

When called from `execute_code`, `hermes_tools.read_file(path)['content']` returns each line prefixed with its line number and a pipe:

```
Got:     '1|---\n2|name: my-skill\n3|version: 1.0.0'
Wanted:  '---\nname: my-skill\nversion: 1.0.0'
```

**Impact:** Using this content directly with `write_file` or `str.replace` embeds line numbers into the target file — corrupts it.

**Fix — strip line numbers before processing:**
```python
from hermes_tools import read_file
import re

raw = read_file(path)['content']
clean = re.sub(r'^\s*\d+\|', '', raw, flags=re.MULTILINE)
# Now use 'clean' for write_file or string operations
```

**Alternative — read via terminal:**
```python
from hermes_tools import terminal
r = terminal(f"cat {path}")
# r['output'] is raw, no line numbers
r = terminal(f"python3 -c \"open(open('{path}').read())\"")
```
