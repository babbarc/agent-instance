---
name: recaptcha-solver
description: "Solve reCAPTCHA v2 image challenges — user-driven (interactive), vision-model (cron), or pixel-cluster fallback (distinct colours only)"
annotation: "reCAPTCHA v2: user-driven interactive solve via browser"
version: 11.0.0
author: Joy
---

# reCAPTCHA Solver

## Steps

### Part A — Trigger or recover
1. Find anchor iframe via `Target.getTargets`. It's the recaptcha.net/anchor... URL.
2. Run `document.querySelector('.recaptcha-checkbox').click()` on it. Wait 5-8s.
3. If the challenge was already active or you're recovering from expiry — skip to Part B.

### Part B — Read prompt + size
4. Find bframe iframe via `Target.getTargets`. It's the recaptcha.net/bframe... URL.
5. On bframe: read `document.body.innerText`. Identify the object word.
6. On bframe: run `document.querySelectorAll('.rc-imageselect-tile').length` to get grid size:
   - 9 tiles → 3×3 (standard)
   - 16 tiles → 4×4 (common on TLScontact)
   - 6 tiles → 3×2 or 2×3
   - **32+ tiles → TRUE CAROUSEL TYPE.** Run `document.querySelector('.rc-imageselect-table-44, .rc-imageselect-table-33, .rc-imageselect-carousel')` and check for `rc-imageselect-carousel-leaving-left` class. True carousels have 32+ tiles because they slide through multiple image frames horizontally. The actual grid is still 4×4 (if `-44`) or 3×3 (if `-33`), but overlapping tiles produce duplicate bounding rects.
   - 🚩 **CRITICAL: Do NOT confuse CSS sprite technique with carousel mode.** ALL reCAPTCHA grids (standard and carousel) use `left:` CSS offsets on `img` elements to slice a single composite sprite. This is the standard sprite-slicing technique — every tile's img has a `left:` value like `0%`, `-100%`, `-200%` etc. indicating which portion of the sprite it displays. A standard 4×4 grid (16 tiles) will always have `left:` offsets on its img elements, and ALL 16 tiles have unique, non-overlapping getBoundingClientRect positions — each tile occupies its own cell in the grid. Only proceed to carousel-specific handling when you have VERIFIED 32+ tiles OR the `rc-imageselect-carousel-leaving-left` CSS class.

7. **If carousel:** identify which tiles are in the current "frame" (visible at `left: 0%`):
   ```javascript
   var tiles = document.querySelectorAll('.rc-imageselect-tile');
   var visible = [...tiles].map(function(t,i){
     var img = t.querySelector('img');
     var left = img ? img.style.left : '0%';
     return {idx:i, left:left, selected:t.classList.contains('rc-imageselect-tileselected')};
   }).filter(function(t){ return t.left === '0%'; });
   JSON.stringify(visible);
   ```
   These are the tiles currently displayed. Only these can be selected. Other tiles have left: -100%, -200%, etc. and are off-screen (previous/next carousel frames).
   
   **Carousel tile indexing (32+ tiles only):** getBoundingClientRect positions CAN overlap — tiles from different carousel frames at `left: 0%`, `-100%`, `-200%` stack on top of each other. Only tiles where `img.style.left === '0%'` are the current visible frame. Filter by this before cropping. For standard grids (9 or 16 tiles), each tile has its own unique position — no filtering needed.

### Part C — Make bframe visible (critical — bframe is often off-screen)
7. The bframe iframe is positioned at `top: -9999px` by reCAPTCHA (hidden above the viewport). It will NOT appear in a standard viewport screenshot. You must make it visible first.

8. **Check and reposition the bframe.** On the **main page** (NOT the bframe target), run:
   ```javascript
   var all = document.querySelectorAll('iframe');
   var results = [];
   for (var i = 0; i < all.length; i++) {
     var b = all[i].getBoundingClientRect();
     if (b.width > 100) {
       results.push({
         idx: i, left: b.left, top: b.top, width: b.width, height: b.height,
         src: (all[i].src || '').slice(0, 80)
       });
     }
   }
   JSON.stringify(results);
   ```
   The bframe is the one with `width=400, height=580` and typically `top` is a large negative value (e.g. `-9999`).

9. **Move the bframe to a visible position** (if it was off-screen):
   ```javascript
   var bframe = document.querySelector('iframe[src*="bframe"]');
   if (bframe) {
     bframe.style.position = 'fixed';
     bframe.style.top = '200px';
     bframe.style.left = '800px';
     bframe.style.zIndex = '99999';
   }
   'bframe moved to visible: ' + bframe.getBoundingClientRect().top;
   ```
   This makes the bframe render at (800, 200) in the viewport so it will appear in screenshots.

