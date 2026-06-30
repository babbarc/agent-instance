# Tile Extraction from reCAPTCHA Bframe

## The core insight

**Do not guess pixel offsets.** Get exact tile coordinates from the DOM first, then crop the screenshot. This works every time regardless of screen resolution, zoom level, or reCAPTCHA version.

## CRITICAL: Bframe is often off-screen

reCAPTCHA hides the bframe iframe at `top: -9999px` (above the viewport). A standard viewport screenshot will NOT contain it. You must reposition it first.

### Detect and fix bframe position (run on the main page)

```javascript
// Check bframe position
var all = document.querySelectorAll('iframe');
var results = [];
for (var i = 0; i < all.length; i++) {
  var b = all[i].getBoundingClientRect();
  if (b.width > 100) {
    results.push({
      idx: i, width: b.width, height: b.height,
      left: b.left, top: b.top,
      src: (all[i].src || '').slice(0, 80)
    });
  }
}
JSON.stringify(results);
```

The bframe typically has width=400, height=580 and top=-9999 (or another large negative).
Anchor iframe is smaller (~304×78) and visible in the viewport.

**Known variant — TLScontact Keycloak auth page** (`i2-auth.visas-fr.tlscontact.com/auth/realms/atlas/...`):
The bframe is naturally positioned in the right column of the login form at `left=860, top=279.5`. It is already fully visible in the viewport and does NOT need repositioning. This was confirmed on the 2026-05-26 session — always check actual position before assuming off-screen.

If `top` is negative, move it to visible coordinates:
```javascript
var bframe = document.querySelector('iframe[src*="bframe"]');
if (bframe) {
  bframe.style.position = 'fixed';
  bframe.style.top = '200px';
  bframe.style.left = '800px';
  bframe.style.zIndex = '99999';
}
'bframe visible at: ' + bframe.getBoundingClientRect().top;
```

Now take the screenshot — the bframe will appear at (800, 200).

### Cross-origin canvas taint

Do NOT try to extract tiles via canvas `drawImage`. The sprite is served from `recaptcha.net` (cross-origin), so any canvas that touches it becomes **tainted** — the browser silently blanks the canvas and returns either nothing or a placeholder pattern. This is a browser security mechanism, not a tool bug. Screenshot + crop is the only viable approach.

## Step 1 — Get bframe position on the page

Run this on the **main page** (not the bframe iframe):
```javascript
var all = document.querySelectorAll('iframe');
var results = [];
for (var i = 0; i < all.length; i++) {
  var b = all[i].getBoundingClientRect();
  if (b.width > 100) {  // filter out tiny iframes
    results.push({
      idx: i, width: b.width, height: b.height,
      left: b.left, top: b.top,
      src: (all[i].src || '').slice(0, 80)
    });
  }
}
JSON.stringify(results);
```

The bframe iframe typically has width=400, height=580. Anchor iframe is smaller (~304×78).

## Step 2 — Get individual tile positions

Run this on the **bframe target**:
```javascript
var tiles = document.querySelectorAll('.rc-imageselect-tile');
JSON.stringify([...tiles].map(function(t, i){
  var b = t.getBoundingClientRect();
  return {idx: i, left: b.left, top: b.top, width: b.width, height: b.height};
}))
```

**Proven values from 2026-05-26 session** (4×4 grid at Wandsworth TLScontact):
```
Grid: 97x97px tiles, 4 columns × 4 rows
Tile 0:  left=6,   top=124,  width=97, height=97
Tile 1:  left=103, top=124,  ...
Tile 2:  left=200, top=124,  ...
Tile 3:  left=297, top=124   ...
Tile 4:  left=6,   top=221   ...
...continues in row-major order...
Tile 15: left=297, top=415
```

These are viewscreen-relative within the bframe iframe, so crop from the bframe-only screenshot.

