# Instance Data Leakage Audit

> Periodic check: scan all agent-created (learned) skills for instance-specific data that leaked in through session-learning patches.
>
> **Context:** Memory is a three-layer system — MEMORY.md (behavioral re-anchor, auto-injected every turn), $HERMES_HOME/memory/ (structured reference facts via write_file), and skills (procedures only). Instance data in skills is a category error — extract to $HERMES_HOME/memory/.

## When to Run

- When consolidating or distilling skills
- When the total learned-skill line count exceeds ~200 avg/skill
- When a user says "this skill is too verbose" or "why is my name in a skill?"

## What to Check

Check every file in the skill directory — SKILL.md AND all files under references/, templates/, scripts/. Instance data often hides in reference files while SKILL.md stays clean, OR in SKILL.md example output blocks while the core procedure is clean.

### SKILL.md Body — Specific Patterns

SKILL.md bodies commonly contain instance data in these specific locations that are distinct from narrative text:

| Pattern | Example | Fix |
|---------|---------|-----|
| **Report templates with real numbers** | Monthly spending summary showing user's actual income (£8,500), spending (£3,242.69), surplus | Replace with round numbers (£10,000 / £3,500) and generic merchants |
| **Subscription/expense examples** | "Netflix £14.99, Spotify £11.99, PureGym £15.00, Notion AI £8.00" | Replace with generic services ("Streaming Service A £14.99") |
| **Budget defaults with real targets** | DEFAULT_BUDGET with user's actual housing (£1,850), dining (£150), transport (£180) | Use clearly default-looking round numbers; note "actual targets in memory tree" |
| **Contract/letter examples with real dates** | "Date: 10 May 2026" | Use "DD Month YYYY" or clearly fictional date |
| **Monthly comparison with real data** | "May 2026 vs May 2025 — Groceries £487.32 vs £512.10" | Use generic YTD comparison with round numbers |
| **Any "example output" block** | Templates introduced by "### Report Template" or "### Sample Output" | Always use clearly fictional data. Never copy-paste real output into a skill template |

**Detection heuristic:** If an example block contains numbers that look like they came from a real month (not round), contains specific merchant names (Waitrose, TfL, Amazon, Encore Estates), or references specific dates that match the conversation timeline — it's instance data.

For each file, search for:

| Class | Examples | Replacement |
|-------|----------|-------------|
| **Names** | User's name, partner's name, child's name, pet's name | "the user", "the partner" |
| **Addresses** | Full address, postcode, specific flat/unit number | "a property", "[address]" |
| **Phone numbers** | `<phone>`, `<whatsapp-phone>` | `<phone>` or `<whatsapp-phone>` |
| **Email addresses** | Any real email | "<email>" or "[email]" |
| **Account numbers / sort codes** | `<chase-current-account>`, `<chase-sort-code>` | `<chase-current-account>`, `<sort-code>` |
| **Amounts** | £7,210, £500/mo, £1,599 | Remove or replace with placeholder |
| **Dates** | 25 May 2026, 13 May 2026 session | Remove narrative dates |
| **Specific provider names** | Hargreaves Lansdown, Kraken, Purplebricks, Vyman, Ola Leslie | "a broker", "a solicitor", generic |
| **Pass/store paths** | `<service>/<path>` | `<service>/<path>` |
| **File paths** | `/opt/data/skills/...` specific paths | Use relative or environment-variable paths |
| **Postmortems** | "Real incident 4 Jun 2026", "discovered during session" | Move to a reference file or remove |
| **Script names with instance context** | `batch-download-ista.py` | Genericize the script name |
| **Interest rate histories** | "was 2.50%, now 2.25% since Dec 2025" | Move to memory tree account file |
| **Observational transaction patterns** | "No withdrawals observed", "all money in is interest only" | Move to memory tree — these are transient observations about a specific account's behaviour |
| **Entity-specific file naming** | "Statement for <Month> <Year> 2.pdf (note the 2 suffix)" | These are borderline — keep in skill if necessary for correct file routing, but move to memory tree if they reference the user's specific accounts |
| **Field-value hardcodes** | Nationality, gender, occupation, address in visa/application form field guides | Replace with "As on passport" / "Per booking" / generic descriptions. Store actual values in memory tree |
| **Prior application references** | "Previously applied through Norway in March 2025" | Move to memory tree. Keep the generic pattern ("include prior visa details") in the skill |
| **Login credential locations** | `pass joy/tejal/ukvi`, email address | Move credential path to memory tree. Keep portal-quirk descriptions in skill |
| **Trip-specific data** | Specific dates (17 Aug → 31 Aug), multi-city routes (Crete→Rome→Florence), budget numbers (£5,500-6,500) | Move to memory tree under travel/trips/. Keep generic travel planning patterns in skill |
| **Insurance policy details with pricing** | "Comprehensive tier ~£44 for Europe", specific policy wording comparisons | Generalise the what-to-check criteria. Move specific provider comparisons and pricing to memory tree |