### Part D — Capture screenshot + crop to bframe
10. `browser_vision(question="")` — fails but saves screenshot. The screenshot IS saved at the returned path. Copy it to /tmp/.
    - **Important:** If the bframe was off-screen and you didn't reposition it, the screenshot won't contain the bframe. Always verify bframe visibility first.
    - **browser_vision failure message:** On DeepSeek and other non-vision models, the error reads `unknown variant 'image_url', expected 'text'`. This is expected — the screenshot is still captured.
11. **Crop the bframe from the full screenshot** using the position you confirmed in step 8/9:
    ```python
    from PIL import Image
    full = Image.open('/tmp/recaptcha_page.png')
    bframe_only = full.crop((800, 200, 800+400, 200+580))  # adjust to actual bframe position
    bframe_only.save('/tmp/bframe.png')
    ```
12. **Get precise tile positions from the bframe DOM** — run this on the **bframe target**:
    ```javascript
    var tiles = document.querySelectorAll('.rc-imageselect-tile');
    JSON.stringify([...tiles].map(function(t,i){
      var b=t.getBoundingClientRect();
      return {idx:i,left:b.left,top:b.top,width:b.width,height:b.height};
    }))
    ```
    Returns exact pixel coords (e.g. 97x97px tiles in a 4×4 grid starting at left=6, top=124-128). These are relative to the bframe viewport, matching the cropped bframe image.
    
    **For true carousels (32+ tiles):** getBoundingClientRect returns overlapping positions for tiles at different `left:` offsets (they stack). Only use tiles where the img.style.left is '0%' — those are the visible ones. The others share bounding rects but have scrolled-off content. For standard grids (9 or 16 tiles), ignore left offsets — every tile has its own position and is independently valid.

13. **Crop each tile from the bframe screenshot** using those coordinates:
    ```python
    from PIL import Image
    bframe = Image.open('/tmp/bframe.png')
    tile = bframe.crop((6, 126, 6+97, 126+97))  # left, top, right, bottom — use YOUR coords
    tile.save('/tmp/tile_0.png')
    ```
    Save all visible tiles to `/tmp/tile_N.png`. See `references/tile-extraction.md` for the full script.

### Part D — User-driven solving (interactive sessions)

For interactive sessions where a human is present:

1. Capture a screenshot via `browser_vision(question="")` — it fails with `unknown variant 'image_url'` on non-vision models but the screenshot IS saved
2. Copy the screenshot path from the error's `screenshot_path` field
3. Send to the user via `send_message` with `MEDIA:<path>` included, along with:
   - The exact challenge prompt from `document.body.innerText` on the bframe
   - The grid dimensions (3×3 or 4×4 based on `.rc-imageselect-tile.length`)
   - The VERBATIM instruction text — not just the object word
4. Wait for the user's response with tile numbers
5. Click the tiles and VERIFY button as instructed

### Part E — Automated/cron solving (no user present)

When running as a cron job or autonomous subagent with NO user present to respond:

**There is NO viable automated reCAPTCHA solving path without a vision-capable model.** Options ordered by viability:

1. **Cron model override (best)** — Create the cron job with a `model` override pointing to a vision-capable model. The vision-capable agent can then use `vision_analyze` directly on the cropped tiles or bframe composite.

2. **Subagent with vision toolset (fallback)** — If the parent model is non-vision but a vision tool is available via subagent:
   ```
   delegate_task(goal='Analyze tiles at /tmp/tile_N.png for [object]...', toolsets=['vision','terminal','file'])
   ```
   ⚠️ Only works if a vision-capable model serves the vision tool.

3. **Fail fast** — If neither option is available, do NOT waste tool calls on pixel-analysis guesstimation. State clearly: "reCAPTCHA could not be solved — this cron job needs a vision-capable model override." The ~2-minute challenge window expires before any non-vision approach reaches reliable accuracy.

**Why pixel-analysis alone is insufficient:** Colour-cluster analysis (`references/pixel-color-fallback.md`) works for distinctly-coloured objects (red fire hydrants, yellow traffic lights) but fails for non-colour objects like crosswalks, staircases, and bridges — ~50% of common reCAPTCHA challenges.