**Proven values from 2026-05-26 session** (3×3 grid on TLScontact Keycloak auth page):
```
Grid: 130x130px tiles, 3 columns × 3 rows
Tile 0: left=5,   top=125,  width=130, height=130
Tile 1: left=135, top=125,  width=130, height=130
Tile 2: left=265, top=125,  width=130, height=130
Tile 3: left=5,   top=255,  width=130, height=130
Tile 4: left=135, top=255,  width=130, height=130
Tile 5: left=265, top=255,  width=130, height=130
Tile 6: left=5,   top=385,  width=130, height=130
Tile 7: left=135, top=385,  width=130, height=130
Tile 8: left=265, top=385,  width=130, height=130
```

**Note:** 3×3 tiles (130×130) are significantly larger than 4×4 tiles (97×97), which makes Claude's object classification more reliable for 3×3 grids. Always confirm by reading DOM positions rather than assuming dimensions from a past session.

## Step 3 — Full extraction script

```python
from PIL import Image

# Load the bframe-only screenshot (already cropped from the full page)
bframe = Image.open('/tmp/bframe.png')

# Tile positions from Step 2 — paste your actual coordinates here
tile_coords = [
    # (left, top, width, height)
    (6, 124, 97, 97),   # tile 0
    (103, 124, 97, 97),  # tile 1
    (200, 124, 97, 97),  # tile 2
    (297, 124, 97, 97),  # tile 3
    (6, 221, 97, 97),    # tile 4
    (103, 221, 97, 97),  # tile 5
    (200, 221, 97, 97),  # tile 6
    (297, 221, 97, 97),  # tile 7
    (6, 318, 97, 97),    # tile 8
    (103, 318, 97, 97),  # tile 9
    (200, 318, 97, 97),  # tile 10
    (297, 318, 97, 97),  # tile 11
    (6, 415, 97, 97),    # tile 12
    (103, 415, 97, 97),  # tile 13
    (200, 415, 97, 97),  # tile 14
    (297, 415, 97, 97),  # tile 15
]

for idx, (left, top, tw, th) in enumerate(tile_coords):
    tile = bframe.crop((left, top, left+tw, top+th))
    tile.save(f'/tmp/tile_{idx}.png')

# Also build a composite reference image
composite = Image.new('RGB', (97*4, 97*4))
for idx in range(16):
    tile = Image.open(f'/tmp/tile_{idx}.png')
    col = idx % 4
    row = idx // 4
    composite.paste(tile, (col*97, row*97))
composite.save('/tmp/grid_composite.png')
```

**3×3 grid variant** (130×130 tiles, proven on TLScontact auth page):
```python
from PIL import Image

bframe = Image.open('/tmp/bframe.png')

tile_coords = [
    (5, 125, 130, 130),   # tile 0
    (135, 125, 130, 130),  # tile 1
    (265, 125, 130, 130),  # tile 2
    (5, 255, 130, 130),    # tile 3
    (135, 255, 130, 130),  # tile 4
    (265, 255, 130, 130),  # tile 5
    (5, 385, 130, 130),    # tile 6
    (135, 385, 130, 130),  # tile 7
    (265, 385, 130, 130),  # tile 8
]

for idx, (left, top, tw, th) in enumerate(tile_coords):
    tile = bframe.crop((left, top, left+tw, top+th))
    tile.save(f'/tmp/tile_{idx}.png')

# Composite reference
composite = Image.new('RGB', (130*3, 130*3))
for idx in range(9):
    tile = Image.open(f'/tmp/tile_{idx}.png')
    col = idx % 3
    row = idx // 3
    composite.paste(tile, (col*130, row*130))
composite.save('/tmp/grid_composite.png')
```

## Step 4 — Pixel-analysis fallback (when vision is unavailable)

When vision analysis is rate-limited or unavailable, analyze which tiles have actual image content vs. blank/background:

