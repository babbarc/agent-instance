# Gemini Follow-Up Image Modification (11 Jun 2026)

## Discovery

Gemini **can** modify previously generated images via a follow-up message in the same conversation thread. Confirmed by live testing on 10-11 Jun 2026.

## Flow

1. Generate an image via `gemini-generate-image.py` (fresh chat on `/images`)
2. Send a follow-up instruction using the `--follow-up` flag:
   ```bash
   python3 gemini-generate-image.py \
     "Modify the image you just created. Change 'Pallav and Priyanka' to just 'Priyanka'. Remove the 'Hosted by' line." \
     --output /tmp/modified.jpg --follow-up
   ```
3. The follow-up stays in the current conversation — it does NOT navigate to `/images`
4. Gemini produces a **new image** with the requested changes, preserving overall visual style

## How Gemini Stores Images (Two Source Types)

AI-generated images in Gemini appear in the DOM as one of two URL types:

1. **`blob:https://gemini.google.com/...`** — in-memory blob. Both the original and follow-up images may be blob URLs. These **cannot** be fetched via `fetch()` ("Failed to fetch" — CORS restriction on blob URLs). Reliable download method: `new Image()` + canvas.

2. **`lh3.googleusercontent.com/...`** — Google CDN URL. These are standard HTTP image URLs. Download via `fetch()` + blob + FileReader (navigate browser to URL directly, then use fetch).

The rebuilt `gemini-image-download.py` (11 Jun 2026) handles **blob URLs only** via `new Image()` + canvas. For CDN URLs, use the workaround below.

## How to Download: Blob URL Approach (Primary)

The rebuilt `gemini-image-download.py` handles blob URLs without any workaround:

```bash
# Single command — opens thread, finds images, downloads
python3 /opt/data/scripts/gemini-image-download.py \
  --thread "Bombay Brunch Baby Shower RSVP Card" \
  --image 2 \
  --output /tmp/modified.jpg
```

**How it works internally (`new Image()` + canvas):**
1. Scans `[class*="conversation-container"]` for `img[src*="blob:"]` — finds ALL images in DOM order
2. Creates a programmatic `new Image()` object, sets `src` to the blob URL
3. Waits for `onload` event (the blob resolves in the browser's image pipeline)
4. Draws to a `<canvas>`, exports as JPEG via `toDataURL('image/jpeg', 0.92)`
5. Reads base64 in 100KB chunks via CDP `Runtime.evaluate`
6. Decodes and saves to disk

**Why this works but `fetch()` doesn't:** `blob:` URLs are in-memory references to data created by `URL.createObjectURL()`. The browser's image element rendering pipeline (`new Image()` + `onload`) has access to this data. But `fetch()` is subject to CORS — modern browsers block fetch on blob URLs from the page context.

**Why `naturalWidth > 0` is unreliable:** DOM `<img>` elements with `blob:` URLs that are offscreen (e.g., in a navigated-into thread's history) have `naturalWidth: 0` and `complete: false`. The old download approach that checked `img.naturalWidth > 0` would miss these entirely. The conversation-container scan avoids this dependency.

## How to Download: CDN URL Approach (Fallback)

If the image is served from `lh3.googleusercontent.com/...` instead of a blob URL:

1. Navigate the browser to the image URL with `=s1024` (full res) suffix:
   ```bash
   browser_navigate(url="https://lh3.googleusercontent.com/gg/<long-hash>=s1024")
   ```
2. The page renders the raw image file as a static `<img>`
3. Use CDP `Runtime.evaluate` to fetch and base64-encode:
   ```javascript
   (async function() {
     const r = await fetch(document.location.href);
     const b = await r.blob();
     const p = new Promise(function(rj) {
       const reader = new FileReader();
       reader.onload = function() { rj(reader.result); };
       reader.readAsDataURL(b);
     });
     const dataUrl = await p;
     window._b64 = dataUrl.split(',')[1];
     window._len = window._b64.length;
     return window._len;
   })()
   ```
   Returns ~1.6M chars of base64 for a 572x1024 image.
4. Read base64 in 100K chunks using `window._b64.substring(start, end)` via `Runtime.evaluate`
5. Decode and write with Python.

## How to Count Turns Before Downloading

```bash
python3 /opt/data/scripts/gemini-thread-info.py --thread "Bombay Brunch Baby Shower RSVP Card"
# Returns: {"turns": 3, "images": 2, ...}
# Turns 1-2 have images (image gen prompts), turn 3 is a text query
# Use --verbose for per-turn details
```

The script counts `[class*="conversation-container"]` elements (each = 1 user+AI exchange) and counts blob images inside each container. This is the most reliable way to know how many images exist and which position to download.

## Key DOM Structure (Discovered 11 Jun 2026)

- **Turn containers:** Each conversation turn is an Angular component with class containing `"conversation-container"`. DOM order = chronological order (oldest first).
- **Image detection:** AI-generated images are `<img>` elements with `src` starting with `"blob:"` nested inside conversation containers.
- **Scroll container:** The main content area is an `INFINITE-SCROLLER` with `chat-history` in its class name, NOT the `document.body`. Scripts that need to trigger lazy-loading should scroll this element.
- **ARIA roles:** Gemini does NOT use `role="user"` or `role="assistant"` on message elements. Don't rely on ARIA roles for turn detection.
- **Edit buttons:** Each user message has one edit button (detectable via `[aria-label*="edit" i]`), but it may only be visible for the most recent message.

## Critical Pitfall: Thread Navigation

When `--thread` specifies a title that partially matches multiple conversations, the exact-match comparison (`textContent.trim() === title`) is essential. A `includes()` match or fuzzy match may open the wrong thread (e.g., "Bombay Brunch Baby Shower Invitation Design" instead of "Bombay Brunch Baby Shower RSVP Card"). The script uses strict equality — if `STATUS:NOT_FOUND` is returned, check the exact title via `gemini-thread-open.py --list`.

## Result From The Session (10 Jun 2026)

The follow-up modification workflow produced a 572x1024 image where:
- "PALLAV & PRIYANKA'S BABY SHOWER" → "PRIYANKA'S BABY SHOWER" ✅
- "HOSTED BY: PALLAV, PRIYANKA & TEJAL" line completely removed ✅
- RSVP form fields replaced with warm message: "Join us for an afternoon of love, laughter, and delicious Bombay flavours!" ✅
- All floral borders, gold tones, jewel colours preserved ✅
