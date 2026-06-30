# Google Contacts Phone Matching — Country-Code Search Limitations

## The Bug

`whatsapp_delta.py`'s `_resolve_and_link()` Step 2 searches Google Contacts by country code (`+44`) with no `--max` flag (defaults to pageSize=30), then iterates returned contacts doing an exact phone match via `_normalize_phone(gp) == normalized_phone`.

**This misses contacts that exist but don't appear in the top 30 UK results.**

### Real example (Naresh Bansal, June 2026)

| Step | Query | Results | Outcome |
|------|-------|---------|---------|
| Country code search | `searchContacts("+44")` | 10 contacts returned | Naresh not in results |
| Exact phone match | `447894348698` | Fall through — not in 10 results | Missed |
| Push-name search (not executed) | `searchContacts("NB")` | 0 results | Would also miss |
| Name search (not executed) | `searchContacts("Naresh")` | 2 results, includes Naresh with phone `+44 7894 348698` | Would find him |

Phone `447894348698` normalizes correctly from `+44 7894 348698`. The contact exists in My Contacts. The script simply never searches using a query that returns him.

## Fix: Push-Name Fallback in Step 2

After the country-code search + exact phone match fails, add:

```python
# Fallback: search by formatted phone (Google API handles spaces better than digits-only)
gc_result = _run_gapi(phone)  # "+44 7894 348698" not "447894348698"
if gc_result:
    for match in gc_result:
        for gp in match.get("phones", []):
            gp_digits = _normalize_phone(gp)
            if gp_digits == normalized_phone:
                return _link_or_seed(match)
```

This searches by the **formatted phone** (with spaces and + prefix) which Google People API handles better than a bare digit string. The client-side phone match is the same logic as the country-code search — if the contact has the phone, it gets found now.

## Why Country-Code Search Misses Contacts

Google People API's `searchContacts()` uses relevance ranking, not exhaustive "all contacts matching this criterion." A country-code query (`+44`) returns the most relevant 30 contacts — not ALL contacts with UK numbers. Contacts with:
- Fewer interactions
- Auto-saved ("Other Contacts") vs manually saved ("My Contacts")
- Names that rank lower in relevance

...may be excluded from the default search results. The fix bypasses this by searching the specific phone number, which either returns the exact contact or nothing — no ranking ambiguity.

## Why the fix goes in `whatsapp_delta.py`

The `_resolve_and_link()` function is the single entry point for JID-to-contact resolution. Adding the formatted-phone fallback there covers all code paths (heartbeat, enrichment, all callers) without changing any other script.

## Testing

After the fix, search the phone directly from the LID reverse mapping:
```bash
python3 /opt/data/skills/productivity/google-workspace/scripts/google_api.py \
  --account pallav contacts search "+44 7894 348698"
```
Should return the contact by name (even if the formatted query differs from the stored format).
