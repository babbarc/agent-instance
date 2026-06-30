# Routing Flow — B/C vs D Design Pattern

## The Problem

When a routing decision flow mixes B (new task), C (pending task), and D (output only) in the same branch, the model uses D as an escape hatch for items that already passed the routing table gate.

**B and C are status decisions** (both create a task, differing only in `--status ready` vs `--status pending`).
**D is a routing decision** (no task at all).

Mixing them is categorically wrong. It lets the model re-open a decision that was already made.

## The Fix

Frame the NO-match branch as a pure status decision:

```
→ **NO match → a task gets created. Choose its status: B or C (never D).**
   D does not exist in this branch. D is Step 1's answer for types that
   aren't in the Routing Table, and the YES-branch's answer for routine
   back-and-forth. An item that reached here is a tracked type with no
   existing workstream — that is the definition of a new task.
```

## Where D Still Belongs

- **Step 1 ("No" branch)** — item type isn't in the routing table
- **Step 3 ("YES, clear match" branch)** — routine back-and-forth on an existing task

## Expert Consultation

**Claude (preferred for this pattern):** "B/C is a status decision, D is a routing decision.
They are categorically different. Removing D here costs you nothing, because every
legitimate no-task outcome is still expressible — just not at this branch."

**Gemini:** "Because Step 1 already acts as a hard gatekeeper, any item that reaches
Step 3's NO-match branch is mathematically guaranteed to be in the Routing Table.
When you ask the model to evaluate if a receipt 'needs a domain action,' it interprets
'action' too narrowly — thinking of active tasks (like calling a plumber) rather than
passive tasks (like logging a receipt)."

## Verification

Test with a one-shot purchase confirmation (Amazon order, no existing workstream match).
The model should create a task with `status ready` and the correct assignee from the
routing table, not skip to D.
