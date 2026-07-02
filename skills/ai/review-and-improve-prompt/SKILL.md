1|---
2|name: review-and-improve-prompt
3|description: Iteratively improve a deterministic prompt using a stronger model as reviewer, with human-in-the-loop validation. Best for cron prompts, system prompts, and any prompt where output consistency matters more than creativity.
4|annotation: "Iterative prompt improvement — test, measure, refine"
5|version: 1.3.0
6|---
7|
8|# Review and Improve Prompt
9|
10|Structured process for taking an existing prompt and making it more deterministic, consistent, and resistant to target-model weaknesses.
11|
12|## Prerequisites
13|
14|1. Load the full existing prompt text from the cron job, config file, or snapshot.
15|2. Identify the target model that will run the prompt and its known weaknesses (hallucination, math errors, subjective classification drift, etc.).
16|
17|## Process
18|
19|### Phase 0 — Load This Skill + Domain Rules
20|
21|1. **Load this skill first** — Run `skill_view(name='review-and-improve-prompt')` before any analysis or reviewer dispatch. You need the full process loaded before you start executing it.
22|2. **Determine the prompt's domain** and load the governing rules:
23|   - **Cron prompt** → Also load `skill_view(name='cron-rules')` for fundamentals, then `skill_view(name='cron-prompt-design')` for prompt-specific rules. The scheduler preamble override and terminal() command format are the most commonly missed issues — see cron-prompt-design's `references/scheduler-preamble-override.md`.
24|   - **System prompt** → Load the relevant structural constraints reference for that system.
25|   - **Other domains** → Find and load the governing skill for that domain.
26|3. **Do NOT skip companion loading** — without domain rules loaded, the reviewer model will miss constraints specific to the prompt type.
27|
28|### Phase 1 — Strip Personal Facts + Initial Review
29|
30|1. **Strip non-procedural content before review.** Scan the prompt(s) for personal facts — names, relationships ("wife", "husband", "spouse"), due dates, addresses, IDs, employer names, contact details, family member names. Prompts are procedural instructions only — these do NOT belong. Remove them before sending to the reviewer (saves reviewer tokens and focuses the review on structure).
31|
32|2. **Get multiple reviewer perspectives when available.** Send to Gemini (`gemini_web`), Claude (`claude -p` via terminal if `claude_code` tool is unavailable), and form your own analysis. Each catches different issues. Cross-reference their findings before presenting to the user. If Claude Code CLI auth fails, fall back to terminal: `claude -p "prompt text here" --print`.
33|
34|3. Send the full prompt to a stronger reviewer model (Gemini, Claude Sonnet, GPT-4o) with:
35|   - The prompt text (with personal facts already stripped)
36|   - Target model name and known weaknesses
37|   - Explicit instruction: "Most of the logic looks solid, but output could be more consistent and deterministic."
38|   - Ask for: hallucination hotspots, structural changes for determinism, specific rewrites for riskiest sections
39|   - Also ask: are there any personal facts, names, or non-procedural content that slipped through?
40|
41|4. Read the reviewer's suggestions. Form your own opinion on each:
42|   - **Strong agree** — structural changes that fix, root cause of hallucination / math error / drift
43|   - **Partial agree** — needs refinement before applying
44|   - **Disagree** — explain why to the user
45|
46|5. Present your assessment to the user. Let the user steer: they may agree with your refinements over the reviewer's.
47|
48|### Phase 2 — Full Rewrite
49|
50|6. **Decide who writes the rewrite.** Two valid paths:
51|
52|   - **Delegate to the reviewer** — if the reviewer's suggestions were structurally sound and you only need minor tweaks. Send a follow-up with:
53|     - The agreed changes
54|     - "Produce the FULL prompt — not a diff, not a summary of changes"
55|     - Exact structural requirements (e.g. "preserve the email scoring system, add WhatsApp scoring rubric")
56|
57|   - **Write it yourself** — if the reviewer's output has format issues (XML tags, over-compression, dropped detail), you disagree with the direction, or you have strong refinements that would be lost delegating back. Requirements:
58|     - Preserve ALL working structure from the original (guards, scoring rules, conditional branches)
59|     - Apply ONLY the agreed changes — do not add new features mid-rewrite
60|     - Cross-reference every section against the original for regression
61|     - Present the full text to the user for sign-off before deploying
62|
63|7. **Regardless of who wrote it: check for rendering artifacts.** Common ones:
64|   - XML tags (scratchpad, etc.) inside markdown lists getting eaten
65|   - Angle-bracket placeholders like `<action>`, `<summary>` being stripped as HTML
66|   - Example commands truncated
67|   - Lost footnotes or guardrails (e.g. "widen if unsure", "never X", "do not guess")
68|   - New structural features (emojis, section headers, output format changes) that weren't in the original — flag these; the user may not want them
69|
70|### Phase 3 — Quality & Regression Pass
71|
72|8. Send a second review round asking for side-by-side comparison against the original. Look for:
73|   - Sections, clauses, or guardrails present in the original that are missing
74|   - Internal consistency (score thresholds, contradictory instructions)
75|   - Token efficiency (is there fluff that can be cut?)
76|   - Target-model-specific risks (would the smaller model misinterpret anything new?)
77|
78|9. Run mechanical compliance checks on the revised prompt (do not delegate):
79|   - **Enabled toolsets audit**: Cross-reference every tool call in the prompt against the cron's `enabled_toolsets`. Scan for every function-like call (skills_list(), cronjob(), terminal(), read_file(), etc.), map each to its toolset, then compare against `cronjob action=list` output.
80|     - Any tool called whose toolset is NOT in `enabled_toolsets` → ADD it. Missing toolset = tool unavailable = phase silently fails.
81|     - Any toolset in `enabled_toolsets` that no tool in the prompt uses → DROP it. Each unused toolset adds ~5-15KB of schema overhead.
82|   - **Action-frame override**: Does the prompt open with a positive action directive (e.g. "CRITICAL OVERRIDE: You MUST call terminal()") that directly counters the scheduler preamble's "just produce your report" bias? Without this, DeepSeek V4 Flash skips all tool calls. See cron-prompt-design's `references/scheduler-preamble-override.md`.
83|   - **First-character constraint**: Does the prompt constrain the FIRST character of the delivered response (emoji, bullet, `[` for [SILENT]) to prevent planning text, headings, or acknowledgments from leaking? The constraint must explicitly say tool calls don't count as response text.
84|   - **Phase ordering**: Are all file-write phases ordered AFTER the evaluation phases whose content they depend on? A prompt that says "write the changelog entry" before "evaluate findings" forces the LLM to write empty placeholder files. The tool-calls-first instinct is correct but must only apply to tool calls whose data is already available (mkdir, init empty files) — never to evaluation-dependent persistence.
85|   - **Command format**: Are all executable commands in `terminal("...")` format? Not backtick docs, not bare python3 lines.
86|   - **[SILENT] gate**: If the prompt says "skip silently" or "if no data", ensure it maps to emitting exactly `[SILENT]` — not just staying quiet. Empty output is delivered; `[SILENT]` suppresses delivery. These are different. The rule must be strict: "Output exactly `[SILENT]` and nothing else" — no explanations.
87|   - **Bash string safety**: Check for two specific vulnerabilities:
88|     1. Single-quoted strings breaking on apostrophes (can't, don't, won't) → use heredocs instead.
89|     2. Heredoc sentinel collision (content containing exactly `EOF` closes the heredoc early) → use a less common sentinel like `HERMES_EOF`.
90|     - Also check: overwrite (`>`) vs append (`>>`) on tracking/history files — `>` clobbers, losing previous cycles.
91|   - **Date consistency**: If related prompts contain personal dates (due dates, deadlines), verify they match across all of them — OR strip them entirely since prompts are procedural only.
92|
93|10. Apply regression fixes via another full rewrite request. Don't patch — rewrite clean.
94|
95|### Phase 4 — Deploy
96|
97|11. When the prompt is solid, save a snapshot at `memory/reference/<prompt-name>-snapshot.md`:
98|   - Include metadata header: version, job ID, schedule, script, deliver, toolsets
99|   - Do NOT create versioned filenames (e.g. `-v<N>.md`) — Git commit history provides version tracking. Overwrite the same snapshot file on every update.
100|
101|12. Update the cron job: `cronjob(action='update', job_id='...', prompt='...')`
102|
103|13. Commit the snapshot and push: `git add memory/reference/<prompt-name>-snapshot.md`
104|