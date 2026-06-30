1|# Checklist-Based Email Priority Scoring
2|
3|> Research synthesis and proposed design for replacing Gate 1's categorical pass/fail with a binary-checklist scoring system.
4|> Source: Heartbeat cron review session, June 2026
5|> Version: 3 (v15 of heartbeat prompt — semantic Content scoring)
6|
7|## Problem
8|
9|The current heartbeat Gate 1 uses an 8-category table (Family, Financial, Legal, Career, etc.) with binary pass/fail per category. Three issues:
10|
11|1. **Category gaps** — GP prescriptions, building maintenance notices, and other real-world emails have no natural home
12|2. **Fuzzy categorization** — LLMs are inconsistent at "is this Financial or Legal?" for borderline emails
13|3. **Tiebreaker uncertainty** — the tiebreaker defaults to "pass" for unknown cases, over-flagging noise
14|
15|## Research Sources
16|
17|- "AI Driven Email Triage and Action Bot for Smarter Email-to-Action Conversion" (IEEE, 2026) — Uses NLU + Agentic AI pipeline with intent classification + priority scoring + action extraction. Decomposes complex triage into simpler classification steps.
18|- Google Smart Reply (KDD 2016) — Learned sender interaction patterns for prioritization; sender history is the strongest signal.
19|- "Focus on the Action: Learning to Highlight and Summarize Jointly for Email To-Do Items Summarization" (2022) — Sentence-level relevance scoring for action item extraction.
20|- Semantic Scholar search: "email priority triage llm" — 60 results, dominated by medical emergency triage (not directly applicable) and spam detection (narrower scope). True email triage for knowledge workers is under-researched in academic literature.
21|
22|## Proposed Design
23|
24|Replace Gate 1's 8-category table with a 4-dimension binary checklist. Each dimension collects yes/no answers. The total score maps to an ordinal urgency level.
25|
26|### The Scoring Rubric
27|
28|**Sender (0-4):**
29|- Close family/spouse → +4
30|- Known professional contact (solicitor, doctor, active project) → +3
31|- Known friend/colleague → +2
32|- Recently emailed (sent mail match) → +1
33|- Bulk/mailing list → 0 (silent — stop scoring)
34|
35|**Content (0-6, add all that apply, each check → +1):**
36|- Expresses urgency or a deadline → +1
37|- Requires Pallav to take an action → +1
38|- Requires a decision or approval → +1
39|- Has financial relevance (payment, amount, transaction) → +1
40|- Reports a change in status (accepted, confirmed, completed, cancelled) → +1
41|- Shares personal news or an update from someone Pallav knows → +1
42|
43|**Why semantic checks over keyword lists:** The old Content scoring used specific keywords ("urgent", "action required", "decision", "payment due") with weighted values (+3 for time-sensitive, +2 for questions). This had two problems:
44|1. **Narrow coverage** — "Please sign by Friday" doesn't contain "deadline" or "due" but is clearly time-sensitive. Semantic checks let the LLM use natural understanding.
45|2. **Weight jump risk** — One keyword shifted scores by 2-3 points, easily crossing a boundary between 🔵 and 🟡 or 🟡 and 🔴. Each semantic check is +1, so a single signal shifts the score by 1 point — finer granularity, fewer accidental boundary crossings.
46|
47|Max content score: 6 (vs 10 in the old weighted system). Max total: 16 (vs 20).
48|
49|**Relevance (0-4):**
50|- Matches active kanban workstream → +4
51|- Relates to known life goal (property, baby, visa, health) → +3
52|- Security/account alert → +4
53|- About known upcoming event → +2
54|- None of the above → 0
55|
56|**Context (0-2):**
57|- Calendar event in next 7 days relates to sender/topic → +2
58|- No context match → 0
59|
60|### Priority Mapping
61|
62|| Total Score | Level | Action |
63||-------------|-------|--------|
64|| 10-16 | 🔴 Urgent | 1 bullet, explicit ask/deadline |
65|| 7-9 | 🟡 Important | 1 bullet, needs decision |
66|| 4-6 | 🔵 Informational | 1 line if noteworthy |
67|| 0-3 | ⏭ Silent | Skip entirely |
68|
69|## Why Checklist Beats Categories
70|
71|| Property | 8-category pass/fail | Checklist scoring |
72||----------|---------------------|-------------------|
73|| Decision type | Categorical ("which bucket?") | Binary (yes/no per check) |
74|| LLM consistency | Low — forces round peg into square hole | High — yes/no is LLMs' strongest skill |
75|| Gap handling | Tiebreaker defaults to "pass" — over-flags | Scores low naturally — silence unless checks fire |
76|| Token cost | 36 lines of table + tiebreaker | ~30 lines of checklist items |
77|| Explainability | "It passed Gate 1" | "Sender+3, Content+4, Relevance+4 = 11 → Urgent" |
78|| Tunability | Add/remove categories = rewrite gates | Add/remove checklist items = adjust scores |
79|
80|## Example Scoring
81|
82|**Security alert from Google:**
83|- Sender: unknown (1)
84|- Content: security sign-in alert → status change (1)
85|- Relevance: security alert (4)
86|- Context: no calendar match (0)
87|- **Total: 6 → 🔵 Informational**
88|
89|**Solicitor email about property deadline:**
90|- Sender: known professional (3)
91|- Content: urgent deadline (1), requires action (1), needs decision (1) → cumulative 3
92|- Relevance: active kanban workstream (4)
93|- Context: calendar event matches (2)
94|- **Total: 12 → 🔴 Urgent**
95|
96|**Octopus monthly bill:**
97|- Sender: automated/unknown (1)
98|- Content: financial relevance (1)
99|- Relevance: no match (0)
100|- Context: no match (0)
101|- **Total: 2 → ⏭ Silent**
102|
103|**Friend dinner invite:**
104|- Sender: known friend (2)
105|- Content: requires action? maybe (1)
106|- Relevance: unrelated (0)
107|- Context: no match (0)
108|- **Total: 3 → ⏭ Silent**
109|
110|## Implementation Notes (Jun 2026 — Implemented)
111|
112|- The final structure has **separate WhatsApp and Email triage sections**, each with only the gates they need
113|- Gate 2 was **removed entirely** — script-level dedup (email cursor, WhatsApp feed) handles uniqueness; kanban staleness is a one-line check in the output section, not a gate
114|- Prompt snapshot: `memory/reference/heartbeat-prompt-snapshot.md`
115|- **Status: IMPLEMENTED** in heartbeat-watchdog prompt (v7 → v11)
116|
117|### Final Architecture (v11)
118|
119|```
120|### EMAIL — Gate 1 → Gate 3
121|
122|Gate 1 — Score (4 dimensions)
123|Gate 3 — Output by score (🔴 🟡 🔵 ⏭)
124|Calendar items: de-escalate one level unless <48h
125|
126|### WHATSAPP — Gate 1 → Gate 3
127|
128|Gate 1 — Sender check (known → Gate 3, bulk → ⏭)
129|Gate 3 — Content-based (health→🔴, decision→🟡, casual→🔵, routine→⏭)
130|
131|### STALLED TASKS (one line in RECURRING STATUS, not a gate)
132|```
133|
134|Gate 2 was removed because:
135|- **Email dedup is at script level** — gmail_delta.py with cursor only returns new emails since last check
136|- **WhatsApp dedup is at script level** — whatsapp_delta.py only injects new messages
137|- **"Already tracked → silent" was wrong** — a new email on the same kanban workstream ("please sign page 3") IS a development that should be flagged, not silenced
138|- **Kanban staleness** is a separate concern — it's a one-line check alongside RECURRING STATUS, not a gate that items flow through
139|
140|### Gate 3 Restructure (v9 — Removed Duplicate Urgency Re-Assessment)
141|
142|**Problem:** Gate 1 already scored emails (10-14→🔴, 6-9→🟡, 3-5→🔵). But Gate 3 re-assessed urgency with different criteria (48h deadline, needs decision, blocks goal), forcing the LLM to reconcile two systems.
143|
144|**Fix:** Gate 3 no longer re-assesses urgency — it just formats output based on Gate 1's score:
145|
146|| Score | Level | Output |
147||-------|-------|--------|
148|| 10-14 | 🔴 Urgent | 1 bullet with explicit ask/deadline |
149|| 6-9 | 🟡 Important | 1 bullet with state/decision needed |
150|| 3-5 | 🔵 Informational | 1 line |
151|
152|**Also removed:**
153|- Two 🟡 levels ("Action needed" vs "Important") — merged to one
154|- ⏭ Routine ("Same pattern as last cycle" — vague, LLM has no reference)
155|- ⏭ Handled (caught by Gate 2, no longer exists)
156|- Source multiplier was replaced by separate WhatsApp content-based output
157|
158|### WhatsApp Separate Triage — Content-Based Output (v10-v11)
159|
160|**WhatsApp Gate 1 (sender-only):**
161|
162|WhatsApp goes through a **sender-only check** instead of the full 4-dimension email checklist:
163|
164|```
165|- Known contact → Gate 3
166|- Bulk/group → ⏭ Silent
167|```
168|
169|**Why separate from email:** WhatsApp messages are conversational — deadlines, transactions, and workstream keywords don't apply naturally. A casual "dinner at 7?" from Priyanka would score 6+ on the full checklist (Sender 4 + Content "question" 2 = 6 → 🟡 Important), which is too high for a trivial question.
170|
171|**Critical bug found in v8-v9:** The WhatsApp fast path assigned NO numerical score — it just said "pass to Gate 2." But Gate 3's "Source multiplier (adjust score before choosing output)" said "WhatsApp → +2 points." There were no points to add. The multiplier was dead code for WhatsApp.
172|
173|**Fix (v10):** WhatsApp has its own Gate 3 section that reads message content directly — no score involved:
174|
175|Priyanka or immediate family:
176|- Health concern, emergency → 🔴 Urgent — 1 bullet
177|- Needs a decision, time-sensitive → 🟡 Important — 1 bullet
178|- Casual update, logistics, check-in → 🔵 Informational — 1 line
179|
180|Known friend, colleague, family:
181|- Important news, specific ask → 🟡 Important — 1 bullet
182|- Casual invite, update, check-in → 🔵 Informational — 1 line
183|- Routine → ⏭ Silent
184|
185|Unknown or !!UNKNOWN:!!:
186|- Any → 🔵 Informational — 1 line
187|
188|**Design rationale:** WhatsApp messages are short (1-2 sentences). The LLM reads the message content directly and makes an ordinal judgment — much cheaper than fitting WhatsApp through the full 4-dimension email rubric. Gate 1 handles sender-only (zero reasoning), Gate 3 handles content (on the already-short message). The broken score multiplier is replaced entirely.
189|
190|**WhatsApp Gate 2 not needed:** WhatsApp-feed.py only returns new messages since last check — same message never appears twice. And message-level dedup would be wrong: "viewing confirmed" from a realtor is one message, "offer accepted" on the same thread is a different message with different content. Gate 2 would silence the second if using topic-level dedup, which is incorrect. WhatsApp has two gates, not three.\n\n**WhatsApp-feed already filters groups and broadcasts:** The whatsapp_delta.py script (line 467) skips `status@broadcast` JIDs entirely and (line 500) only keeps group messages where Pallav is @mentioned or name-dropped. So the prompt's WhatsApp Gate 1 does NOT need a "Bulk or group → ⏭ Silent" rule — the script already handled it. Everything reaching the prompt is a direct message or a personally relevant group mention. This follows the broader pattern: filter output in the script, not the prompt.
191|
192|### Final Scoring Format (v15 — Semantic Content)
193|
194|The Content dimension was refined from 4 weighted keyword checks to 6 unweighted binary semantic checks (each +1):
195|
196|| Old (v7) | New (v15) |
197||----------|-----------|
198|| deadline/time-sensitive word → +3 | Expresses urgency or a deadline → +1 |
199|| "urgent/action required/decision/payment due" → +3 | Requires Pallav to take an action → +1 |
200|| specific question/request → +2 | Requires a decision or approval → +1 |
201|| transaction/amount → +2 | Has financial relevance → +1 |
202|| — | Reports a change in status → +1 |
203|| — | Shares personal news or an update → +1 |
204|
205|Benefits: narrower score jumps (1 point per signal instead of 2-3), broader coverage (status changes and personal news were missing), and natural language checks the LLM interprets without keyword matching.
206|
207|**Adjusted boundaries:** Max score dropped from 20 to 16. Ranges widened to 10-16/7-9/4-6/0-3, making each boundary harder to cross accidentally.
208|
209|### Routing Integration (v13 — Triage-Decides-Route)
210|
211|**Problem (v1-v12):** Routing was a separate step after triage. The LLM evaluated each item in triage (score → output), then re-evaluated it in routing (does this need a task?). Same item, two cognitive passes, token waste, potential inconsistency.
212|
213|**Fix (v13):** The routing decision is made *during* triage. Each triage section (Email, WhatsApp) ends with a "Route or output only?" rule that the LLM applies while evaluating the item. The ROUTING MECHANICS section becomes just the SQL execution — no re-thinking.
214|
215|### Two-Tier Routing
216|
217|Instead of always creating a new kanban task, the LLM chooses:
218|1. **Update existing workstream** — if the item relates to an active kanban workstream, append the new information to the existing task's body via UPDATE
219|2. **Create new standalone task** — if the item is a new action (new bill, new purchase, new contract), INSERT a new task for the appropriate specialist
220|
221|The assignee table from v1-v12 remains:
222|| New standalone item | Assignee |
223||---------------------|----------|
224|| Statement/bill/invoice | ca-expert |
225|| Purchase confirmation | inventory-manager |
226|| Contract/legal | legal-expert |
227|| Home maintenance | home-manager |
228|| Family event | family-manager |
229|
230|### Pending Tasks for Decision-Needed Items
231|
232|Items needing Pallav's personal decision (e.g. "which offer to accept?") previously had no routing path — the rule said "never task." But blocking routing meant no follow-up mechanism existed once Pallav decided.
233|
234|**Fix:** Create a task with `status="pending"` and append `"⏳ waiting on Pallav"` to the body. The specialist sees it when the status changes to "ready", allowing the workflow to continue without losing context.
235|
236|### WhatsApp Routing
237|
238|WhatsApp messages now route when they contain actionable info tied to an active workstream (property viewing, health booking, travel change, family event). Same two-tier: update existing task body for an active workstream, or create a new task. Casual chat, informational updates, and routine messages stay as output-only — no task.
239|
240|### Routing SQL Templates — Use kanban.py
241|
242|For new tasks (standalone actions):
243|```bash
244|python3 /opt/data/scripts/kanban.py add --title "<title>" --assignee <profile> --status ready --body "<body>"
245|```
246|
247|For pending tasks (decision-needed items): same `kanban.py add` but `--status pending` and body includes `"⏳ waiting on Pallav"`.
248|
249|For active workstreams (update existing task body):
250|```bash
251|python3 /opt/data/scripts/kanban.py get <existing-task-id>
252|# Read the full body, decide if append or status change is needed, then:
253|python3 /opt/data/scripts/kanban.py update <existing-task-id> --append-body "\n<heartbeat update>: <new info>"
254|```
255|
256|### Summary — Routing Evolution
257|
258|| Version | Routing model | Problem |
259||---------|--------------|---------|
260|| v1-v12 | Separate ROUTING step, re-evaluates every flagged item | Token waste, inconsistency |
261|| v13 | Routing decided during triage, SQL is execution-only | One pass, consistent |
262|| v16 | Deduplicated A/B/C/D model — shared across Email + WhatsApp | Two copies of same logic in different words |
263|
264|### v17 Routing — `kanban.py add` Over Raw SQL (June 2026)
265|
266|The routing SQL templates from v13-v16 used `hex(randomblob(8))` for task IDs and raw SQL INSERT/UPDATE. These were replaced with `kanban.py` CLI calls (v17):
267|
268|**Before (v16) — raw SQL:**
269|```sql
270|INSERT INTO tasks (id, title, body, assignee, status, created_by, created_at)
271|VALUES (hex(randomblob(8)), '<title>', '<body>', '<profile>', 'ready', 'heartbeat', strftime('%s','now'));
272|```
273|Produces unreadable hex IDs like `69745526F1E2A655`.
274|
275|**After (v17) — `kanban.py add`:**
276|```bash
277|python3 /opt/data/scripts/kanban.py add --title "<title>" --assignee <profile> --status ready --body "<body>"
278|```
279|Produces readable `t_verb_noun` IDs like `t_review_ista_invoice`.
280|
281|**Read-before-write routing (v17 routing A):**
282|Instead of blind-appending to the task body, routing A now loads the full body first:
283|```markdown
284|A) **Update existing task** — item topic matches an active kanban workstream title or body
285|   → python3 /opt/data/scripts/kanban.py get <task-id>
286|   Read the full task body. Then decide:
287|   - Does the new info warrant a status change? (blocked, in_progress, done, pending)
288|   - Does it update the body? Where?
289|   - Is it a timeline comment instead? (use kanban.py comment)
290|   Then execute the appropriate kanban.py command.
291|```
292|
293|**Blind append resolved (v18) — `--append-body`.** The raw SQL append pattern was a temporary gap because `kanban.py update --body` replaced the entire body. As of 6 Jun 2026, `kanban.py update --append-body` appends to the existing body. No more raw SQL needed.
294|
295|**Kanban query updated** to include `substr(body, 1, 80)` so the LLM can quickly identify candidate tasks without loading every one. Also added `blocked` to the status filter (was missing in v16 — blocked tasks are still active workstreams).
296|