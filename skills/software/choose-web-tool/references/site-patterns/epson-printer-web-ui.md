# Epson Printer Web UI Navigation

## Summary

Epson network printers (ET-2750 Series and likely others) expose a web-based management interface. This reference covers navigation patterns for checking status, ink levels, and available vs unavailable maintenance actions.

## Access

```
http://<printer-ip>/
```

The landing page redirects to `/PRESENTATION/HTML/TOP/INDEX.HTML` via JavaScript.

## Two Interface Modes

### Basic Mode (`/PRESENTATION/HTML/TOP/INDEX.HTML`)

Entry-level view with these options:
- Epson Connect Services
- Google Cloud Print Services
- DNS/Proxy Setup
- Firmware Update
- Root Certificate Update
- AirPrint Setup
- **Product Status** — shows printer error messages and ink levels

### Advanced Mode (`/PRESENTATION/ADVANCED/COMMON/TOP`)

Switch via combobox (id=`modeselect`) at the top-right — select "Advanced Settings". The form submits value `../../ADVANCED/COMMON/TOP`.

**Frameset layout** (3 frames):
- `HEADER` — banner
- `MENU` — left sidebar navigation
- `CONTENTS` — content area, target of all menu links

## Basic Settings → Product Status

**URL:** `/PRESENTATION/HTML/TOP/PRTINFO.HTML`

Shows:
- **Printer Status** — error text ("An error has occurred. Please confirm the indicator or message on the product.")
- **Other Status** — connection status (e.g., "Wi-Fi-72Mbps")
- **Ink levels** — JS-rendered images (BK, Y, M, C indicators). Cannot extract text levels from curl alone. Use browser with vision/screenshot to read actual ink levels.

## Advanced Settings → Maintenance

**URL:** `/PRESENTATION/ADVANCED/INFO_MENTINFO/TOP`

Only shows **"Number of Pages Sorted by Size"** stats table — no head cleaning, nozzle check, or other maintenance actions.

## What's NOT Available from Web UI

- **Head cleaning** — NOT available. Only from the printer's physical control panel (Setup → Maintenance on the touch panel/LCD).
- **Nozzle check** — NOT available. Physical panel only.
- **Print head alignment** — NOT available. Physical panel only.

## Frameset URL Mapping (Advanced Mode)

All paths relative to `/PRESENTATION/ADVANCED/`:

| Menu Item | CONTENTS target |
|-----------|-----------------|
| Product Status | `INFO_PRTINFO/TOP` |
| Network Status | `INFO_NWINFO/TOP` |
| Maintenance | `INFO_MENTINFO/TOP` |
| Hardware Status | `INFO_BEHAVIORINFO/TOP` |
| Error Settings | `PRINTER_ERROR/TOP` |
| Wi-Fi | `NW_WIFI/TOP` |
| Basic (Network) | `NW_BASIC/TOP` |
| Protocol | `NW_SERVICE_PRTCL/TOP` |
| MS Network | `NW_SERVICE_MSNW/TOP` |
| Network Scan | `NW_SERVICE_NWSCAN/TOP` |
| Wi-Fi Direct | `NW_SERVICE_WIFID/TOP` |
| Power Saving | `SYS_ENASAVE/TOP` |
| Admin Password | `ADMIN_PASSWORDSET_CHANGE/TOP` |
| Admin Name/Contact | `ADMIN_CTINFO/TOP` |

## Error States

- When the printer has an error ("An error has occurred"), it may drop off the network entirely (ping fails, HTTP times out). A power cycle (hard reset at the physical printer) is the most reliable recovery.
- The web UI does not expose the specific error code — you must read it from the printer's own display panel.

## Ink Level Detection

Ink level graphics are loaded via JS-rendered `<img>` tags from `../../IMAGE/Ink_K.PNG`, `Ink_Y.PNG`, `Ink_M.PNG`, `Ink_C.PNG`. The image height/size visually indicates the level. Best approached with:

1. Browser with JavaScript enabled → `browser_vision()` screenshot analysis
2. Or open `http://<printer-ip>/PRESENTATION/IMAGE/Ink_K.PNG` etc. directly to see each tank

## Ports Found Open

| Port | Service |
|------|---------|
| 80 | HTTP (web UI) |
| 443 | HTTPS |
| 631 | IPP (Internet Printing Protocol) |
| 515 | LPD (Line Printer Daemon) |
| 9100 | JetDirect (raw TCP/IP printing) |