### Part F — Click + verify
13. Verify tile IDs in DOM: `document.querySelectorAll('.rc-imageselect-tile')` on bframe. Map: Claude N (1-indexed) → DOM N-1 (0-indexed).
14. Batch click: `[DOM_IDS].forEach(function(n){var el=document.getElementById(n+'');if(el)el.click();})`
15. Click verify: `document.getElementById('recaptcha-verify-button').click()`
16. Wait 3s. Read bframe.innerText again.
17. **Always re-query grid size after every round.** Run `document.querySelectorAll('.rc-imageselect-tile').length` — the grid may have changed (3×3 → 4×4 after "Please try again", or vice versa). Tile dimensions depend on grid size (3×3 ≈ 130×130px, 4×4 ≈ 97×97px).
18. New images appear → repeat from Part C step 7 (capture new screenshot).
19. Challenge expired → go back to Part A step 2 (re-trigger checkbox).
20. reCAPTCHA solved → continue to the main task.

### If there are none (skip/disabled flow)

When the challenge text says **"If there are none, click skip"** and vision analysis reports NO tiles match the object:

**The verify button IS disabled.** Its text changes to "Skip" but it has the CSS class `rc-button-default-disabled` — clicking it programmatically has no effect. This is reCAPTCHA's design: you MUST select at least one tile to enable the button, even when the correct answer is zero tiles.

**What to do when ALL tiles are NO and the verify button is disabled:**
1. Click the reload button: `document.getElementById('recaptcha-reload-button').click()`
2. Wait 5-7 seconds for a new challenge to load
3. Read the bframe innerText to identify the new object
4. Start fresh from Part B step 5

This costs one of the ~2 minute window but is the only working path. The reload button cycles through available challenge types and may present a different object that actually appears in the grid.

## Dual-solving mode (user + pixel hint)

When running in interactive mode where the user wants to validate results:

1. Capture the bframe screenshot
2. **Send to user** — send the screenshot to the user via `send_message` with `MEDIA:` in the message. Include the grid dimensions and the exact prompt text
3. Optionally run colour-cluster analysis (`references/pixel-color-fallback.md`) as a cross-check if the target has a distinctive colour
4. Wait for the user's answer — their judgement is final

## reCAPTCHA prompt nuance — CRITICAL

The reCAPTCHA instruction text matters more than the object word alone. Two different prompt patterns exist:

- **"Select all squares WITH [object]"** — click tiles where the object appears anywhere in the tile. Even a partial view, a small corner, or the object in the background counts.
- **"Select all squares OCCUPIED BY [object]"** — click only tiles where the object is the **primary subject** — it fills most of the tile, is in focus, and is clearly the main thing in the image. Background appearances, small corners, or blurry partial objects do NOT count.

The same prompt might also read **"Select all images with [object]"** (equivalent to "with") or **"Click verify once there are none left"** (standard boilerplate — ignore this).

**How to handle this:**
1. Always read the FULL prompt text from `document.body.innerText` on the bframe — don't just extract the object word
2. If the prompt says "with" — be generous: any tile that contains the object at all should be selected
3. If the prompt says "occupied by" — be strict: only tiles where the object is the clear main subject should be selected
4. Include the exact prompt wording when sending to the user for user-driven solving
5. If unsure after vision analysis, the dual-solving mode (user as second opinion) is the safest path

## Pitfalls
- **"Click verify once there are none left"** is standard boilerplate. It does NOT mean zero tiles. Ignore this text — read the object word from the line ABOVE it and proceed to select matching tiles.
- **"Please try again"** means round failed. Take new screenshot, repeat from Step 4. **IMPORTANT: Grid can escalate.** After "Please try again" on a 3×3 grid, reCAPTCHA may upgrade to a 4×4 grid (same object, harder layout). Always re-query grid size with `document.querySelectorAll('.rc-imageselect-tile').length` after every round — don't assume it stayed the same. Tile dimensions change: 3×3 = ~130×130px, 4×4 = ~97×97px.
- **"Please also check the new images"** means round passed. Take new screenshot, repeat.
- **"If there are none, click skip" is ambiguous.** On TLScontact, this text appears as **standard boilerplate on almost every 4×4 grid** — it does NOT mean the answer is zero. Always run vision analysis on the tiles first:
  - **Vision finds matches** → proceed normally (select tiles + verify). The "skip" text is just the button label, not an instruction.
  - **Vision says ALL tiles are NO** → this is genuine zero-match. The verify/Skip button IS disabled (`rc-button-default-disabled`). Use the reload button to get a fresh challenge. See "If there are none (skip/disabled flow)" section below.
