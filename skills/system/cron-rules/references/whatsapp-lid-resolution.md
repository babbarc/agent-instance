# WhatsApp LID Resolution — `_jid_to_phone()` Fix

## Problem

WhatsApp is migrating some accounts from phone-number JIDs (`447917911831@s.whatsapp.net`) to LID-based JIDs where the prefix is a large numeric ID (`37516572946636`). The heartbeat's data script `whatsapp_delta.py` could not resolve these to real phone numbers, producing `!!UNKNOWN:pushName!!` tags.

## Root Cause — Two Bugs

**Bug 1: `_jid_to_phone()` only handled LIDs via `@lid` suffix.**  
WhatsApp now uses `@s.whatsapp.net` for LID-based accounts too. The raw JID prefix (`37516572946636`) was returned as-is, which is not a real phone number.

**Bug 2: `_run_gapi()` passed raw digits to Google People API search.**  
Even after Bug 1 was fixed (returning `447894348698`), the Google People API's `searchContacts()` method does NOT match raw digit strings. It needs the formatted display version with `+` prefix and spaces (e.g. `+44 7894 348698` or even `7894 348698`).

## The Fixes

### Bug 1 — `_jid_to_phone()` (applied June 2026)

```python
def _jid_to_phone(jid: str) -> str | None:
    if jid.endswith("@s.whatsapp.net"):
        prefix = jid.split("@")[0]
        lid_phone = _lid_to_phone(prefix)
        return lid_phone or prefix
    if jid.endswith("@lid"):
        return _lid_to_phone(jid.split("@")[0])
    return None
```

### Bug 2 — Google API phone search format

In `_resolve_and_link()`, the phone string passed to `_run_gapi()` must be formatted for Google's search index. The `_format_phone()` function (adds `+` prefix) is insufficient.

**Phone formats that work with Google People API `searchContacts()`:**

| Format | Example | Works? |
|--------|---------|--------|
| Raw digits | `447894348698` | ❌ |
| `+` prefix only, no spaces | `+447894348698` | ❌ |
| `+` + country code + space + national | `+44 7894 348698` | ✅ |
| National number with space | `7894 348698` | ✅ |
| Last 4 digits only | `8698` | ❌ |
| Name search | `Naresh` | ✅ |

**The fix pattern — format the phone before passing to `_run_gapi()`:**

```python
# Step 2: Google Contacts search
# Raw digits don't match — format to display format
formatted = _format_phone(phone)  # e.g. "+447894348698"
# Also try national number with space separator for partial matching
national = phone[2:]  # strip country code
if len(national) >= 7:
    google_query = national[:4] + " " + national[4:]  # "7894 348698"
    results = _run_gapi(google_query)
```

**Alternative:** Always try both `_format_phone(phone)` and the spaced national format, returning the first non-empty result. This avoids guessing which format Google indexed.

## How LID Resolution Works

1. WhatsApp session maintains `lid-mapping-{phone}.json` (forward: phone → LID) files
2. When a contact is resolved, the session creates `lid-mapping-{lid}_reverse.json` (reverse: LID → phone)
3. `_lid_to_phone(lid)` checks for the reverse file at `session/lid-mapping-{lid}_reverse.json`
4. If found, returns the real phone number (e.g. `447894348698`)
5. If not found, returns None → caller falls back to the raw prefix

## Mapping File Format

```
Forward:  session/lid-mapping-447894348698.json          → "37516572946636"
Reverse:  session/lid-mapping-37516572946636_reverse.json → "447894348698"
```

Both are created automatically by the WhatsApp session as contacts are resolved.

## Why the short display name (`--- 946636 ---`)

The heartbeat output shows `--- 946636 ---` as the conversation separator, but this is the **last 6 digits** of the full JID prefix:

```python
# whatsapp_delta.py line ~702
short = jid.split("@")[0][-6:] if "@" in jid else jid[:6]
```

So `946636` → full LID `37516572946636@s.whatsapp.net`. The fix resolves the full JID correctly.

## Resolution Chain After Fixes

1. `_jid_to_phone('37516572946636@s.whatsapp.net')` → `'447894348698'`
2. `_resolve_and_link()` searches contact files for phone `447894348698` — local files use `_normalize_phone()` (strip non-digits) for matching
3. If found → links JID to existing contact file
4. If not found → searches Google Contacts via `_run_gapi(formatted_phone)`
   - **⚠️ Must format phone for Google's search index (see Bug 2 above)**
5. If Google Contacts has it → seeds a new contact file via `_seed_contact()`
6. If not → remains `!!UNKNOWN:pushName!!` (correct — no data to link from)

## Verification

```python
_jid_to_phone('447917911831@s.whatsapp.net')   → '447917911831'  # unchanged
_jid_to_phone('37516572946636@s.whatsapp.net') → '447894348698'  # resolved via LID
_jid_to_phone('946636@s.whatsapp.net')         → '946636'        # short truncated — no reverse mapping
_jid_to_phone('111111@s.whatsapp.net')         → '111111'        # unknown LID, fallback
_jid_to_phone('946636@lid')                    → None            # @lid path unchanged
```

## Real Example — Naresh Bansal (20:04 heartbeat run, 16 Jun 2026)

```
JID:       37516572946636@s.whatsapp.net
Push name: NB
LID:       37516572946636
Phone:     447894348698
Google:    Naresh Bansal (+44 7894 348698, bansal.naresh@gmail.com)
```

`_jid_to_phone()` returned `447894348698` correctly (Bug 1 fixed). But `_run_gapi("447894348698")` returned empty because Google's search needs `"+44 7894 348698"` or `"7894 348698"` (Bug 2 — unfixed as of this writing).
