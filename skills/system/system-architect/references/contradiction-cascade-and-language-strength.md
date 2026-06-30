# Contradiction Cascade & Language Strength Analysis

**Trigger:** Agent consistently ignores softer constraints (Execution Contract — formerly EA Posture —, MEMORY.md go-slow, USER PROFILE) in favour of action directives. Behaviour feels "jumpy" — the agent executes before asking, scopes before defining, assumes before confirming.

**Root cause theory:** The contradiction is not between two equal instructions. It's a **cascade** — multiple prompt sections at different language strengths, where the strongest-language section dominates all weaker ones regardless of positional order.

## The Cascade Model vs The Pair Model

The existing `guidance-conflict-diagnosis.md` treats conflicts as **pairs**: directive A vs directive B, resolve by adjusting positional authority.

The cascade model treats conflicts as **multi-layer**: 3+ competing directives across different prompt tiers, each with different **language strength**. Resolving a cascade requires mapping not just *what* each directive says but *how emphatically* it says it.

### Pair model (existing)
```
Tool-use enforcement          → "Make progress every turn"
MEMORY.md go-slow             → "Present plan first"
Resolution: Reframe deliverable in MEMORY.md
```

### Cascade model (this file)
```
TOOL_USE_ENFORCEMENT_GUIDANCE    → "MUST... immediately... never"         [imperative absolute]
TASK_COMPLETION_GUIDANCE         → "do not stop... keep working"           [imperative strong]
| SOUL.md EA Posture (now Execution Contract)               → "should... prefer... adjust for context"[hedged imperative]
guards.md Reflective Arch        → "state it and proceed"                  [descriptive action]
MEMORY.md                        → "always require approval"              [descriptive]
USER PROFILE                     → "go-slow, ask before acting"            [descriptive]
```

Each weaker layer hedges itself ("unless context says otherwise"). The strongest layers are absolute. The LLM obeys the strongest language first.

## Language Strength Hierarchy

Not all directives are equal. Classify each competing instruction on this scale:

| Level | Name | Language patterns | Example |
|-------|------|------------------|---------|
| **5** | **Imperative Absolute** | MUST, NEVER, NOT ACCEPTABLE, execute now, immediately | *"You MUST use your tools to take action — do not describe what you would do or plan to do"* |
| **4** | **Imperative Strong** | Do not stop, keep working, always (procedural), demand, every | *"Keep working until the task is actually complete. Do not stop"* |
| **3** | **Hedged Imperative** | Should, prefer, when possible, unless, adjust for context | *"Prefer making a reasonable default choice yourself when the decision is low-stakes"* |
| **2** | **Conditional Directive** | If X, then Y. When stuck, do Z. In case of, first check | *"When stuck: show the error and what you tried. Propose a simpler path."* |
| **1** | **Descriptive** | The user prefers, this is how, the correct flow is | *"Execution Contract: hear the need → propose approach → get explicit go-ahead → execute → report"* |

**Key insight:** A Level 5 instruction will consistently override Level 1-3 instructions even when Level 1 is positionally later in the prompt. The LLM's instruction-following machinery treats MUST/never as hard constraints and "prefer"/"should" as soft suggestions.

### Why this matters for jumpiness

The jumpy behaviour cascade is:

```
Level 5 (Absolute):   "Every response must contain tool calls or a final result"
Level 4 (Strong):     "Do not stop with a summary of what you plan to do next time"
Level 3 (Hedged):     "Propose approach → get explicit go-ahead"  [but: "direct orders get direct execution"]
Level 1 (Descriptive): "Always require approval before executing state-modifying actions"
```

Level 5 wins. The agent fires tools because the prompt says it MUST. The Level 3 (go-ahead) and Level 1 (approval) instructions are too soft to compete.

## Diagnosis Procedure

### Step 1 — Extract All Competing Directives

For each prompt section, extract the exact phrasing that bears on the target behaviour (e.g. "taking action without asking"):