**False positives (NOT instance data):**
| Pattern | Why it's OK |
|---------|-------------|
| `/nebula/.hermes-docs/` | System document archive path — not personal |
| `$HERMES_HOME/memory/` | Environment variable — generic system reference |
| `/opt/data/` | System root path — generic, not instance-specific |

### Script-Level Leakage (Python, Shell, Config Files)

Python scripts under `scripts/` are the most common hidden leakage vector — instance data here is invisible to SKILL.md audits:

| Pattern | Example | Fix |
|---------|---------|-----|
| **Hardcoded emails in functions** | `def _own_addresses(): return {"user@gmail.com"}` | Extract to `$HERMES_HOME/memory/reference/own-email-addresses.md`; function reads from file |
| **Real usernames in docstrings/examples** | `login: pallavvasa` in script's `"""..."""` block | Anonymize to `login: example-user` |
| **Hardcoded account names in argparse** | `choices=["pallav", "priyanka"]` | Remove choices list; read account names from config in memory tree |
| **Hardcoded pass paths in docstrings/examples** | `--pass-path pallav/accounts.google.com` | Replace with `<pass-path>/accounts.google.com` |
| **Instance-specific defaults in function signatures** | `account="pallav"` as default param | Move to config file; use generic default |
| **Real names in comment examples** | `# Pallav's account`, `# Priyanka's token` | Replace with `# Default account`, `# Another account` |

**Detection:** `grep -rn 'pallav\|priyanka\|user@gmail\|pallavvasa' /opt/data/skills/` — run this after any batch of session-learning patches to scripts.

### Argparse-Level Leakage

CLI argument parsers in scripts are a distinct vector because argparse exposes the `choices` list in `--help` output, which may be logged or inspected:

- **Bad:** `parser.add_argument("--account", choices=["pallav", "priyanka"])`
- **Good:** `parser.add_argument("--account", default=_DEFAULT_GOOGLE_ACCOUNT)` — choices come from config

**Detection:** `grep -rn 'choices=\[' /opt/data/skills/ --include='*.py'` and inspect each for personal names.

### Credential Path Leakage in Cron Prompts

Cron job prompts stored in `/opt/data/cron/jobs.json` are a separate attack surface from skills:

- Plaintext passwords, API keys, or login credentials in cron prompts
- Instance-specific email addresses used as login IDs
- Instance-specific pass paths

These are not skills, so they don't fall under skill-focused audits. Run a separate scan: `grep -rn 'password\|pass:\|api_key\|secret' /opt/data/cron/ --include='*.json'` after every cron creation or edit.

**If found:** Immediately update the cron prompt to remove credentials. Passwords belong only in `pass`. Login identifiers (email addresses used as usernames) can go in the memory tree.

## Extraction Workflow

When instance data is found in a skill reference file, follow this sequence:

### Phase 1 — Identify

1. Read the full reference file content (via `skill_view`)
2. Classify each section: generic procedure (keep) vs instance data (extract) vs borderline (if it's format-level knowledge about a specific provider's statement layout, keep in skill; if it's observational data about this user's account, move to memory tree)
3. For visa/application reference files especially: scan for hardcoded field values (nationality, gender, occupation, address), prior application references (dates, countries), login credentials, document paths

### Phase 2 — Extract

