---
name: cron-script-design
description: "Design cron data-collection scripts and no-agent shells — pre-run data scripts, context demarcation, pipeline isolation, bash safety. Load when writing a data script or no_agent cron job."
annotation: "Cron script design: data scripts, no-agent, bash safety"
version: 1.1.0
metadata:
  hermes:
    related_skills: [cron-rules, cron-prompt-design, life-track-crud]
---

# Cron Script Design

> Load when writing a data-collection script or designing a no_agent cron job. Not for normal chat sessions.

## 1. No-Agent Script Design

When writing a script for a `no_agent: true` cron job, the script's stdout is **delivered verbatim** — every byte on stdout becomes the message.

### 1.1 Determine What to Output

1. Was meaningful data collected?
   - YES → Print a human-readable one-line summary. Format for human eyes, not machines.
   - NO (unused day, no data, API error) → Output nothing (empty stdout). In no_agent mode, empty stdout = silent delivery.

2. Always add a `--json` flag for debugging. When set, print raw machine output instead of the human summary.

### 1.2 Validate Before Writing to DB

1. Reject clearly nonsensical values — negative stress, bogus zero active calories on an unworn day, null timestamps.
2. Detect "not used today" state (all-zero metrics + no tracked activity + no sleep) and skip all writes. Stay silent.
3. Exit 0 always — exit code tracks job infrastructure health, not data quality. Non-zero exit marks the cron as errored.

### 1.3 Make Writes Idempotent

1. Delete existing entries for the same date/scope before inserting fresh ones.
2. Re-running the script produces the same DB state — backfills are naturally safe.

### 1.4 Output Decision Tree

```
Data collected?
├─ YES:
│  ├─ --json flag set? → Print raw JSON
│  └─ Default → Print one-line human summary
│     Format: 📊 <Source> • <Date>  •  <metric1>  •  <metric2>
└─ NO (unused, no_data, error) → Silent (empty stdout)
```

See `references/no-agent-script-design.md` for pitfalls and real examples.

## 2. Pre-Run Data Script Design

A pre-run data script (set via `script:` on the cron job) collects data and injects it into the prompt context before the LLM runs.

### 2.1 When to Use One

1. Data comes from an external API (rate limits, latency, auth overhead)
2. Data gathering would take 3+ terminal() calls that burn LLM turns
3. Multiple crons need the same data — route through a single collector

### 2.2 When You Don't Need One

- A single deterministic query (one sqlite3 or life-track.py call)
- A side-effect action (DB write, kanban task creation)
- A conditional action that depends on LLM judgment

### 2.3 Decision Framework

| Layer | Responsible for | Examples |
|-------|----------------|----------|
| **Script** (deterministic) | External IO, parsing, aggregation | curl API, parse JSON/XML, read files, count records, format as labelled sections |
| **LLM prompt** (judgment) | Compare, triage, summarise, propose, decide | "Is this relevant?", "What changed?", "Rate on Value/Cost/Risk" |

The script handles ALL network calls and file reads. The LLM handles ALL decisions. The script NEVER makes a judgment call.

### 2.4 Pattern

- Script goes in `/opt/data/scripts/<cron-name>-data.sh`
- Outputs labelled sections with `=== HEADER ===` markers
- Each section has `|| echo "(no data)"` fallback for graceful degradation
- The cron prompt references injected data as its sole data source (no terminal() for data gathering)

### 2.5 Merge Complementary Data Sources

**Rule:** When two data sources represent the same class of information (movement, content, signals), merge them into ONE labelled section at the script layer. Do NOT rely on the LLM to cross-reference separate sections.

**Why:** LLMs evaluate each section independently. If "Yesterday's Workout" is empty but "Garmin Activities" has a walk logged, the LLM will report "no workout" and ignore the activities section — the prompt's instruction to cross-reference is fragile.

**How:**
1. Collect both sources in the script (capture to variables, not pipes)
2. Priority order: logged/human-entered data first, auto-tracked data as fallback
3. When the primary source is empty but the fallback has data, label it clearly — "No gym workout logged, but Garmin shows movement:" followed by the activities JSON
4. When both exist, keep them in the same section (primary shown, supplementary noted)
5. Remove the duplicate standalone section that was the fallback's original home

**Decision tree:**
```
Primary source has data? 
├─ YES → Show primary data
│  Supplementary source has data?
│  ├─ YES → Show supplementary below primary within same section
│  └─ NO → Show primary alone
└─ NO
   Supplementary source has data?
   ├─ YES → Show supplementary with context prefix
   └─ NO → Show "(no data)"
```
1. **Trim reference file injections.** When injecting a static document (life goals, baselines), use `sed '/^## <Section>/Q'` to stop at the boilerplate boundary. The LLM only needs the factual content, not the document's own meta-instructions.
2. **No output-phase side-effects in the prompt.** If the LLM prompt has a `## Post-Step` that runs terminal() after composing output, move that work into this data script instead. The LLM's whole output IS the deliverable — nothing should execute after it. See `cron-prompt-design`'s `references/post-step-ordering.md`.
3. **Only signal with a purpose.** If adding a pipeline-completion signal to the script, every signal must have a downstream reader. A `collected` or `pipeline-ran` with no consumer is noise. See `references/signal-noise-pitfalls.md`.
4. **Output JSON from CLI wrappers, not pipe-delimited text.** When a query goes through `life-track.py` (or any CLI wrapper), pass `--json` so the LLM receives structured data with labelled fields. Pipe-delimited text forces the LLM to guess column boundaries — fragile when data changes. The script section header declares what the data is; the JSON body provides the structure.

   Correct:
   ```bash
   python3 /opt/data/scripts/life-track.py signal list --date "$DATE" --domain health --json
   ```

   Wrong (pipe-delimited, fragile ordering):
   ```bash
   sqlite3 "$DB" "SELECT metric, value FROM life_signals WHERE ..."
   ```

