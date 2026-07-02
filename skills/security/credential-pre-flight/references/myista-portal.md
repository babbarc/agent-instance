# My ista UK Portal — Access & Document Download

> Access technique for the myista.co.uk energy billing portal. Account details and invoice history in `memory/finance/accounts/` — query via QMD or `search_files`.

## Login Technique

The myista login is an SPA with `input[name="username"]` and `input[name="password"]` fields. CDP `Runtime.evaluate` with native value setter + event dispatch often fails to trigger the framework state (known SPA Login Fallback Trap — see main credential-pre-flight skill).

**Working approach for SPA portals like this:**

1. Navigate to `https://myista.co.uk/auth/login`
2. Use `cdp-pass-inject.py` from the credential-pre-flight skill — reads from `pass` internally with zero tool-param exposure:
   ```
   python3 /opt/data/skills/security/credential-pre-flight/scripts/cdp-pass-inject.py <pass>/myista.co.uk 'input[name="password"]'
   ```
3. To also fill the username field (not a secret), use `Runtime.evaluate` via CDP or `browser_type` since email/username is not sensitive
4. Click the submit button via `document.querySelector('#account_login_submit').click()`
5. If CDP injection fails entirely (SPA ignores value setters), fall through per the timebox rule in the main protocol — ask the user for permission to use `browser_type` once

## Transaction History

URL: `https://myista.co.uk/billandpayment`
- Multiple pages of transaction history (10 rows per page)
- Pagination uses CSS pseudo-elements for PREVIOUS/NEXT buttons — not accessible via DOM queries. Use `browser_snapshot` to find their ref IDs and `browser_click(ref)` to navigate.
- Each Invoice row has a link in the 5th column (`<td>:last-child a`)

## Document Download

- Invoice URLs: `https://myista.co.uk/document/{id}`
- Opens an iframe-based PDF viewer (docs.myista.co.uk with token auth)
- ⚠️ **Download button does NOT work** in headless — clicking it navigates to `chrome://newtab/`
- **Working method:** Use `Page.printToPDF` via CDP after navigating to the document page:
  1. `browser_navigate("https://myista.co.uk/document/{id}")`
  2. Wait 2s for PDF viewer to load
  3. `browser_cdp(method='Page.printToPDF', params={{...}}, target_id=<page_target>)`
  4. Decode base64 `data` field and save as `.pdf`
  5. Reusable script at `web-expert/scripts/batch-download-ista.py`
- PDFs saved to `/nebula/.hermes-docs/02-Finance/ista_invoice_{id}.pdf`
