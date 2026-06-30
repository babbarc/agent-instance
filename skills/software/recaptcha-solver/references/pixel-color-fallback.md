# Pixel Color-Cluster Analysis for reCAPTCHA

When Claude CLI is rate-limited and basic blank-detection (`n_colors > 50`) fails because every tile has content, use **color-cluster analysis** to identify tiles containing a specific coloured object (fire hydrant, traffic light, bus, etc.).

## Principle

Objects with distinctive colours produce cohesive single-colour clusters. Background noise produces scattered pixels. By measuring **cluster density** (largest contiguous same-colour region ÷ total same-colour pixels), we distinguish real objects from noise.

## Generic fallback script

```python
from PIL import Image

def analyze_color_clusters(path, r_min=100, g_max=120, b_max=120, r_boost=1.3):
    """
    Analyze image for cohesive clusters of a target colour.
    
    Parameters:
      path: tile image path
      r_min, g_max, b_max: colour threshold (default = reddish)
      r_boost: minimum r/(g or b) ratio for a pixel to count
    
    Returns:
      total_colored: total pixels matching colour
      largest_cluster: size of largest contiguous same-colour region
      cluster_ratio: largest_cluster / total_colored (0-1, 1 = fully cohesive)
      aspect: width/height ratio of bounding box (for shape classification)
    """
    img = Image.open(path).convert('RGB')
    w, h = img.width, img.height
    
    # Create binary colour mask
    mask = [[0]*w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            r, g, b = img.getpixel((x, y))
            if r > r_min and r > g * r_boost and r > b * r_boost and g < g_max and b < b_max:
                mask[y][x] = 1
    
    # Flood fill to find largest connected component
    visited = set()
    largest = []
    for y in range(h):
        for x in range(w):
            if mask[y][x] and (x, y) not in visited:
                cluster = []
                stack = [(x, y)]
                while stack:
                    cx, cy = stack.pop()
                    if (cx, cy) in visited:
                        continue
                    visited.add((cx, cy))
                    cluster.append((cx, cy))
                    for nx, ny in [(cx-1,cy), (cx+1,cy), (cx,cy-1), (cx,cy+1)]:
                        if 0 <= nx < w and 0 <= ny < h and mask[ny][nx] and (nx, ny) not in visited:
                            stack.append((nx, ny))
                if len(cluster) > len(largest):
                    largest = cluster
    
    total_colored = sum(sum(row) for row in mask)
    if total_colored == 0 or not largest:
        return 0, 0, 0, 0
    
    cluster_ratio = len(largest) / total_colored
    min_x = min(p[0] for p in largest)
    max_x = max(p[0] for p in largest)
    min_y = min(p[1] for p in largest)
    max_y = max(p[1] for p in largest)
    aspect = (max_x - min_x + 1) / max((max_y - min_y + 1), 1)
    
    return total_colored, len(largest), cluster_ratio, aspect
```

## Colour thresholds by object

| Object | Target colour | r_min | g_max | b_max | r_boost | Shape hints |
|--------|-------------|-------|-------|-------|---------|-------------|
| Fire hydrant | Bright red | 120 | 100 | 100 | 1.2 | Vertical (aspect < 0.6), cluster_ratio > 0.8 |
| Traffic light | Yellow/red | 150 | 120 | 100 | 1.3 | Small cluster, vertical column |
| Bus | Red, blue, or green | 120 | varied | varied | 1.2 | Large, aspect ~0.5-1.2 |
| Bicycle | Varied | 60 | 60 | 60 | 1.0 | Diffuse, low cluster_ratio |
| Car | Varied | 80 | 80 | 80 | 1.0 | Moderate size, low cluster_ratio |
| Motorcycle | Varied | 80 | 80 | 80 | 1.0 | Moderate size, low cluster_ratio |

For non-red objects, lower the thresholds and adjust. The key metric is always **cluster_ratio** — a value > 0.8 means the colour forms one cohesive object; < 0.5 means it's scattered noise or multiple small objects.

## Real-world example (TLScontact, fire hydrant, 3×3 grid)

Tiles in round 1 (all had content — blank-detection was useless):
```
Tile  | Total red | Largest cluster | Cluster ratio | Shape       | Verdict
------|-----------|-----------------|---------------|-------------|--------
Tile 0| 168       | 65              | 0.39          | vertical    | NO (scattered)
Tile 1| 9         | 5               | 0.56          | tiny        | NO
Tile 2| 1101      | 1095            | 0.99          | vertical    | YES ← hydrant
Tile 3| 1         | 1               | 1.00          | single px   | NO
Tile 4| 8         | 3               | 0.38          | tiny        | NO
Tile 5| 318       | 130             | 0.41          | square      | NO (scattered)
Tile 6| 0         | 0               | 0             | -           | NO
Tile 7| 49        | 45              | 0.92          | square      | POSSIBLE (small)
Tile 8| 39        | 15              | 0.38          | tiny        | NO
```

Tile 2 was the clear winner: 1101 red pixels, 99% in one cohesive cluster, tall vertical shape (aspect 0.31) — perfectly matching a fire hydrant.

## When to use this

1. Claude CLI is rate-limited (common — hourly reset)
2. Basic blank-detection shows all tiles have > 50 unique colours
3. The target object has a distinctive colour (red, yellow, blue)
4. You cannot use `browser_vision` (non-vision model)

## When this does NOT work

- Object has no distinctive colour (crosswalk, staircase, bridge, bicycle — see real-world failure below)
- Object is multi-coloured with no dominant hue
- Lighting/compression reduces colour distinctiveness
- Multiple objects in the same tile share the target colour

## Real-world failure: crosswalk detection (2026-05-26 session)

Crosswalks ("passages pour piétons") have NO distinctive colour — they are white stripes on dark grey asphalt. All automated approaches FAILED:

| Method | Attempt | Result |
|--------|---------|--------|
| Unique colour count | All 9 tiles had 99-109 unique colours | Cannot distinguish |
| White/dark ratio | Ranged 6-51% white, 1-66% dark | Overlapping ranges |
| FFT periodic stripe detection | Dominant freq=0.008 for ALL tiles | No periodic signal |
| Edge energy (horizontal vs vertical) | H/V ratios 0.95-1.72 | No separation |
| Row brightness transitions | 6-12 transitions across all tiles | All ambiguous |
| Subagent with `toolsets=['vision']` | DeepSeek model has no vision capability | `image_url` not supported |

**Verdict:** Crosswalk detection via pixel analysis is impossible. Only a vision-capable model or a human can solve crosswalk reCAPTCHA challenges. The same applies to staircases, bridges, and any object lacking a distinctive colour signature (see the "Colour thresholds by object" table above — every entry requires a specific hue).
