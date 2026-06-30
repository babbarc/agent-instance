---
name: run-cdp-scripts
description: "Load when you need the CDP CLI scripts in /opt/data/scripts/ (cdp-eval, cdp-list-tabs, etc.) instead of writing raw websocket code. Cross-refs to use-cdp-protocol for CDP method documentation."
annotation: "CDP CLI scripts from /opt/data/scripts/ — reference guide"
version: 1.1.0
metadata:
  hermes:
    tags: [browser, cdp, automation, scripts]
    related_skills: [use-cdp-protocol, operate-browser, choose-web-tool]
---

# run-cdp-scripts — CDP CLI Scripts

**Load when you need to list tabs, evaluate JS, navigate, or screenshot via CLI tools** in `/opt/data/scripts/`. For the underlying CDP method reference (Runtime.evaluate params, Page.navigate, frame_id vs target_id), load `use-cdp-protocol` instead.

## Available Scripts

All in `/opt/data/scripts/`. STATUS:CODE convention on stdout.

### Browser introspection
```bash
python3 /opt/data/scripts/cdp-list-tabs.py                    # list all tabs
python3 /opt/data/scripts/cdp-list-tabs.py --verbose
python3 /opt/data/scripts/cdp-find-page.py --url "gemini"     # find by URL
python3 /opt/data/scripts/cdp-find-page.py --title "Bombay"   # find by title
python3 /opt/data/scripts/cdp-find-page.py                    # first page
```

### JS evaluation
```bash
python3 /opt/data/scripts/cdp-eval.py --page "gemini" --expr "document.title"
python3 /opt/data/scripts/cdp-eval.py --page "gemini" --async --expr "(async function(){ window._r=null; window._ready=false; window._r=await asyncWork(); window._ready=true; })()"
```

### Navigation & screenshots
```bash
python3 /opt/data/scripts/cdp-navigate.py --page "gemini" --url "https://..."
python3 /opt/data/scripts/cdp-screenshot.py --page "gemini" --output /tmp/shot.jpg
```

## Shared Module

`cdp_utils.py` provides: `discover_targets`, `find_page_by_url`, `find_page_by_title`, `find_first_page`, `get_ws_url`, `evaluate` (sync JS), `send_cdp` (CDP method + id match).

```python
sys.path.insert(0, '/opt/data/scripts')
import cdp_utils
evaluate = cdp_utils.evaluate
send_cdp = cdp_utils.send_cdp
discover_targets = cdp_utils.discover_targets
```

## Pitfalls

- **browser_navigate creates pages invisible to CDP scripts** — browser tools attach to wrong page target. Fix: call `browser_cdp(method='Target.getTargets')` to see all targets, use correct target_id.
- **Page target IDs are ephemeral** — always call Target.getTargets fresh before using a target_id.

## Script Boilerplate

```python
#!/usr/bin/env python3
import argparse, asyncio, json, sys; import websockets
sys.path.insert(0, '/opt/data/scripts'); import cdp_utils
evaluate = cdp_utils.evaluate; send_cdp = cdp_utils.send_cdp; discover_targets = cdp_utils.discover_targets
```
