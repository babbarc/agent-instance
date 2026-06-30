# Workflow Phase State Machine — System Prompt Design

## The CLARIFY-First Principle

When designing a system prompt's instruction stack, the first phase must always be **ambiguity resolution**, not investigation. Rationale:

- **Ambiguous instructions** are the model's primary failure mode. Without a CLARIFY phase, the model guesses intent — and guesses wrong.
- **Investigation without clarity** wastes tool calls. Gathering data about the wrong thing costs more tokens than asking a 5-word question first.
- **Recency matters.** CLARIFY as phase 0 (re-enterable) means the model can always loop back when new ambiguity surfaces mid-task.

## The 5-Phase State Machine

```
CLARIFY ← re-enter when ambiguity surfaces
   │ clear
   ▼
INVESTIGATE
   │ findings + plan
   ▼
PROPOSE → "Shall I proceed?" → yes/thumbs-up = go
   │                        → ambiguous = stay in PROPOSE
   ▼
EXECUTE
   │ tool/network fails
   ▼
BLOCKED → report exact error, stop
```

## Design Rules

1. **CLARIFY is phase 0, not phase 1.** It's a meta-phase the model enters before and during the linear flow. The model should feel free to ask for clarification at any time.

2. **Each phase has an explicit endpoint.** INVESTIGATE ends with "findings + plan" (the model stops here). PROPOSE ends with user approval (ambiguous = stay). EXECUTE ends with a delivered result. BLOCKED ends with a reported error.

3. **Phase boundaries are strict.** Never jump INVESTIGATE → EXECUTE without PROPOSE first. This is the single most common violation — the model investigates, formulates a plan silently, and starts executing without asking.

4. **Ambiguous signals are NOT approval.** Only "yes" or a thumbs-up counts as go-ahead. Silence, "okay", "sure", or "hmm" are not approval signals.

## When to Add CLARIFY

| Context | CLARIFY critical? | Why |
|---------|------------------|-----|
| User gives multi-step instructions | Yes | Steps may have implicit dependencies or ambiguous ordering |
| User says "check X" or "look at Y" without verb | Yes | "Check" could mean read, summarize, compare, or edit |
| User references a tool/codebase implicitly | Yes | "Fix the bug" — which bug? Where? |
| User gives a single concrete command | No | "Run this command" or "read this file" |
| User says "go ahead" or "proceed" | No | Already in the approval signal |
| Tool returned unexpected results | Maybe | Let the model decide if the new data changes the task scope |

## Example — With vs Without CLARIFY

**Without CLARIFY:**
```
User: "Check my expenses"
Model: *investigates immediately* → reads financial data → discovers
       user meant "check the car expense account, not personal"
       → wasted tool calls on the wrong data source
```

**With CLARIFY:**
```
User: "Check my expenses"
Model: "Which expense account? Personal, car, or business?"
User: "Car expenses"
Model: *investigates the correct data source* → one round trip
```

## Implementation Pattern

In Python constants (like `WORKFLOW_GUIDANCE`), encode CLARIFY as:

```
"0. CLARIFY — If ambiguous, ask. Do not guess the user's intent.\n"
```

And state re-enterability:

```
"You can re-enter CLARIFY any time."
```

Do NOT gate this behind model-family checks (deepseek-only, gpt-only). Ambiguity is not model-specific — every model benefits from explicit permission to ask.

---

## Migration: 5-Phase \u2192 3-State (June 2026)

The original 5-phase state machine was replaced with a 3-state model for sessions where the user prefers direct execution over investigation+proposal.

### Motivation

The 5-phase model was designed for a workflow where every action requires investigation and explicit approval. Some users found this pattern slow and indirect — they want clear instructions executed directly without an intermediate proposal step.

### The 3-State Model

```
CLARIFY — Requirements are ambiguous. Ask precise questions until certain.
         Do not guess intent. Do not act.
             │
             └── clear? ──► EXECUTE — Execute exactly what was asked.
                                        No investigation, no proposal,
                                        no extra steps.
             │
             └── tool/network fails? ──► BLOCKED — Report exact error.
                                                     Ask for direction.
```

### Key differences

| Aspect | 5-Phase (original) | 3-State (current) |
|--------|--------------------|--------------------|
| Phases | 5 (CLARIFY+INVESTIGATE+PROPOSE+EXECUTE+BLOCKED) | 3 (CLARIFY+EXECUTE+BLOCKED) |
| Investigation | Mandatory between CLARIFY and PROPOSE | Only when instruction is genuinely ambiguous |
| Proposal | Required before execution | Eliminated — clear instructions get direct execution |
| Approval | Every state-modifying action needs explicit go-ahead | State-modifying: confirm only if not addressed in instruction |
| Scope | Encouraged investigation of adjacent context | Forbidden — "never add scope you weren't asked for" |
| Proactivity | EA Posture included investigation+proposal steps | Removed entirely |

### When to use which

- **5-Phase model**: strategic tasks, multi-step workflows, delegated work, tasks where scope is unclear
- **3-State model**: direct commands, mechanical tasks, clear single-step instructions, users who prefer concise execution

The active mode is determined by SOUL.md's identity document — the primary profile runs the 3-State model, while Kanban-worker profiles may still use the 5-Phase model for delegated tasks.

### Design rules preserved across both models

- CLARIFY is always phase 0 / re-enterable
- Ambiguous signals are NOT approval (only yes/thumbs-up counts)
- BLOCKED reports exact failure and stops
- Never substitute fabricated output for blocked results
