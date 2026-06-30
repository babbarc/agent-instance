# File Placement Discipline

> **Write-side enforcement, not post-hoc detection.** Never put disposable output or one-off scripts at `$HERMES_HOME` root. The routing logic should prevent debris, not find it later.

---

## Principles

### 1. Write-Side Enforcement

The user will not tolerate post-hoc detection of root-level debris. No heartbeat scans, no "find orphan files" cron jobs, no cleanup reports.

**The correct approach:** Every agent and profile that writes files must know where things go *before* creating them. The available_skills list in the system prompt (with each skill's domain description) is the discovery layer. If a file ends up at the wrong place, the routing, not the cleanup, is broken.

**What NOT to do:**
- ❌ Create a cron job that scans for new root-level files
- ❌ Add a heartbeat step that checks for clutter
- ❌ Wait for files to accumulate, then clean up

**What to do instead:**
- ✅ Ensure the correct destination is specified before any file is created
- ✅ If you(`skills/scripts/profiles`) are about to write a file, route it explicitly
- ✅ If you discover debris, fix the routing that caused it, not just the symptom
- ✅ Consult `hermes-docs-map.md` at `/opt/data/memory/reference/hermes-docs-map.md` for the canonical document store categories BEFORE creating any deliverable document

### 2. Storage Hierarchy

| File type | Destination | Examples |
|-----------|-------------|---------|
| **Reusable script** | `$HERMES_HOME/scripts/` | CLI tools, utilities, cron-adjacent scripts |
| **One-off / disposable script** | `/tmp/` | Diagnostic checks, one-time extractions, throwaway analysis |
| **Script output data** | `/tmp/` or `$HERMES_HOME/cache/` | Extracted text, intermediate CSVs, report drafts |
| **Durable research output** | `$HERMES_HOME/memory/activity/` or `$HERMES_HOME/memory/life/` | Market research, analysis summaries |
| **Financial statements, bills, invoices** (downloaded from email) | `$HERMES_HOME/statements/` — must be `.md` format for QMD indexing | Bank statements, energy bills, investment statements, service charge invoices |
| **System state** | `$HERMES_HOME/cache/` or designated dirs | JSON caches, model lists, channel directories |
| **Generated deliverable documents** (PDFs, reports, filings, certificates) | `/nebula/.hermes-docs/<category>/<topic>/<filename>` — see Document Store section below | Filed accounts, tax returns, legal documents, signed forms |
| **Document reference stub** | `$HERMES_HOME/memory/<domain>/<topic>.md` — see Document Store section below | Lightweight .md pointing to the deliverable PDF/doc |

### 3. Document Store — hermes-docs

The canonical binary document store is at `/nebula/.hermes-docs/`. It is organised by categories defined in `/opt/data/memory/reference/hermes-docs-map.md`.

**Workflow for storing a generated deliverable document:**

1. **Read the category map** — `skill_view('system-architect', file_path='references/hermes-docs-map.md')` or read `/opt/data/memory/reference/hermes-docs-map.md` directly. Identify the correct category for the document.
2. **Save the document** — Write the file to `/nebula/.hermes-docs/<category>/<topic>/<filename>`.
3. **Create a reference stub** — Write a lightweight `.md` file to `$HERMES_HOME/memory/<domain>/<topic>.md` that contains:
   - A brief summary of the document
   - The full path to the document in hermes-docs
   - Key metadata (dates, amounts, status)
4. **Clean up** — Remove any copies from `/tmp/`, `$HERMES_HOME/memory/`, or `$HERMES_HOME/documents/`. The canonical copy lives under hermes-docs.

**DO NOT:**
- ❌ Save deliverable PDFs under `$HERMES_HOME/memory/` — that directory is for lightweight reference `.md` files only, not binary documents
- ❌ Save deliverable PDFs under `$HERMES_HOME/documents/` or similar ad-hoc paths
- ❌ Skip the reference stub — the user expects a pointer in memory

**Current categories (from hermes-docs-map.md):**

| Category | Purpose |
|----------|---------|
| 00-Unsorted | Uncategorised |
| 01-Identity-Legal | Passports, BRPs, naturalisation, marriage cert, driving licence, OCI, PAN card |
| 02-Career-Manager | CVs, offer letters, employment records |
| 02-Finance | Bank statements, tax docs, Amex, energy bills, crypto, bullion |
| 03-CA-Expert-Tax-Finance | Tax returns, accounting records, HMRC correspondence |
| 04-Immigration-Visa | UK spouse visa, Schengen, visa extensions |
| 05-Holiday-Planner-Travel | Booking confirmations, itineraries, travel insurance |
| 06-Health | Medical records, scans, baby/pregnancy docs |
| 07-Property | Title deeds, council tax, service charges, sale docs |
| 08-Professional-Registrations | HCPC, CSP, SMCR certifications |
| 09-Personal | Baby shower, meeting minutes, Vasa Holdings, personal docs |

**Reference stub format (saved to `$HERMES_HOME/memory/<domain>/<topic>.md`):**

```markdown
---
title: "<Document Title>"
type: reference
domain: <domain>
updated: "<YYYY-MM-DD>"
---

# <Document Title>

## Document Location
`/nebula/.hermes-docs/<category>/<topic>/<filename>`

## Key Information
- Key field 1: value
- Key field 2: value

## Status
- [ ] Action item 1
- [ ] Action item 2
```

### 4. Salvage Heuristic

When reviewing existing scripts to decide keep vs delete:

| Signal | Verdict | Action |
|--------|---------|--------|
| Uses env-based paths (`$HERMES_HOME`, `$HOME`, `os.environ`) | ✅ Keep | Tidy docstring, move to `scripts/` |
| Takes CLI arguments for paths (`sys.argv`, `argparse`) | ✅ Keep | Add usage message, move to `scripts/` |
| Has hardcoded personal paths (`/nebula/.hermes-docs/...`, `/home/user/...`) | 🗑️ Delete | Not portable, won't be maintained |
| Is a diagnostic check (`check_*_tools.py`, `list_*_modules.py`) | 🗑️ Delete | Trivial to recreate |
| Has two versions of the same tool (`add_birthday.py` + `birthday.py`) | ✅ Keep newer, 🗑️ Delete older | Consolidate into one |

### 5. Prevention in Practice

**When creating a new script as part of a task:**
1. Ask: is this reusable (worth keeping) or one-off (disposable)?
2. Reusable → put in `$HERMES_HOME/scripts/` with a proper docstring and usage
3. Disposable → put in `/tmp/`
4. Never: `$HERMES_HOME/` root, `$HOME/` root, or CWD if it's `$HERMES_HOME`

**When a profile or sub-agent creates files:**
- The task instruction (Kanban task body, delegate_task prompt) must include the storage routing rule
- If the profile writes to `$HERMES_HOME` root, the routing instruction was missing — fix the prompt, not the file

---

## Related

- `references/workspace-orphan-detection.md` — Post-hoc detection (for audit/review, not prevention)
- `.hermes.md` §Storage Routing — Operational routing rules
- The available_skills list in the system prompt — skill discovery per domain
- `/opt/data/memory/reference/hermes-docs-map.md` — Canonical hermes-docs category map