| Section | Source constant/module | Exact text | Level |
|---------|----------------------|------------|-------|
| Tool-use enforcement | `TOOL_USE_ENFORCEMENT_GUIDANCE` in `prompt_builder.py` | *"You MUST use your tools to take action... execute it now... Every response should either (a) contain tool calls that make progress, or (b) deliver a final result"* | 5 |
| Finishing the job | `TASK_COMPLETION_GUIDANCE` in `prompt_builder.py` | *"Do not stop after writing a stub, a plan, or a single command. Keep working until you have actually exercised the code"* | 4 |
|| Execution Contract (formerly EA Posture) | `SOUL.md` (memory/user store) | *"Hear the need → propose approach → get explicit go-ahead → execute → report"* but also *"direct orders get direct execution"* | 3 |
| Reflective Architecture | `guards.md` (memory/user store) | *"In conversation state it and proceed"* | 2 |
|| MEMORY notes | memory store | *"Execution Contract: propose → explicit go-ahead → execute. Never skip approval."* | 1 |
| USER PROFILE | user store | *"Go-slow: one step at a time, ask before acting, never jump ahead"* | 1 |

### Step 2 — Check Positional Order vs Language Strength

Positional order (early in prompt = higher authority):
1. Tool-use enforcement (earliest)
2. guards.md
3. SOUL.md
4. MEMORY.md (in volatile tier, injected last)

Language strength order:
1. Tool-use enforcement (Level 5 — MUST/never/not acceptable)
2. TASK_COMPLETION_GUIDANCE (Level 4 — do not stop/keep working)
3. SOUL.md Execution Contract (formerly EA Posture) (Level 3 — should/prefer/unless)
4. guards.md, MEMORY, USER PROFILE (Level 1-2 — descriptive)

**In this case, positional order and language strength happen to align** (strongest language is also earliest). But they can diverge — when they do, language strength wins. A Level 5 in position 3 will beat a Level 3 in position 1.

### Step 3 — Identify the Self-Undermining Exception

Look for sections that state a constraint **and then immediately carve out an exception**. The exception is what the LLM actually follows.

| Section | Constraint | Exception | Effect |
|---------|-----------|-----------|--------|
| Execution Contract (formerly EA Posture) | *"Hear the need → propose → get explicit go-ahead"* | *"direct orders get direct execution"* | LLM classifies most requests as "direct orders" |
| Tool-use enforcement | *"EXCEPTION for investigation, debugging, and planning"* | Body says *"You MUST... immediately"* | Exception is buried, body is commanding |
| Finishing the job | *"Exception: investigation and diagnosis is NOT stubbing"* | *"keep working... do not stop"* | Same pattern — body overrides exception |
| clarify tool | *"Use when... ambiguous"* | *"Prefer making a reasonable default choice yourself"* | Encourages not asking |

### Step 4 — Map the Cascade

Draw the actual behaviour chain:

```
User says "check X" or "investigate Y"
    → TOOL_USE_ENFORCEMENT: "MUST make tool calls, not acceptable to describe intentions"
    → TASK_COMPLETION: "do not stop until complete"
    → Execution Contract: "direct orders get direct execution" → classifies as direct order
    → MEMORY: "ask before acting" → too weak, overridden by Level 5
    → USER PROFILE: "go slow" → too weak, overridden by Level 5
    → Actual behaviour: fires tool chain immediately, no permission asked
```

## Resolution Strategy

Since the strongest-language sections (`TOOL_USE_ENFORCEMENT_GUIDANCE`, `TASK_COMPLETION_GUIDANCE`) are frozen Python constants, you have three options:

### Option A — Reframe the Deliverable (lowest effort)

Add a MEMORY.md entry that reframes what counts as a "valid deliverable" under Level 5's own terms:

> *"Presenting a clear plan and asking 'shall I proceed?' IS a valid deliverable under the Tool-use enforcement rules. It satisfies the 'every response must make progress' requirement — investigation and planning are progress."*

This doesn't fight Level 5 — it claims its authority.

### Option B — Patch the Constant (moderate effort, requires restart)

Patch `prompt_builder.py` to soften the absolute language in `TOOL_USE_ENFORCEMENT_GUIDANCE`. Replace:

> *"You MUST use your tools to take action — do not describe what you would do or plan to do without actually doing it."*

With:

> *"Use your tools to take action. Planning, investigating, and presenting a plan count as valid progress — the exception on investigation overrides the action-first push below."*

And replace:

> *"Every response should either (a) contain tool calls that make progress, or (b) deliver a final result to the user. Responses that only describe intentions without acting are not acceptable."*

With:

> *"Every response should either (a) contain tool calls that make progress, (b) deliver a final result to the user, or (c) present a plan and await approval. Requests for approval are valid progress."*