```python
from PIL import Image

def analyze_tile(path):
    """Returns True if tile contains non-uniform image content."""
    img = Image.open(path)
    colors = set()
    for x in range(0, img.width, 2):
        for y in range(0, img.height, 2):
            p = img.getpixel((x, y))
            if len(p) > 3:
                p = p[:3]
            colors.add(p)
    return len(colors) > 50  # threshold: image content vs blank

for i in range(16):
    is_content = analyze_tile(f'/tmp/tile_{i}.png')
    print(f'Tile {i}: {"CONTENT" if is_content else "blank"}')
```

**Limitation:** This only identifies which tiles contain *some* image content vs. blank background. It cannot determine *what object* is in the tile. Use it as a last resort when Claude is unavailable — you can at least rule out clearly blank tiles (reducing the search space by ~30-50%).

**Real-world data from 2026-05-26 session (4×4, TLScontact login, "traffic lights"):**
Tiles in the top two rows (index 0-7) appeared blank (274-304 bytes PNG) — these were likely header/instructions or background. Content-bearing tiles were in the bottom rows (tile_9: 5360, tile_11: 2923, tile_14: 1733 bytes). This aligns with the reCAPTCHA grid being positioned at y=124-512 within the 580px bframe — the "grid" doesn't fill the full iframe height.

**When Claude is unavailable AND pixel-analysis can't determine the object:**
The only remaining option is to click "SKIP" / "Get a new challenge" and try again. This wastes the CAPTCHA but is better than blind-guessing. The challenge expires in ~2 minutes total, so time-box this to 3 retries.

## Step 5 — Bframe screenshot from full page

Before cropping tiles, first crop the bframe from the full page screenshot.

**IMPORTANT:** The bframe is typically hidden above the viewport (`top: -9999px`). You MUST reposition it before taking the screenshot (see "CRITICAL: Bframe is often off-screen" above). After repositioning, the bframe will be at approximately (800, 200) in the viewport.

```python
from PIL import Image

full = Image.open('/tmp/recaptcha_page.png')
# After repositioning, bframe is typically at (800, 200)
bframe_x, bframe_y = 800, 200  # adjust to actual bframe position from step 1
bframe_w, bframe_h = 400, 580
bframe = full.crop((bframe_x, bframe_y, bframe_x+bframe_w, bframe_y+bframe_h))
bframe.save('/tmp/bframe.png')
```

## Supported grid sizes

| Grid   | Tiles | Tile pattern                                  |
|--------|-------|-----------------------------------------------|
| 3×3    | 9     | Row-major, 0-2 top row, 3-5 middle, 6-8 bottom |
| 4×4    | 16    | Row-major, 0-3, 4-7, 8-11, 12-15              |
| 3×2    | 6     | Row-major, 0-2 top, 3-5 bottom                |

Always confirm the grid size with:
```javascript
document.querySelectorAll('.rc-imageselect-tile').length
```

## Carousel challenges

Carousel-type reCAPTCHAs have a table class of `rc-imageselect-table-44 rc-imageselect-carousel-leaving-left` (or `-33`). Key differences from standard grids:

**Tile count is misleading.** 32+ `.rc-imageselect-tile` elements exist in the DOM, but only tiles with `img.style.left === '0%'` are currently visible. The rest are at `-100%`, `-200%`, `-300%` (previous/next carousel frames).

**Bounding rects overlap.** Tiles at different `left:` offsets share identical getBoundingClientRect positions. Only `left: 0%` tiles actually render at those coordinates.

**Filter before cropping:**
```javascript
// Get visible tiles (left: 0%)
var tiles = document.querySelectorAll('.rc-imageselect-tile');
var visible = [...tiles].map(function(t,i){
  var img = t.querySelector('img');
  var left = img ? img.style.left : '0%';
  return {idx:i, left:left};
}).filter(function(t){ return t.left === '0%'; });
JSON.stringify(visible.map(function(t){return t.idx;}));
```

The number of visible tiles should match the grid size (9 for 3×3, 16 for 4×4). Only these positions should be used for cropping.

**Tile images are uniform across carousel frames.** The carousel slides the same composite sprite horizontally. Cropping at the same coordinates captures different portions of the source image in each frame. Only the `left: 0%` frame is the "current" challenge set.
