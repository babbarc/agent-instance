# Portal Download in Headless Chrome

> General patterns for downloading files from web portals (PrimeFaces, ASP.NET, SPA) in a headless Hermes browser session.

## The Core Problem

Many government/enterprise portals use server-side frameworks (PrimeFaces/JSF, ASP.NET WebForms, Oracle ADF) that serve file downloads through AJAX callbacks, form POST responses, or JavaScript-initiated blob downloads — not direct URL links. In a headless browser:

- The download lands in the **browser container's** Downloads directory, not the host filesystem
- Direct curl/wget to a URL won't work (no static URL, tokens expire per-request)
- `Page.printToPDF` only works if the document is rendered in the viewport

## Retrieval Pattern

### Browser container

If using `hermes-browser` container:

```bash
# List downloaded files
podman exec hermes-browser ls -la /home/chrome/Downloads/

# Copy latest to host
podman cp hermes-browser:/home/chrome/Downloads/<filename> /tmp/
```

### Local chrome-downloads

If running locally with Chrome profile at `~/chrome-downloads/`:

```bash
ls -la ~/chrome-downloads/downloads/
```

## Framework-Specific Patterns

### PrimeFaces (JSF) — France-Visas, similar government portals

The button triggers `PrimeFaces.ab()` AJAX. The server returns a form update + sets a cookie (`primefaces.download_<page>=true`). PrimeFaces then calls `PrimeFaces.download(url, name)` internally which XHRs the actual file as a blob.

**Strategy:** Click the button via browser_click or CDP Runtime.evaluate, then retrieve from container Downloads.

**Detection:** Look for `primefaces.download_<pagename>=true` cookie after clicking — confirms the server-side download action fired.

### ASP.NET WebForms / UpdatePanel

Similar pattern — button click triggers a `__doPostBack()` partial postback. Server returns the file wrapped in a special response.

**Strategy:** Same as PrimeFaces — click the button, retrieve from Downloads.

### SPA Blob Downloads (React/Vue)

Some SPAs fetch the file via XHR `responseType: 'blob'` and create a temporary blob: URL.

**Strategy:** Override `window.URL.createObjectURL` or the download function to capture the blob data as base64:

```javascript
var origCreate = window.URL.createObjectURL;
window.URL.createObjectURL = function(blob) {
  var url = origCreate.apply(this, arguments);
  var reader = new FileReader();
  reader.onloadend = function() {
    window._capturedBlob = reader.result;
    window._capturedBlobReady = true;
  };
  reader.readAsDataURL(blob);
  return url;
};
```

## Pitfalls

- **Multiple clicks = multiple files** — each click creates a new copy with `(1)`, `(2)` suffixes. Use `ls -lt` to find the latest.
- **The button may use PrimeFaces AB** — `PrimeFaces.ab({s:"...", f:"...", u:"...", ...})`. The `s` param is the source component ID. You can click it via `document.getElementById(sourceId).click()`.
- **Some portals require the application/group to be expanded first** — the download button may only be rendered when the accordion/fieldset is open.
- **Download cookie = confirmation** — if the framework-specific download cookie isn't set after clicking, the server-side action failed.
