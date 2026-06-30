# Guidance Conflict Diagnosis — Intra-System-Prompt

**Trigger:** Agent behaviour loops, oscillates between competing impulses (action vs pause, verbose vs concise, investigate vs report), or fails to honour a user's explicit behavioural correction.

**Scope:** Conflicts *within* the system prompt instructions themselves — as opposed to `guidance-tool-contradiction-diagnosis.md` which covers tool-description vs guidance.

## Instruction Stack (Priority Order)

The Hermes system prompt is composed from multiple files, assembled top-to-bottom. Earlier entries have higher positional authority:

```
1. Tool-use enforcement / Finishing the job     [frozen, injected by prompt_builder]
2. SOUL.md                                      [user-editable, profile-specific]
3. MEMORY.md  (/opt/data/memories/MEMORY.md)    [user-editable, via memory tool]
```

**Rule of thumb:** Layer 1 (frozen) compels *continuous action*. Layers 2-3 (user-editable) impose *constraints and preferences*. When they conflict, the frozen layer often wins by positional authority — the agent will keep acting rather than stop to plan.

## Diagnosis Procedure

### Step 1 — Read All Source Files

Load each file and note its core directive:

| File | Core Directive |
|------|---------------|
| SOUL.md (injected) | Joy's identity: Kanban-first, execution discipline, EA posture, communication rules |
| MEMORY.md | Debug discipline, investigation pace, stop-on-frustration, pre-flight credential rules |

### Step 2 — Identify Competing Directives

Look for pairs where one instruction says "do X" and another says "do Y instead." Common conflict pairs:

- **"Make progress via tool calls every turn"** (Tool-use enforcement) **vs** **"Plan first, present to user, wait for sign-off"** (MEMORY.md investigation pace)
- **"Keep working until complete"** (Finishing the job) **vs** **"Stop after 2 failed attempts, rethink"** (MEMORY.md debugging loop rule)
- **"Every response must have tool calls or a final result"** (Tool-use enforcement) **vs** **"Do NOT fire/retry until user asks for it"** (MEMORY.md debug discipline)

### Step 3 — Determine the Fix Layer

The frozen layer (Tool-use enforcement, Finishing the job) is **not user-editable**. Fixes must go in the editable layer that is *closest to the conflict in the stack*:

| Conflict | Best Fix Layer |
|----------|---------------|
| Frozen action-edict vs MEMORY.md go-slow | MEMORY.md — add priority assertion that investigation/planning IS valid progress |
| Frozen action-edict vs SOUL.md | SOUL.md — add explicit carve-out |

### Step 4 — Precision Edits to MEMORY.md

When patching MEMORY.md to resolve a conflict, the edit must explicitly name the competing instruction and assert priority:

```
<existing rule> — do NOT <competing action>. Reporting findings IS
valid progress under the Tool-use enforcement rules.
```

This pattern works because MEMORY.md is injected late in the prompt — it has recency advantage over the frozen sections injected earlier.

## Canonical Example (June 2026)

**Symptom:** When told "go slow" or "investigate X," the agent still fires tool chains on every turn instead of presenting a plan and awaiting sign-off.

**Root cause:** "Tool-use enforcement" (frozen) says every response must contain tool calls or a final result. "Investigation pace" (MEMORY.md) says plan first, ask before proceeding. The frozen layer's positional authority wins — the agent keeps acting.

**Fix (MEMORY.md line 13):**
```
Investigation pace: one step at a time. Plan first, present to user,
wait for sign-off. Presenting a clear plan and asking "shall I proceed?"
IS a valid deliverable — the enforcement section's "make progress" rule
includes this. DO NOT assume scope or jump ahead. No tool chains
without sign-off.
```

**Key insight:** The phrase "IS a valid deliverable" explicitly bridges the frozen requirement (every response must deliver a result) with the MEMORY.md requirement (plan before acting). The fix doesn't fight the frozen layer — it reframes what counts as a deliverable.

## Verification

After any MEMORY.md edit to resolve a guidance conflict:
1. Re-read the edited line — does it explicitly name the competing instruction?
2. Does it reframe the deliverable rather than try to override the frozen layer?
3. Run a dry-run scenario: "go slow, check X" — would the edit change how you respond?
