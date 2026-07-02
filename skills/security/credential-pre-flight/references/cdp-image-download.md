# CDP Image Download from SPA Web Apps

When a web app (like Gemini, ChatGPT, etc.) generates an image and serves it as a **blob URL** (`blob:https://...`), you cannot fetch it from outside the browser. Here's how to download it via CDP with zero exposure to LLM context.

## The Pattern

1. **Find the image element** in the DOM
2. **Draw it to a canvas** (converts blob → raster)
3. **Export as JPEG base64** via `canvas.toDataURL('image/jpeg', 0.92)`
4. **Store in a window variable** for chunked retrieval
5. **Read in chunks** via separate CDP `Runtime.evaluate` calls

## Step-by-Step

### Step 1: Identify the image

```javascript
// In CDP Runtime.evaluate:
document.querySelector('img[alt*="RSVP"], img[alt*="AI generated"]')
```

### Step 2: Convert to JPEG via canvas

```javascript
const img = document.querySelector('img[alt*="RSVP"]');
const c = document.createElement('canvas');
c.width = img.naturalWidth;
c.height = img.naturalHeight;
c.getContext('2d').drawImage(img, 0, 0);
const data = c.toDataURL('image/jpeg', 0.85);
window._imgB64 = data.split(',')[1];  // strip data:image/jpeg;base64, prefix
```

JPEG at 0.85 quality produces ~165KB base64 for a 708x1267 image (vs 1.3MB for PNG).

### Step 3: Read total size

```javascript
// Returns e.g. "165008"
window._imgB64.length
```

### Step 4: Read in chunks

```javascript
// Chunk 0-50000:
window._imgB64.substring(0, 50000)

// Chunk 50000-100000:
window._imgB64.substring(50000, 100000)

// Chunk 100000-end:
window._imgB64.substring(100000)
```

Each chunk goes through a separate `browser_cpd` call with `returnByValue: true`.

### Step 5: Reconstruct on disk

```python
import base64
chunks = [chunk1, chunk2, chunk3]
full_b64 = ''.join(chunks)
img_data = base64.b64decode(full_b64)
with open('/tmp/image.jpg', 'wb') as f:
    f.write(img_data)
```

## Alternative: Page.captureScreenshot with clip

If the image is fully rendered in the viewport, `Page.captureScreenshot` with a `clip` parameter can capture just the image area:

```json
{
  "method": "Page.captureScreenshot",
  "params": {
    "clip": {
      "x": 638, "y": 304,  // from getBoundingClientRect()
      "width": 708, "height": 1267,
      "scale": 2
    },
    "format": "png"
  }
}
```

**Caveat:** This is a screenshot, not the generated image. Quality may differ from the actual blob. Only use when the blob URL cannot be fetched (e.g., cross-origin restrictions, ephemeral blobs).

## Pitfalls

| Issue | Fix |
|-------|-----|
| `returnByValue` result is empty/truncated | Data too large. Use JPEG (not PNG) and/or lower quality |
| Blob URL is cross-origin | Use canvas approach (drawImage works for same-origin blobs) |
| Image not in DOM yet | Poll with `setTimeout` + check for `document.querySelector` |
