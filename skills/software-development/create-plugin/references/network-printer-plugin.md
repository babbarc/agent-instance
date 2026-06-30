# Network Printer Plugin

Reference implementation of a tool-registration plugin. Located at `/opt/data/plugins/network-printer/`.

## What It Does

Three tools in the `printer` toolset:

| Tool | Purpose | Method |
|------|---------|--------|
| `printer_discover` | Check if Epson ET-2750 is reachable on LAN | Direct TLS socket to port 631 |
| `printer_status` | Ink levels, state, queued jobs, accepting jobs | IPP Get-Printer-Attributes (no CUPS) |
| `print_file` | Send file to printer via CUPS + ESC/P-R driver | `lp -d <instance>` |

## Architecture

Two code paths coexist:

- **Status/discover** — direct IPP-over-TLS to the printer (`ipp_client.py`). No CUPS dependency.
- **Print** — CUPS + ESC/P-R driver (`lp` command) for vector-quality output on PDF/JPEG/PNG.

## Profile-Based Design (Replaces Raw Booleans)

Instead of passing `duplex=True/False`, the tool uses a **profile** string that maps to a CUPS printer instance:

```python
PROFILE_MAP = {
    "default": "ET-2750",              # duplex (Duplex=DuplexNoTumble)
    "onesided": "ET-2750/onesided",    # simplex (Duplex=None)
    "dest": "ET-2750/onesided",        # alias
}

dest = PROFILE_MAP.get(profile, "ET-2750")
args = ["lp", "-d", dest]
```

This separates **intent** ("print single-sided") from **implementation** (which CUPS options). Profiles are opinionated bundles of printer options, not raw flags.

### Rationale

- The ESC/P-R driver ignores `-o sides=one-sided` — `Duplex=None` is the correct PPD option
- Profiles can embed multiple options (Duplex, MediaType, etc.) without changing the tool API
- Adding a new print configuration (e.g. "photo-quality" with high-res + glossy) means adding a CUPS instance + PROFILE_MAP entry, not adding another boolean parameter
- User can test via `lp -d ET-2750/onesided path` independently of the plugin

## Tool Schema Pattern

```python
PRINT_FILE_SCHEMA = {
    "name": "print_file",
    "description": "...",
    "parameters": {
        "type": "object",
        "properties": {
            "path":        {"type": "string", "description": "..."},
            "job_name":    {"type": "string", "description": "..."},
            "profile":     {"type": "string", "default": "default",
                            "description": "Printer profile: 'default' (duplex) or 'onesided' (simplex)"},
            "color":       {"type": "boolean", "description": "Print in colour"},
            "page_ranges": {"type": "string", "description": "e.g. '1-3', '5', '5-', '1,3,5-7'"},
        },
        "required": ["path"],
    },
}
```

### Key design choices

- `profile` has a `default` value so simple calls (`print_file(path="doc.pdf")`) work without specifying it
- `color` and `page_ranges` are orthogonal to the profile — they layer on top regardless of which profile is active
- Page ranges use CUPS native syntax (`5-` means "from page 5 to end")

## CUPS Instance Setup

The `ET-2750/onesided` instance is created with `Duplex=None` baked in as its default:

```bash
lpoptions -p ET-2750/onesided -o Duplex=None
```

Both instances point to the same physical printer URI (`ipp://192.168.0.136/ipp/print`). The instance is just a named set of option defaults.

## IPP Client (`ipp_client.py`)

Direct IPP-over-TLS for printer status queries. Key facts:

- Printer at `192.168.0.136:631` with TLS on the standard IPP port
- Uses IPP 2.0 protocol, HTTP-wrapped on the wire
- `Get-Printer-Attributes` (0x000B) for status
- `Print-Job` (0x0002) is implemented but unused — CUPS handles actual printing for vector quality
- Reads `marker-names`, `marker-colors`, `marker-levels`, `marker-low-levels`, `marker-high-levels`, `marker-types` for ink info
- Parses multi-value IPP attributes where subsequent values repeat the attr name with name-length=0
