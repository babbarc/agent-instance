# Prompt Engineering — Recency Bias & Instruction Structure

## Core Principle
All decoder-only transformers (DeepSeek, Claude, GPT, Llama) exhibit **recency bias** — information at the end of the prompt is overweighted, material in the middle gets attenuated. Confirmed by "Lost in the Middle" (Liu et al. 2023). This is not model-specific.

## What Happens
When instructions are structured as:
```
Beginning: Generate [briefing/etc.]
Middle:    Data sources, checklist, format template...
End:       ⚠️ MANDATORY: Do this thing (all-caps, emoji, "MUST")
```
The AI focuses on the end. Emphasis markers (⚠️, MUST, NOT optional) hijack recency bias harder than plain text.

## Optimization Patterns

### a) Front-load the primary deliverable
```
❌ [Setup] → [Middle] → [IMPORTANT: do the thing]
✅ 💥 YOUR OUTPUT MUST BE [format]. [Setup] → [Instructions] → [Background step]
```

### b) Use syntactic structure over emphasis language
```
❌ ⚠️ MANDATORY: You MUST do this thing now
✅ ## Background task (run after delivering your main output)
```
Plain section headers don't trigger recency hijack. Emphasis markers do.

### c) Single explicit output instruction, not implied
```
❌ Format: [template]          (implies template IS the output)
✅ Send exactly this as your response, nothing more: [template]
```

### d) End-of-prompt as reasoning scaffolding
```
❌ [Long instructions] → [Do the thing]
✅ [Do the thing] → Reason step-by-step: first X, then Y, finally persist Z
```
If the most important instruction must be last, chain it with "First… then… finally…"

### e) Token budget awareness
If skill overhead + instructions exceed ~50% of effective context, expect degraded follow-through. The "do the thing" signal gets buried under noise.

## Checklist for New Cron Prompts
1. Primary output instruction is at the VERY TOP with 💥 or similar
2. "MANDATORY" / "MUST" / "⚠️" only used for actual critical path, not background tasks
3. DB writes / side effects are framed as "Background: do this after delivering your output"
4. Output format section says "THIS IS WHAT YOU SEND" not just "Format:"
5. Skills loaded match what the task actually needs — no overloading

## Cron Prompt Architecture — Mechanics vs Intelligence

Cron prompts have two layers that must NOT be mixed:

**Phase 1 — Mechanics (specific, stable commands):**
- Exact script paths, account names, API calls
- Known Gmail search patterns
- Tools to run and how to run them
- These change rarely and are safe to hardcode

**Phase 2 — Intelligence (generic, evolving context):**
- "What does the user need right now?" — NO hardcoded life facts
- Trust the agent's memory, recent sessions, life-goals, and kanban tasks
- Ask open-ended questions: "Any birthdays upcoming? Projects stalled? Deadlines approaching?"
- The agent fills in specifics from its knowledge — don't bake life details into the prompt

**Why this matters:**
- Hardcoded life facts go stale in weeks (pregnancy progresses, birthdays pass, projects change)
- A prompt that says "check what's coming up" works today AND next year
- The agent has access to memory and sessions — trust that instead of enumerating life details

## Specialist Knowledge Location — Single Source of Truth

Domain-specific knowledge (categorisation rules, merchant mappings, edge cases) MUST live in exactly ONE place:

✅ **Specialist profile's SOUL.md** (e.g. `/opt/data/profiles/ca-expert/SOUL.md`) — the single source
✅ Task body — keep minimal (file paths, source, amount, one-liner instruction)
❌ Heartbeat cron prompt — do NOT embed categorisation rules here
❌ Pipeline skills (finance-tracker, etc.) — do NOT duplicate the full category table
❌ Multiple reference files with the same merchant list — leads to drift

**Rule:** If you're writing the same merchant-to-category mapping in more than one file, stop. Put it in the specialist's SOUL.md and reference it from there. Every duplicate is a future correction that will only be applied to one of the copies.
