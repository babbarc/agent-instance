# Hermes-Browser Session Persistence

## Architecture

```
hermes (container)
  └── browser-proxy (container, /proxy.py)
        └── hermes-browser (container, google-chrome-stable --headless=new)
              └── hermes-browser-data (podman volume)
                    └── Chrome profile at /home/chrome/devtools-profile/ (non-default — Chrome 148+ blocks DevTools on default path)
                          ├── Default/Cookies       ← Google auth cookies
                          ├── Default/Web Data      ← localStorage
                          └── downloads/            ← downloaded images
```

## How Session Persists

The `hermes-browser-data` named volume is mounted at Chrome's profile path:

| Container | Volume Mount |
|---|---|
| `hermes-browser` | `hermes-browser-data` → `/home/chrome/devtools-profile` |
| `hermes` | `hermes-browser-data` → `/opt/data/home/chrome-downloads` |

Chrome runs with:
- `--user-data-dir=/home/chrome/devtools-profile` — non-default path (Chrome 148+ blocks DevTools on `~/.config/google-chrome`)
- `--download-default-directory=/home/chrome/devtools-profile/downloads` — downloads land on the volume

## What Survives

| Event | Session? | 
|---|---|
| Tab close | ✅ Yes |
| 1h idle timeout (browser stops) | ✅ Yes |
| `podman stop → podman start` | ✅ Yes |
| `podman rm -f → podman run` (proxy restart) | ✅ Yes (volume persists) |
| Server reboot | ✅ Yes (volume persists) |
| Full container image rebuild | ✅ Yes (volume separate from image) |

## What the Proxy Does

`browser-proxy.py` (in `hermes-agent` repo) manages the container:

- **Idle timeout:** 3600s (1h) after last CDP activity → `podman stop` browser
- **On demand:** New CDP connection → `podman start` browser (same container, same volume)
- **Fresh start:** On proxy restart → `podman rm -f hermes-browser` + `podman run -d` with volume mount

The `--user-data-dir` flag + volume mount together ensure the Chrome profile survives all paths.

## Why No Script Cookie Logic

Earlier approaches used `Network.getAllCookies`/`Network.setCookies` to save/load auth cookies as JSON files. This was abandoned because:
- The volume approach is simpler (Chrome handles its own cookie store)
- No files to keep in sync
- No CDP `Network.enable()` footgun to trip over
- Works for **all** browser state (cookies, localStorage, extensions, cache), not just cookies

## Checking the Setup

```bash
# Verify volume mount
podman inspect hermes-browser --format '{{json .Mounts}}' | python3 -m json.tool

# Check Chrome flags
podman exec hermes-browser ps aux | grep chrome

# Verify profile exists on volume
podman exec hermes-browser ls /home/chrome/devtools-profile/Default/Cookies

# Log into Gemini once
python3 /opt/data/scripts/gemini-google-login.py
```

## Related

- `hermes-infrastructure` skill's `references/browser-proxy-cookie-persistence.md` — proxy-level details
- `gemini-web-images` skill — how to use the browser for image generation