1. Create or extend memory tree files under `$HERMES_HOME/memory/<domain>/` with the extracted instance data
2. Use YAML frontmatter format: title, type, updated date
3. Group related data into one file (e.g. all visa applicant details in one profile file, all trip research in one file)

### Phase 3 — Rewrite

1. Rewrite the reference file to be purely procedural
2. Add cross-reference pointers using QMD/search language — use `> query \`memory/<domain>/\` via QMD (\`mcp_qmd_query\`) or \`search_files\`` rather than hardcoded `$HERMES_HOME/memory/<path>` references. This keeps the skill flexible if the memory tree is reorganized, and it's how the user wants instance data looked up.

### Phase 4 — Parent SKILL.md Check

Two distinct sources of instance data in SKILL.md:

**Source A — Reference content leaked upward:** Content from the distilled reference file that was copied or paraphrased into the SKILL.md body.
- Scan for: "e.g. Norway cover letters left in a France folder" type examples, narrative sections that name the user's specific situation, verification checklist items that reference specific trips
- Fix: generalize or remove

**Source B — Native example output blocks with real data:** Report templates, sample budgets, subscription lists, DEFAULT configurations that were created with real user data during the original skill write (NOT leaked from a reference file).
- Scan for: example output blocks containing non-round numbers, specific merchant names, real dates, or any template that looks like it was copy-pasted from real output
- Fix: replace with clearly fictional data — round numbers, generic merchants, placeholder dates. Add a note: "Actual data in `$HERMES_HOME/memory/`"

For both: patch any instance data found in the SKILL.md body.

### Phase 5 — Verify

1. Run a search across all skills for the extracted instance data patterns to confirm no stragglers remain
2. Check for: entity names (Vasa Holdings, Caxton), transaction patterns (SHARE OF NETSETT), interest rate observations, trip dates, country references tied to the user's situation, email/password references

## What NOT to Extract

Some data that looks like instance data is actually necessary procedural context:

| Pattern | Reason to keep |
|---------|----------------|
| `/nebula/.hermes-docs/` | This is the system's document archive root path — it's a generic infrastructure path, not personal |
| `$HERMES_HOME/memory/` | Environment variable — generic reference to the structured fact store |
| `/opt/data/` | System root — same for all users of this instance |
| Provider-specific file format knowledge | How a Chase statement formats its summary block vs a NatWest one is FORMAT knowledge, not personal data — keep the format description in the skill, extract the interest rate history to memory |
| IBKR's hierarchical CSV structure | This IS the data format — the skill needs to know how IBKR structures its CSV to parse it |

## Output Format

When reporting findings, use:

```
## [skill-name] — [risk-level]

Issues found:
- [n] personal name references
- [n] specific amounts
- [n] narrative/postmortem sections
- [n] instance file paths

Action taken: stripped from SKILL.md / moved to $HERMES_HOME/memory/ tree / replaced with generic / removed
```

## Where Extracted Facts Should Go

Instance data stripped from a skill does NOT stay in the skill's reference files — those are still procedural context. Facts belong in the $HERMES_HOME/memory/ tree:

| What was found | Destination |
|----------------|-------------|
| User's name, partner, family details | `contacts/pallav-vasa.md` (canonical), `contacts/priyanka-shah.md` (partner details) |
| Account numbers, policy refs | `$HERMES_HOME/memory/finance/accounts/` |
| Addresses, property details | `$HERMES_HOME/memory/life/properties/` |
| Dates, timelines | `$HERMES_HOME/memory/life/` or `$HERMES_HOME/memory/reference/` |
| Environment config | `$HERMES_HOME/memory/environment/` or `$HERMES_HOME/memory/architecture/` |
| Any other structured fact | Create a new file in the appropriate $HERMES_HOME/memory/ subdirectory |

### Memory File Format

When creating files under $HERMES_HOME/memory/, use this format:

```yaml
---
title: "Brief Title — Context"
type: fact-type  # e.g. bank-account, brokerage-account, reference, profile
updated: "YYYY-MM-DD"
---

# Title

## Section

| Field | Value |
|-------|-------|
| Detail | Value |
```

**Rule of thumb:** If a fact doesn't need to fire every turn (MEMORY.md) and isn't a procedure (skill), it belongs in $HERMES_HOME/memory/.
