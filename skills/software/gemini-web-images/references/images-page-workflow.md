# Gemini Images Page — CDP Workflow

## Important: Image Generation Needs the `/images` URL

Gemini's image generation (Imagen) lives at **`https://gemini.google.com/images`**, not the main chat page. Sending an image prompt to the chat page produces a text description, not a generated image.

## Workflow

### 1. Navigate to the Images page

Open a CDP-capable browser and navigate to:
```
https://gemini.google.com/images
```

### 2. Send a prompt

The `.ql-editor` contenteditable input exists on this page too (same Quill editor element as the chat page). `gemini-prompt-send.py` works here:

```bash
python3 /opt/data/scripts/gemini-prompt-send.py "Create an RSVP card with..."
```

**CDP fallback** (if the script fails):
```javascript
// Set the input text
document.querySelector('.ql-editor').textContent = 'Your prompt here';
document.querySelector('.ql-editor').dispatchEvent(new Event('input', {bubbles: true}));

// Click send
document.querySelector('button[aria-label*="Send"]')?.click();
```

### 3. Wait and check for generated image

`gemini-response-read.py` **does not reliably detect image responses** on the `/images` page — it times out even when the image was generated successfully.

**Reliable check via CDP:**
```
Runtime.evaluate
expression: JSON.stringify(Array.from(document.querySelectorAll('img')).map(i => ({src: i.src?.substring(0,80), w: i.naturalWidth, h: i.naturalHeight, complete: i.complete, alt: i.alt})))
```

The generated image appears as a `blob:https://gemini.google.com/...` URL with:
- `alt` text ending in `", AI generated"`
- `complete: true` when rendering is done
- Natural dimensions (e.g. 572x1024 for portrait cards)

### 4. Download the image

`gemini-image-download.py` works correctly on the Images page — it finds the last AI-generated image by alt text and downloads it:

```bash
python3 /opt/data/scripts/gemini-image-download.py --output /tmp/result.jpg --quality 0.92
```

### 5. Refine (if needed) — Use Follow-Up or Regenerate

**Option A — Follow-up in same thread (preferred):** Gemini CAN modify existing generated images via a follow-up message in the same conversation. Send a modification instruction with `gemini-generate-image.py --follow-up`:

```bash
python3 /opt/data/scripts/gemini-generate-image.py \
  "Modify the image you just created. Change 'Pallav and Priyanka' to just 'Priyanka'. Remove the 'Hosted by' line. Replace blank RSVP fields with a warm personal message." \
  --output /tmp/modified.jpg --follow-up
```

**How it works:** Gemini produces a NEW image with the requested changes, preserving overall visual style. The modified image appears alongside the original in the same thread. The image may be served as a `blob:` URL (in-memory) or from `lh3.googleusercontent.com/...` (Google CDN). The `gemini-image-download.py --thread` approach handles both cases for already-existing threads.

**Option B — Regenerate with a corrected prompt** (when you prefer a clean start):
```bash
python3 /opt/data/scripts/gemini-generate-image.py \
  "Create a baby shower invitation, Bombay Brunch theme, Priyanka only, warm message instead of blank fields..." \
  --output /tmp/v2.jpg
```

**Pitfall — wrong conclusion from first test (10 Jun 2026):** I originally concluded Gemini cannot edit in-thread because `gemini-image-download.py` returned the same MD5 as the original. The actual cause: the script iterated images FORWARD, picking the FIRST `img[alt*="AI"]` (the original, still in DOM). The modified image was the SECOND one at a CDN URL. **Fix:** Script was patched to iterate images in reverse so it always picks the most recent AI-generated image.

**Pitfall — response-read timeout:** `gemini-response-read.py` originally timed out even after the image was generated. Root cause: it checked `!document.body.innerText.includes('Creating your image')` to detect completion, but that text persists in the DOM permanently. Fix: check for `img[alt*="AI"]` presence directly instead.

**Pitfall — wrong conversation thread:** When multiple Gemini conversations exist (original thread + fresh /images page), scripts that find the first `gemini.google.com` page target (`get_gemini_ws()`) may connect to the wrong thread. Always verify which conversation you're in before downloading: check `document.body.innerText.substring(0,500)` for the conversation title, or use `Target.getTargets` to confirm the URL contains `/images` for fresh generations.

## Script Import Fix

All gemini scripts import `from gemini_utils import ...` but the file was named `gemini-utils.py` (hyphen). Python rejects hyphens in module names — `import gemini-utils` fails immediately with `ModuleNotFoundError`.

**Fix:** `mv /opt/data/scripts/gemini-utils.py /opt/data/scripts/gemini_utils.py`

Fixed on 10 Jun 2026. If scripts break again with the same error, check the filename hasn't reverted.

## Design Principles

### Adaptive DOM Probing

The scripts discover page structure dynamically rather than assuming specific CSS class names, component tags, or data attributes. This is the single most important design choice for surviving Gemini's frequent frontend updates.

**The pattern:**
1. Find → Scan all elements for the best candidate by behavior (scrollable container, chat-like content)
2. Try → Multiple strategies with fallbacks (class patterns → text patterns → container children)
3. Filter → By content/position/size, not class names
4. Verify → Check that what you found looks right

**If a strategy returns 0 results, it silently falls through to the next.** No breakage — just degraded specificity.

**What this survives:** CSS class name changes, component tag changes, image delivery format changes, layout restructuring.

**When a Gemini redesign breaks scripts:**
1. Run the scripts — they report which strategy they used (`"on": "class_patterns"` or `"user_message_patterns"` or `"container_children"`)
2. If they fell through to a less specific strategy, results may be less accurate
3. Update the fast-path class patterns to re-enable the best strategy
4. Do NOT hardcode new selectors — add them to the multi-strategy array so future changes degrade gracefully
