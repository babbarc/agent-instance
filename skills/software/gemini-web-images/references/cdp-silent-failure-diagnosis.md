# CDP Silent Failure Diagnosis

When a CDP script returns `STATUS:OK` with empty text, or hangs until `STATUS:TIMEOUT`, the most likely cause is a silent `Runtime.evaluate` failure that returns `None` instead of actual DOM content. Here's how to diagnose and fix it.

## Step 1: Identify which `evaluate()` the script uses

Every Gemini CDP script imports `evaluate()` from one of three sources:

| Import source | Has ID-matching loop? | Handles CDP exceptions? | Correct? |
|---|---|---|---|
| `gemini_utils.py` | ❌ No | ❌ No | 🔴 Broken |
| `cdp_utils.py` | ❌ No | ❌ No | 🔴 Broken |
| `gemini-prompt-and-read.py` (local define) | ✅ Yes | ❌ No | 🟡 Partial |

Check the script's imports:
```bash
grep 'from.*import.*evaluate' /opt/data/scripts/<script>.py
```

If it imports from `gemini_utils` or `cdp_utils`, the evaluate is broken.

## Step 2: Add debug prints to confirm

Temporarily modify the `evaluate` call site to expose the raw CDP response:

```python
# Before returning
resp = json.loads(await ws.recv())
print(f"DEBUG evaluate raw: {json.dumps(resp)[:500]}", file=sys.stderr)
```

A healthy response looks like:
```json
{"id": 90, "result": {"result": {"value": "Hello world", "type": "string"}}}
```

A broken response (spontaneous event landed first):
```json
{"method": "Runtime.consoleAPICalled", "params": {"type": "log", ...}}
```

A CDP exception (document not ready):
```json
{"id": 90, "result": {"exceptionDetails": {...}, "result": {"type": "object", "subtype": "error"}}}
```

## Step 3: Apply the ID-matching fix (already applied — verify freshness)

**As of commit `ab49976`** all CDP evaluate functions are fixed:
- `gemini_utils.py` evaluate() — has ID-matching loop + exception handling ✅
- `cdp_utils.py` evaluate() — has ID-matching loop + exception handling ✅
- `gemini-prompt-and-read.py` evaluate() — already had loop, now has exception handling ✅
- `gemini-prompt-send.py` type_like_human() — now uses `Input.insertText` instead of broken DOM dispatch ✅

If scripts still return empty text after this commit, the issue is new (Gemini UI change, reverted script, or different root cause). Do not re-apply these fixes — investigate the new symptom instead.

**For reference — the fix pattern (in case scripts regress):**

Replace the broken `evaluate()` with the correct loop pattern from `references/cdp-communication-patterns.md`:

```python
async def evaluate(ws, expression, msg_id=1):
    msg = json.dumps({
        'id': msg_id,
        'method': 'Runtime.evaluate',
        'params': {'expression': expression, 'returnByValue': True}
    })
    await ws.send(msg)
    while True:
        resp = json.loads(await ws.recv())
        if 'id' in resp and resp.get('id') == msg_id:
            result = resp.get('result', {})
            # Check for CDP exceptions — exceptionDetails means the page context isn't ready
            if 'exceptionDetails' in result:
                print(f"CDP exception: {result['exceptionDetails']}", file=sys.stderr)
                return None
            return result.get('result', {}).get('value')
```

The key changes:
1. **Loop** until the response `id` matches the command `id` (ignores spontaneous events)
2. **Check for `exceptionDetails`** so failures aren't silent

## Which scripts are affected (as of commit `ab49976` — all fixed)

| Script | evaluate source | Status | Fix |
|--------|----------------|--------|-----|
| `gemini-prompt-and-read.py` | local define | ✅ Fixed | Exception handling added |
| `gemini-generate-image.py` | local define | ✅ Clean | Already had correct loop |
| `gemini-prompt-send.py` | `gemini_utils` → now imports `send_cdp` from `cdp_utils` | ✅ Fixed | ID-matching loop + Input.insertText |
| `gemini-response-read.py` | `gemini_utils` | ✅ Fixed | ID-matching loop + exception handling |
| `gemini-chat-list.py` | `gemini_utils` | ✅ Fixed | Inherits from `gemini_utils` fix |
| `gemini-thread-new.py` | `gemini_utils` | ✅ Fixed | Inherits from `gemini_utils` fix |
| `gemini-thread-open.py` | `gemini_utils` | ✅ Fixed | Inherits from `gemini_utils` fix |
| `gemini-google-login.py` | `gemini_utils` | ✅ Fixed | Inherits from `gemini_utils` fix |
| `gemini-thread-info.py` | `cdp_utils` | ✅ Fixed | Inherits from `cdp_utils` fix |
| `gemini-image-download.py` | `cdp_utils` | ✅ Fixed | Inherits from `cdp_utils` fix |
| `gemini_utils.py` | self (source) | ✅ Fixed | ID-matching loop + exception handling |
| `cdp_utils.py` | self (source) | ✅ Fixed | ID-matching loop + exception handling |

## Symptom guide

| Symptom | Likely cause |
|---------|-------------|
| `STATUS:OK` with empty text | evaluate() got a spontaneous event instead of the response → returned None |
| Hangs until `STATUS:TIMEOUT` | evaluate() returned None → `get_body_text` returns `''` → poll loop compares `''` with `''` → stability check never fires because `current != before_text` is `'' != ''` = False |
| Unhelpfully terse response | evaluate() got a partial/mismatched CDP response and the extracted delta was mostly empty |
| Intermittent failures | Spontaneous CDP events are non-deterministic — sometimes they arrive first, sometimes not |
| Script works after browser restart | Fresh page has fewer active components → fewer spontaneous events → less chance of collision |
