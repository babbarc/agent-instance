# Skills Hub & Registries

How the Hermes Skills Hub works when searching and installing community skills.

## The 4 Registries

| Registry | Skills | Trust Level |
|----------|--------|-------------|
| **official** | 91 built-in | `official` — no security scan |
| **optional** | 72 optional | `official` — no security scan |
| **Anthropic** | 16 | `official` — no security scan |
| **LobeHub** | 505 community | `community` — security-scanned, CAUTION verdict blocks by default |

## Install Flow

```
hermes skills search <term>
         ↓
hermes skills inspect <name>      # Preview before installing
         ↓
hermes skills install <name>      # Fetches → quarantines → security scans
         ↓
    ┌────┴────┐
    │ PASS    │ BLOCKED (community source + CAUTION verdict)
    │         └→ hermes skills install <name> --force
    ↓
Installed in ~/.hermes/skills/
```

## Identifier Formats

| Format | Works? | Example |
|--------|--------|---------|
| Short name | ✅ | `hermes skills search grammar` → `grammarly` |
| Name only | ✅ | `hermes skills install grammarly` |
| `source/name` | ✅ in search results | Shows as `lobehub/grammarly` |
| `source:name` | ❌ | `lobehub:grammarly` — "Not found" |
| Direct URL | ✅ | `hermes skills install https://.../SKILL.md` |

## Security Scan Behaviour

- Community-source skills get quarantined to `.hub/quarantine/<name>/`
- A Tirith security scan runs against the SKILL.md
- Findings are reported with severity: LOW, MEDIUM, HIGH
- **CAUTION verdict** blocks the install with: `Blocked (community source + caution verdict, N findings)`
- Common findings: `supply_chain` (npm install, pip install from SKILL.md)
- Override with `--force`

## When to Use Each Registry

- **official/optional** — Reliable, no friction. Prefer these first.
- **lobehub** — 505 community skills, many languages/niche use cases. Expect to `--force` install.
- **Direct URL** — For self-hosted or custom skills not in any registry.
