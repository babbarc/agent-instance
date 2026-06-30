# OneNote Plugin — Debugging Walkthrough

Located at `/opt/data/plugins/onenote/`. A tool-registration plugin wrapping the onenote_api.py CLI script.

## Bug Encountered

On first tool call, `onenote_list_notebooks` raised:

```
TypeError: _handle_list_notebooks() got an unexpected keyword argument 'task_id'
```

## Root Cause

All 6 handlers were defined as `def _handle_*(args)` without accepting `**kwargs`. The Hermes dispatch framework calls `handler(args, task_id=..., user_task=...)` — handlers MUST absorb these extra kwargs.

## Fix

```python
# Before (broken)
def _handle_list_notebooks(args: dict[str, Any]) -> str:

# After (fixed)
def _handle_list_notebooks(args: dict[str, Any], **kwargs) -> str:
```

Applied to all 6 handlers in `tools.py`.

## Second Bug

After fixing the TypeError, the tool returned "❌ Could not acquire token. Re-auth needed." despite working correctly from the terminal.

## Root Cause

The gateway process has `HOME=/opt/data` while the terminal has `HOME=/opt/data/home`. The script uses `os.path.expanduser("~/.cache/microsoft-tokens/token.json")` which resolves differently:

| Context | HOME | Token path resolved | Exists? |
|---------|------|-------------------|---------|
| Terminal | /opt/data/home | /opt/data/home/.cache/.../token.json | Yes |
| Gateway subprocess | /opt/data | /opt/data/.cache/.../token.json | No |

## Fix

Hardcode the absolute token path in the script, or symlink the cache directory.

## Key Lessons

- Always define tool handlers with `**kwargs`
- Subprocess env differs from interactive env — check `$HOME` first when tools work in terminal but not gateway
- Plugin changes need process restart and `__pycache__/` cleanup