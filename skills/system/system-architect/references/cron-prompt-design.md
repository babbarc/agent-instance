# Cron Prompt Design — Principles & Patterns

> Class-level reference. Load this when creating or modifying any cron prompt.
> Covers: recency bias, instruction structure, token budget, skill loading, DB write patterns, routing decision flows.

## 1. Recency Bias Is the #1 Cron Prompt Failure Mode

All decoder-only LLMs (DeepSeek, Claude, GPT, Llama) overweight information at the **end** of the prompt while attenuating content in the middle ("Lost in the Middle", Liu et al. 2023).

**What happens:** A DB-write step placed at the very end with ⚠️ MANDATORY markers becomes the agent's *primary task*, not its *post-task*.

**Documented failure:** Morning-briefing cron (11 May 2026) — the prompt ended with "⚠️ MANDATORY: Save a daily signal to the life-tracking DB". The agent composed exactly that: a DB write confirmation, and nothing else. The actual briefing instructions in the middle were attenuated.

## 2. Prompt Structure Templates

### Template A: Agent-Driven Cron (has a deliverable → Telegram)
```
💥 YOUR RESPONSE MUST BE THE [DELIVERABLE]. Nothing else.

## Data sources (run each, skip failures gracefully)
- Command 1
- Command 2

## Mental checklist
- Check 1
- Check 2

## Output format — THIS IS WHAT YOU SEND
[exact format the user should see, no extra framing]

## Background task: persist [X] signal
After sending your message above, quietly execute_code with this script:
```python
INSERT INTO life_signals ...
```
```

### Template B: Silent/Data-Collection Cron (no Telegram deliverable)
```
Run these commands and persist findings:
1. [command]
2. [command]

## ⚠️ MANDATORY: Persist findings to DB
This is the primary purpose — write:
```python
INSERT INTO ...
```
```

Use Template A when the cron produces user-facing output. Use Template B when the cron is purely background data collection.

## 3. Token Budget Awareness

Each skill loaded adds its SKILL.md content to the system prompt. For the morning-briefing, 4 skills consume ~19K tokens in SKILL.md content alone (plus scripts/references loaded on-demand):

| Skill | SKILL.md chars | Est. tokens |
|-------|---------------|-------------|
| microsoft-email | 3,061 | ~765 |
| google-workspace | 19,654 | ~4,914 |
| contacts-database | 4,949 | ~1,237 |
| executive-assistant | 49,818 | ~12,455 |
| **Combined** | **77,482** | **~19,371** |

**Rule of thumb:** If skill overhead + prompt > ~50% of effective context window, expect degraded follow-through. Trim skills to only what the cron ACTUALLY uses.

## 4. DB Write Pattern Evolution

| Phase | Pattern | Problem |
|-------|---------|---------|
| May 8 | Fenced Python block at end | Agent displays code, doesn't execute |
| May 11 (before fix) | ⚠️ MANDATORY at end with execute_code() call | Agent executes DB write, skips primary output (recency bias) |
| May 11 (after fix) | "Background task: persist [metric] signal" before output section | Agent sends briefing first, then silently persists |

**Current best practice for user-facing crons:**
1. Primary deliverable instruction at TOP with 💥
2. DB write as a "Background task" section BEFORE the output format
3. DB write section header is neutral — no ⚠️ or MANDATORY (these trigger recency hijack)
4. Still include the explicit "run execute_code with this script" instruction (the code-block-alone bug from Phase 1 still applies)

## 5. Skill Loading — Don't Overload

Only load skills the cron actually needs. For the morning-briefing:
- **Needed:** `google-workspace` (calendar), `contacts-database` (contacts)
- **Not needed for the actual work:** `microsoft-email` (no Outlook checks in the briefing), large parts of `executive-assistant` (the full ops manual is loaded but only the briefing section is used)

**Principle:** A cron that loads 4 skills when it needs 2 wastes ~10K+ tokens of context that could be used for instruction quality and follow-through.

## 6. Verification Checklist

When a user reports a cron produced no useful output:
1. Did the agent write the DB signal but nothing else? → Recency bias. Check end-of-prompt structure.
2. Did the agent fail to load skills? → Check skill names exist via skill_view.
3. Did the agent attempt data collection? → Check session output for tool call evidence.
4. Was the output format positioned as "THIS IS WHAT YOU SEND" or implied?

**Proactive check — before making any cron change:** The Tier 1 PRE-TOOL CONTEXT CHECK guard prompts you to consider context before every tool call. When you're about to touch a cron job or system-architecture.md, that guard should trigger "do I need system-architect?" If it doesn't, the guard order may need review. The guard is the anti-forget mechanism; loading this skill is the correct action.

## 7. Routing Decision Flow — Never Offer D After Step 1

When a cron prompt has a multi-step routing decision for triaging items (email, WhatsApp) into kanban tasks, the flow must respect **Step 1's gatekeeping**.

### The Trap

A common pattern mixes two categorically different decisions into one branch:

```
Step 3: Relates to existing workstream?
  → YES → A (update existing task)
  → NO → determine B vs C:
    - Needs domain action → B (new task)
    - Needs Pallav's decision → C (pending)
    - Neither applies → D (output only)    ← THE TRAP
```

**D is a routing decision (create nothing). B/C are status decisions (create a task, differ only in status).** Mixing them in Step 3 lets the model re-litigate Step 1's routing commitment. When a purchase confirmation passes Step 1 ("Yes, it's in the routing table → inventory-manager"), reaches Step 3 with no matching workstream, and sees "Neither applies → D", the model uses the D exit — deciding "logging a receipt doesn't need domain action" — and drops the item.

### The Fix

Step 3's NO-match branch must be a **pure status decision** — B or C only, D structurally unreachable:

```
Step 3: Relates to existing workstream?
  → YES, clear match → A (update existing task)
  → NO match → a task gets created. Choose its status: B or C (never D).
    The item passed Step 1, so its type IS in the Routing Table and the
    mapping is mandatory. The routing decision is already made — the only
    open question is the new task's status:
    - B (status ready) — default. Logging/filing IS the domain action.
    - C (status pending) — only when Pallav must decide before the domain acts.
```

### Where D Belongs

D is still valid — just not in Step 3's NO-match branch:
- **Step 1 "No" exit** — types that aren't in the Routing Table (security alerts, casual chat, newsletters)
- **Step 3 "Yes" branch** — routine back-and-forth on an existing task that doesn't warrant a body update

### Watch: The Catch-All Row

If the Routing Table has a catch-all row (e.g. "Other actionable → joy"), that row becomes the sole judgment-call gate. If worded loosely, the model could over-match and spam tasks. Make sure the catch-all reads as "genuinely needs a domain to do something," not "anything not obviously ignorable."

## References

- `skill_view(name='system-architect', file_path='references/prompt-engineering-recency-bias.md')` — Full recency bias reference with optimization patterns
- This file is under the system-architect skill — loaded when creating/modifying cron prompts
