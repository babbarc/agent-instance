# reCAPTCHA Tile ID Indexing

## Discovery (session 2026-05-25)

The reCAPTCHA bframe uses **0-indexed tile IDs** for its grid cells regardless of grid size. The anchor elements have sequential numeric IDs starting at 0.

## Grid sizes & ID ranges

| Grid | Tile count | DOM IDs |
|------|-----------|---------|
| 3×3  | 9         | 0–8     |
| 4×4  | 16        | 0–15    |
| 3×2  | 6         | 0–5     |
| 4×2  | 8         | 0–7     |

## Why this matters

Claude naturally numbers tiles from 1 (top-left) to N (bottom-right) when asked. If you use `document.getElementById` with Claude's numbers directly, you're clicking the wrong tiles.

## The mapping

Always subtract 1 from Claude's result:
```
Claude tile | DOM ID
   1        →   0
   2        →   1
   ...
   N        →   N-1
```

## Verification step

Before clicking, always verify the tile IDs with:
```javascript
var tiles = document.querySelectorAll('.rc-imageselect-tile');
JSON.stringify([...tiles].map(t => t.id));
```

The array length also confirms the grid size:
- 9 items → 3×3
- 16 items → 4×4 (common on TLScontact)
- 6 items → 3×2 or 2×3

## Batched click approach

Instead of clicking one tile at a time (wastes tool calls), batch with:
```javascript
[TILE_NUMBERS].forEach(function(n){
  var el = document.getElementById(n+'');
  if(el) el.click();
})
```

Where TILE_NUMBERS is the array of DOM IDs (Claude numbers minus 1).
