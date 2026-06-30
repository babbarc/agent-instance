# Cron-Rules Pitfalls

39 known failure modes for cron jobs. Load via `cron-rules` skill.

| # | Title | Key Risk |
|---|-------|----------|
| 1 | Never Use cronjob(action='update') to Read a Prompt | Destructive overwrite. Also: passing fields you don't intend to change overwrites them. Scope to ONLY the fields needed. |
| 2 | Prompt Snapshot Files Must Be Maintained | Loss of prompt recovery path |
| 3 | Phantom Script References in Prompt Body | LLM fabricates data from non-existent scripts |
| 4 | Credential Leakage in Prompts | Secrets stored in plaintext |
| 5 | Fake Routing (Unactionable Instructions) | LLM instructed to route with no mechanism |
| 6 | Orphan Skill References | Silent skill loading failure |
| 7 | Ambiguous Date Templates | API interprets UTC, events shift 1h |
| 8 | Pre-Run Script Watermark Contamination | Manual run causes silent cron |
| 9 | Schedule Collisions | Interleaved output from concurrent deliveries |
| 10 | Stuck Scheduler | `last_run_at` never updates on error |
| 11 | `cronjob run` Does Not Execute Immediately | Dev expects instant execution |
| 12 | Missing enabled_toolsets | ~20 tool schemas loaded unnecessarily |
| 13 | Over-inclusive enabled_toolsets | Token waste |
| 14 | Cron Prompts Not Git-Tracked | Primary backup = output logs |
| 15 | Output Gate Verification During Restructuring | Blue items silently dropped |
| 16 | Dangling FLOW Entries With No Corresponding Section | LLM invents criteria |
| 17 | Injected Data Failure — Primary Sources Should Fail the Run | LLM fabricates data on failed source |
| 18 | Proposing Architecture Changes When Adding Features | Over-rebuild instead of minimal change |
| 19 | Watermark/Cursor Persistence in /tmp | Reboot -> full backlog re-ingested |
| 20 | Pipeline Failure Isolation — Don't Let `||` Mask Root Cause | Downstream failure masked by fallback |
| 21 | Bash String Safety in Post-Step Commands | Apostrophes and $/`/" in summaries crash bash strings |
| 22 | Scheduler Preamble Overrides Action Frames | LLM skips tool calls |
| 23 | Routing Flow Escape Hatch — Don't Mix B/C With D | LLM uses D to skip committed routing |
| 24 | Skill Name Collision Across Profile and Shared Dirs | Worker silently fails on spawn |
| 25 | Email Triage Blind Spot | Purchase confirmations killed by sender scoring |
| 26 | gmail_delta.py `--query` Replaces the Entire Query | Query excludes time filter |
| 27 | Stale Stream Timeout Tuning — Not One-Size-Fits-All | DeepSeek latency + context-size scaling cause false stale kills |
| 28 | Stale/Empty Data-Source Paths — Existence != Data | LLM wastes tool calls on ghost data sources |
| 29 | Cross-Cutting Systemic Issues Require a Full Cron Sweep | Fixing one leaves others broken |
| 30 | Life Goals Data Source Duality — Reference File vs DB Pulse | Script injects compass without position fix |
| 31 | Invisible-Unicode Contamination from External Data Sources | External data triggers injection scanner |
| 32 | `$HERMES_HOME` Script Paths Break Under Profile Isolation | Cron data scripts using `$HERMES_HOME/scripts/<file>.py` resolve to the profile's scripts/ dir, not the default. Python helpers aren't moved. Fix: use absolute `/opt/data/scripts/` paths in all profile scripts. |
| 33 | Direct File Edit of cron/jobs.json or config.yaml | A single `replace_all`, stray backslash, or escape mismatch corrupts the entire JSON file. Use `cronjob(action='update', ...)` for prompt changes, `hermes config set` for config changes. Only use `python3 json.dump()` for bulk recreation from curator backups — validate with `json.loads()` before writing. |
| 34 | Script Path Resolution — `HERMES_HOME/scripts/` Only on Unpatched v0.17.0 | The `script:` field resolves relative to `HERMES_HOME/scripts/` regardless of job `profile`. **Unpatched** v0.17.0: no_agent jobs hard-fail, agent-based jobs silently degrade. **This system is patched** — profiles work via ContextVar-only override. See `references/v0.17.0-profile-removal.md`. |
| 35 | Credential Lookup in Profile-Run Scripts — Pass/GPG Not Found | A no_agent script running under a profile with its own `home/` can't find `pass` or `gpg` keys — those directories don't exist in the profile HOME. `pass show` returns non-zero for every path. Fix: set `PASSWORD_STORE_DIR` and `GNUPGHOME` explicitly in the script before calling any pass/gpg command. Do NOT change `HOME` — too broad. Minimal: `export PASSWORD_STORE_DIR=/opt/data/home/.password-store` and `export GNUPGHOME=/opt/data/home/.gnupg`. |
| 36 | Transient Items Become Permanent Tasks | Catch-all routing rows force one-shot items into kanban tasks. See `references/routing-flow-transient-items.md`. |
| 37 | Orphan Data Scripts — Script Exists, No `script:` Field | Data script on disk never wired to cron — LLM fabricates output. Verify `script:` field via `cronjob action=list`. |
| 38 | Mid-Day Schedule Change Skips a Day | Schedule gap from mid-day change |
| 39 | Phase Ordering — Writing Results Before They Exist | LLM writes placeholder/empty files when file writes precede the evaluation that produces their content |
