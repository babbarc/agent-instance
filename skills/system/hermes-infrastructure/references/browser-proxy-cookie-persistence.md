# Browser-Proxy Cookie Persistence & Shared Volume

## The Problem

Browser sessions (Google auth, Gemini login, etc.) are frequently lost — user must re-authenticate (phone prompt, TOTP) every time they interact with the browser. Plus, the hermes agent needs to read downloaded files from the browser but gets permission denied.

## Architecture

```
hermes (container, port 3333 exposed)
  └── browser-proxy (container, /proxy.py)
        └── hermes-browser (container, google-chrome-stable --headless=new)
              └── Chrome profile at hermes-browser-data volume
```

The `browser-proxy` manages the `hermes-browser` container lifecycle:
- **Idle timeout:** `IDLE_TIMEOUT = 3600` seconds (1 hour). After 1h of no CDP activity, `podman stop -t 5 hermes-browser` is called.
- **On-demand restart:** New CDP connection → `podman start hermes-browser`. If start fails → `podman rm -f` + `podman run -d` (fresh container).
- **Startup:** Proxy always does `podman rm -f --ignore hermes-browser` on its own startup, so browser container is recreated on proxy restart.
- **Persistent volume:** `hermes-browser-data` mounted at `/home/chrome/devtools-profile` (the `--user-data-dir`). Also mounted on the hermes container at `~/chrome-downloads/` for download sharing.

## Root Cause (Historical)

Chrome headless mode (`--headless=new`) **without** `--user-data-dir` creates a **new temporary profile** at `/tmp/com.google.Chrome.scoped_dir.*/` every time the process starts. Each `scoped_dir.*` is a completely fresh profile.

**Fixed** by adding `--user-data-dir=/home/chrome/devtools-profile` and mounting a persistent volume there. The volume alone persists the full Chrome profile (cookies, sessions, downloads) across container stop/start/rm/run.

## Volume Persistence Is Sufficient — No Script-Level Cookie Save Needed

Google auth cookies (SID, HSID, APISID, SAPISID, __Secure-1PSID, __Secure-3PSID) all have `session: false` and concrete multi-year expiry dates. Chrome writes them to `Default/Cookies` SQLite database on the volume, and reads them back on restart. **Script-level cookie save/restore (`save_cookies()` / `try_cookie_restore()`) is redundant.** The volume handles everything.

If you're tempted to add CDP-based cookie save/restore: verify first. Check `has_expires` on the cookies — if they're persistent, the volume is enough.

## Shared Volume Permission Issue: UID Namespace Mismatch

The `hermes-browser-data` volume is mounted on the hermes container at `~/chrome-downloads/` so the agent can read downloaded files. Chrome creates its profile with `0700` permissions owned by uid 999 (chrome user). The hermes agent runs as uid 1003 and gets permission denied.

### Why ACLs Don't Work Across Containers

Both containers use rootless podman with **different UID namespace mappings**:

| Context | UID mapping |
|---|---|
| Browser container | `0→1003`, `1→362144`, `2→362145`, ... |
| Hermes container | `0→1`, `1003→0`, `1004→1004`, ... |

When `setfacl -m u:1003:rx` runs inside the browser container, the kernel stores the ACL for **host UID 363146** (browser-container-uid 1003 remapped through the browser's namespace). When the hermes agent accesses the file, the kernel looks for an ACL matching **host UID 0** (hermes-container-uid 1003 remapped through hermes's namespace → root on host). No match → ACL is silently ignored.

**Diagnose:**

```bash
# Check UID mappings
podman exec hermes-browser cat /proc/self/uid_map
cat /proc/self/uid_map

# Check file ownership
stat -c '%u %g %a %A' ~/chrome-downloads/Default/
# 999 999 750 drwxr-x---  ← group-readable but hermes isn't in group 999
```

### Correct Fix: World-Readable Download Directory

Don't fight namespace isolation. Create a dedicated world-accessible download directory:

```bash
mkdir -p /home/chrome/devtools-profile/shared
chmod 0777 /home/chrome/devtools-profile/shared
```

Set Chrome's download flag in `browser-proxy.py`:
```
--download-default-dir=/home/chrome/devtools-profile/shared
```

The volume root (`../../../_data/`) is 755 world-readable. A `777` subdirectory is accessible from any container regardless of UID namespace. No ACLs, no namespace arithmetic.

**Entrypoint (`docker-entrypoint-browser.sh`):**

```bash
mkdir -p /home/chrome/devtools-profile/shared
chmod 0777 /home/chrome/devtools-profile/shared
```

## Diagnosing Session State

### Check if cookies exist in the browser store

```python
import json, urllib.request, websockets.sync.client

targets = json.loads(urllib.request.urlopen('http://localhost:3333/json').read())
page = [t for t in targets if t.get('type') == 'page'][0]
ws = websockets.sync.client.connect(page['webSocketDebuggerUrl'])

# CRITICAL: Enable Network domain FIRST
ws.send(json.dumps({'id': 1, 'method': 'Network.enable', 'params': {}}))
ws.recv()

# Now get cookies
ws.send(json.dumps({'id': 2, 'method': 'Network.getAllCookies', 'params': {}}))
resp = json.loads(ws.recv())
cookies = resp.get('result', {}).get('cookies', [])
print(f"Cookie count: {len(cookies)}")
```

**Without `Network.enable()` first, `Network.getAllCookies()` returns an empty array — no error, no warning.** This is a CDP protocol footgun.

## Files changed

- `browser-proxy.py` — `-v` mount, `--user-data-dir`, `--download-default-directory` flags, `IDLE_TIMEOUT=3600`
- `hermes.container` — `Volume=hermes-browser-data:/opt/data/home/chrome-downloads`
- `Containerfile.browser` — `apt-get install -y acl` (may not be needed if using chmod approach instead)
- `docker-entrypoint-browser.sh` — `mkdir -p shared && chmod 0777` (or `setfacl` if same-namespace)

## References

- `browser-proxy.py` in the hermes-agent repo — the actual proxy implementation
- `hermes.container` — volume mount where browser data is surfaced to the agent
- `browser-cdp-protocol` skill — CDP method reference, Network.enable requirement
