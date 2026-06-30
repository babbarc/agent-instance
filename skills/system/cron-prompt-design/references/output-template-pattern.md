# Output Template Pattern — Suppression vs Inversion

## The Three-Step Fix (Suppression)

Replace XML `<scratchpad>` tags with these three changes applied together:

### 1. Silent Planning Instructions
Replace `<scratchpad>` block with:
```
## PLAN BEFORE ACTING (think silently — never write this down)
Think through these steps internally. Do NOT include them in your response:
1. Score each item using the TRIAGE rubrics below
2. Dedup across channels (BATCH DEDUPLICATION rules)
3. Decide routing actions (ROUTING section)
4. Enrich contacts if applicable
5. Execute terminal() commands
6. Output ONLY the template below
```

### 2. Explicit Output Templates
Show the ONLY acceptable output shapes:
```
## YOUR RESPONSE RULES (read these first — they constrain your output)
Your entire response is ONE of these patterns:
**Pattern A — terminal() then summary:**
terminal("...command 1...")
🔴 Urgent item description

**Pattern B — summary only:**
🔴 Urgent item description

**Pattern C — silent:** [SILENT]
```

### 3. First-Character Constraint
```
Your first character MUST be one of: t (for terminal), 🔴, 🟡, 🔵, or [ (for [SILENT]).
```

**Important:** "Think silently" doesn't suppress token generation — it removes the fill-in-the-blank template. The real suppression is from steps 2 and 3. All three must be applied together.

## Output-First Inversion (Alternative)

Instead of suppressing reasoning, let the deliverable come first:
```
## YOUR RESPONSE
First, output terminal() calls (if any), then the emoji-bullet summary.
After the summary, you may add reasoning on a line starting with WHY:
```

**When to use:** Model leaks planning despite 3-step suppression, or truncation is a known risk.

## When NOT to Use Either Pattern

- Pure data pass-through crons with no analysis needed
- LLM-only executes terminal commands with no reasoning
- Jobs using `no_agent=True`