- **"Skip" / "Get new challenge" button does NOT exist on many reCAPTCHA implementations** (including TLScontact). The reload button (`#recaptcha-reload-button`) is available instead — clicking it gives a fresh challenge with a new object. Use only as a last resort (costs one of the ~2 minute window).
- **Carousel challenges (32+ tiles only): tile count is not grid size.** A true carousel with 32+ `.rc-imageselect-tile` elements is still a standard 4×4 grid. The extra tiles are previous/next carousel frames that overlap at shared bounding rect positions. Only tiles with `img.style.left === '0%'` are visible in the current frame. Filter by this before cropping. For standard grids (9 or 16 tiles), ALL tiles have unique bounding rect positions — do not filter by left offsets.
- **Standard grids: all tile positions are independently valid.** A standard 4×4 reCAPTCHA (16 tiles, rc-imageselect-table-44) uses CSS sprite technique: each img element has a `left:` offset showing a different portion of a single composite image. This is NOT a carousel. Every tile occupies its own unique (left, top) position in the grid and getBoundingClientRect returns 16 distinct non-overlapping rects. Do NOT filter to `left: 0%` tiles — that will discard valid tiles.
- **Challenge expires in ~2 minutes total** across ALL rounds. Work fast. Take the next round's screenshot immediately after clicking verify. If the challenge expires mid-session (bframe shows expired state, anchor shows "Verification challenge expired. Check the checkbox again."):
  1. Find the anchor iframe target via Target.getTargets
  2. Run: `document.querySelector('.recaptcha-checkbox').click()` on it
  3. Wait 5-8 seconds for a new challenge to load in the bframe
  4. Read bframe.innerText — the challenge should have reset with a new object
|- **ALL tiles may contain non-blank content on some reCAPTCHA versions.** The `n_colors > 50` blank-detection heuristic works when ~70% of tiles are empty/background, but some challenges (especially 3×3 grids) display objects in every tile. All 9 tiles had 2700-3900 unique colors in one TLScontact session. The blank-detection fallback returns nothing useful in this case — you must use the color-cluster analysis in `references/pixel-color-fallback.md`.
|- **4×4 grids: tiles are smaller** — the smaller tile size reduces detail in user-driven solving. Verify tile content carefully.
||- **Never use canvas.drawImage to extract tiles (cross-origin taint).
|- **Check bframe visibility before screenshotting.** reCAPTCHA hides the bframe at `top: -9999px` (above viewport). A standard `browser_vision` viewport screenshot will NOT capture it. Use the bframe repositioning steps in Part C before capturing.
|- **Bframe may already be visible.** On some page layouts (e.g. TLScontact login page), the bframe is at a natural viewport position (~top: 280). Check first with the iframe position script; only reposition if `top < 0`.
|- **browser_vision always fails on non-vision models.** The screenshot IS saved regardless. Use it ONLY to save the screenshot — never expect analysis output. The DeepSeek model produces `unknown variant 'image_url', expected 'text'` — this is expected.
|- **Rate limits** — vision analysis may be rate-limited in heavy use. When this happens, fall back to the pixel-analysis approach in `references/tile-extraction.md`: crop tiles individually, measure color variance, and flag tiles that contain non-uniform image content (not blank/background). Tiles with actual image content have >50 unique colors across their pixels; blank/background tiles have <5.
|- **4×4 grids: run getBoundingClientRect on the bframe BEFORE cropping.** The tile dimensions vary between reCAPTCHA versions and page layouts. Guessing (75px, 87px, 97px) wastes attempts. Always get exact coords from the DOM.

## Objects reference
bus, voitures (cars), passages pour piétons (crosswalks), escaliers (stairs), motos (motorcycles), borne d'incendie (fire hydrant), feux de circulation (traffic lights), ponts (bridges), bicyclette/velo (bicycle), camion (truck)

## Reference files
- `references/tile-extraction.md` — Full scripts for cropping tiles from bframe screenshots + pixel-analysis fallback
- `references/tile-id-indexing.md` — 0-indexed vs 1-indexed tile ID mapping.
- `references/tool-call-limits.md` — Budget planning for cron-run CAPTCHA solving.
- `references/pixel-color-fallback.md` — Colour-cluster analysis for when vision analysis is unavailable AND all tiles have non-blank content. Uses cohesive colour-region detection (cluster ratio, aspect ratio) to identify objects like fire hydrants, traffic lights, etc.