5. **Data script must never trigger LLM side-effects.** The script collects and outputs data — it must NOT run DB writes that duplicate what the LLM prompt's terminal() step does. If the LLM prompt has a write step that merely copies data from one table to another (e.g. reading `life_signals` and writing to `daily_summary`), that write belongs in the collector cron, not in the LLM action nor in this data script. Reasoning: the LLM adds no judgment value to a mechanical data copy — it only wastes tokens and introduces the risk of skipping the action. See `references/llm-table-sync-anti-pattern.md`.

### 2.5 Pipeline Failure Isolation

When a data-collection script pipes multiple commands together, isolate each segment:

**Preferred — Isolate pipe segments:**
```bash
# Step 1: Fetch raw data
RAW=$(python3 gmail_delta.py --since 2h 2>&1) \
  || { echo '{"status":"error","message":"gmail_delta failed"}'; exit 1; }
# Step 2: Enrich (optional — fail open)
echo "$RAW" | python3 resolve-email-senders.py \
  || echo '{"status":"warn","message":"resolve failed, using raw","data":'$RAW'}'
```

**Primary-source failures** should cause the script to exit non-zero (primary = data the cron exists to monitor). **Supplementary failures** get `|| echo` fallback.

See `references/pipeline-failure-isolation.md` for the full pattern.

## 3. Context Demarcation Markers

When a data script injects pre-window context alongside in-window data, the LLM needs explicit demarcation to avoid triaging old items.

### 3.1 Markers

Use `[context]` / `[window]` (square brackets) in the data script output — NOT `--- SECTION ---` which collides with conversation headers.

### 3.2 Conditional Emission

Only emit the context marker when pre-window context actually exists. If no context exists, suppress all markers — all messages are in-window.

### 3.3 Prompt-Level Reporting Scope Rule

The cron prompt must include:
> **Reporting Scope:** Only triage, route, report, and enrich contacts based on items within the current heartbeat window.
> - **Channel with context injection:** Messages between `[context]` and `[window]` are pre-window — provided for thread understanding only. Messages after `[window]`, or all messages if no `[context]` block, are in-window and fully actionable.

### 3.4 Cover All Side-Effects

The exclusion rule must mention enrichment alongside triage/routing/reporting. Context messages containing life facts (e.g. "I just started a new job") would otherwise trigger unnecessary enrichment writes.

## 4. Bash String Safety

All post-step terminal() commands that pass a dynamic summary string:

```bash
# Safe — single-quoted, with apostrophe-restriction rule:
python3 /opt/data/scripts/life-track.py signal add <domain> <metric> <value> '<summary>'
```

**Vulnerability 1 — Apostrophes in single-quoted strings:** If summary contains `'`, it closes the bash string. Fix: paraphrase around apostrophes.

**Vulnerability 2 — $, `, " in double-quoted strings:** Character `$` triggers variable expansion, backtick triggers command substitution, `"` terminates the string. Fix: use single quotes and forbid apostrophes in summaries.

**Prompt rule:**
```
- Summaries: use single quotes in bash commands. Do NOT include apostrophes or special characters ($, `, ") inside summary text.
```

## 5. DB Access — life-track.py Required (Not Optional)

For database writes and reads, use `life-track.py` — never raw `sqlite3`. This is a hard rule, not a preference.

**Why:** Raw `sqlite3` in data scripts bypasses path validation (the canonical DB is `/opt/data/life/life-tracking.db`, not `/opt/data/memory/life/life-tracking.db`), produces fragile pipe-delimited text that the LLM must guess column boundaries for, and creates inconsistent output formats. Every future maintainer must know which path your script hardcoded — the wrapper eliminates this.

**When raw sqlite is acceptable (only):** multi-table analytical reads that `life-track.py` can't express in one command. Single-table reads must go through the wrapper.

**Correct:**
```bash
python3 /opt/data/scripts/life-track.py signal list --date "$DATE" --domain health --json
python3 /opt/data/scripts/life-track.py workout list --date "$DATE" --json
python3 /opt/data/scripts/life-track.py batch << 'EOF'
{"command":"life-signal","domain":"health","metric":"fitness_morning","value":"ok","note":"..."}
EOF
```

**Wrong:**
```bash
sqlite3 "$DB" "SELECT * FROM life_signals WHERE date='$DATE'"
sqlite3 /opt/data/memory/life/life-tracking.db "SELECT ..."  # stale path!
```

Load the `life-track-crud` skill for the full command reference. See `references/ghost-db-remediation.md` for the canonical DB path.

## References

- `references/no-agent-script-design.md` — Pitfalls and real examples for no_agent scripts
- `references/pipeline-failure-isolation.md` — Isolating pipe segment failures with diagnosis patterns
- `references/bash-string-safety.md` — Full reference for both string vulnerabilities
- `references/ghost-db-remediation.md` — Avoiding stale DB paths, canonical path protocol
- `references/signal-noise-pitfalls.md` — Signal logging traps: no-reader signals, duplicating cron state, started/completed noise
- `references/llm-table-sync-anti-pattern.md` — Why LLM must never copy data between tables; where writes belong instead