See `system-prompt-patch-workflow.md` for the full patching mechanism (full-file `cp` via `99-hermes-patches`, requires container restart).

### Option C — Patch Both Constants

Patch both `TOOL_USE_ENFORCEMENT_GUIDANCE` AND `TASK_COMPLETION_GUIDANCE` to remove the strongest absolute language and replace with phrasing that explicitly permits investigation/planning/approval as valid work products.

## Canonical Example

**Symptom:** "Go slow" and "investigate X" consistently produce immediate tool chains instead of a pause-for-approval.

**Cascade found:**
- Level 5: TOOL_USE_ENFORCEMENT demands tool calls every turn
- Level 4: TASK_COMPLETION demands "keep working until complete"
- Level 3: Execution Contract (formerly EA Posture) says "propose → ask" but carves out direct orders
- Level 1: MEMORY says "ask before acting" — overridden

**Resolution path taken:** MEMORY.md reframe (Option A) + note in the USER PROFILE asserting that investigation IS valid progress and "shall I proceed?" IS a valid deliverable.

## Verification

After resolving a cascade:
1. Re-read all competing directives — do any Level 4-5 instructions still use language that contradicts the fix?
2. Test the cascade: "investigate X" → does the response pause and ask, or fire tools?
3. If still jumpy: the fix layer was too low (Level 1 attempt to override Level 5). Move up to Option B or C.

---

## Resolution Applied (June 2026)

The EA Posture cascade documented in this file was resolved via a multi-layer fix:

### What changed

| Layer | Before | After |
|-------|--------|-------|
| **TOOL_USE_ENFORCEMENT_GUIDANCE** | Level 5 absolute: "MUST... immediately... not acceptable" | Merged into WORKFLOW_GUIDANCE and removed. No more "MUST fire tools" language. |
| **TASK_COMPLETION_GUIDANCE** | Level 4 strong: "do not stop... keep working" | Merged into WORKFLOW_GUIDANCE and removed. No "do not stop with a plan" framing. |
| **WORKFLOW_GUIDANCE (5-phase ladder)** | CLARIFY \u2192 INVESTIGATE \u2192 PROPOSE \u2192 EXECUTE \u2192 BLOCKED with "Never jump INVESTIGATE\u2192EXECUTE without PROPOSE first" | Replaced with 3-state: CLARIFY \u2192 EXECUTE \u2192 BLOCKED. Clear instruction \u2192 execute directly. Ambiguous \u2192 clarify. |
| **SOUL.md EA Posture** | "Hear need \u2192 investigate \u2192 propose \u2192 go-ahead \u2192 execute" with "even if appears to be a direct command" carve-out | Replaced with **Execution Contract**: clear instruction \u2192 execute exactly what was asked. Ambiguous \u2192 clarify. State-modifying: confirm if not addressed in instruction. Never act without being asked. |
| **SOUL.md Prime Directive** | "When ambiguous: serve their goals" | Replaced with "When ambiguous: clarify \u2014 do not infer" |
| **SOUL.md Tone** | "Warm, direct, opinionated" | Changed to "Direct, concise" \u2014 removed "opinionated" |
| **SOUL.md Proactive Awareness** | "Notify the user about upcoming events at reasonable lead times" | Removed entirely (unsolicited action) |
| **Memory tool header** | "MEMORY (your personal notes)" | Changed to "MEMORY (behavioral guardrails)" to match the tool description |

### Cascade assessment post-fix

- **Level 5 absolute commands**: eliminated. No remaining instruction uses MUST/never/not acceptable language about tool-firing.
- **Level 4 strong imperatives**: replaced. WORKFLOW_GUIDANCE uses conditional/descriptive language.
- **Level 3+ hedged directives eliminated**: No more EA Posture carve-outs or self-undermining exceptions.
- **All layers now consistent**: SOUL.md Execution Contract, WORKFLOW_GUIDANCE 3-state, Memory tool labels, and USER PROFILE go-slow all agree: clarify when ambiguous, execute when clear, no extras.

### Remaining monitoring

The USER PROFILE "go-slow" entry and the new Execution Contract are now aligned. If the agent still appears "jumpy" after these changes, check whether any new prompt layers (model-specific operational guidance, skills preamble, etc.) introduced language that contradicts the fix.
