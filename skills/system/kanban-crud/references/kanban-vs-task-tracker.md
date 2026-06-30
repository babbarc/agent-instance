# What "Kanban" Means in Hermes

**Short version:** Our kanban is a task tracker with visual status columns. It is not a kanban system in the Toyota/Lean sense. The name describes the board metaphor, not the strict practices.

## What Classic Kanban Requires (That We Don't Do)

| Practice | Classic kanban | Our system |
|----------|---------------|------------|
| **Pull** | Work pulled when capacity available | Tasks created freely, no capacity gate |
| **WIP limits** | Hard caps per column | No caps — any number can be `in_progress` |
| **Flow metrics** | Cycle time, throughput, lead time tracked | No metrics |
| **Explicit policies** | Written rules for every state transition | Status transitions are freeform |
| **Feedback loops** | Standups, reviews, retrospectives | Heartbeat cron is the only loop |

## Why This Is Fine

The constraints kanban solves — team context-switching, bottleneck management, hidden inventory — don't apply to a single AI assistant:

- **No context-switching cost** — 20 `in_progress` tasks doesn't degrade my attention
- **No hidden inventory** — the kanban list shows everything
- **No shared bottleneck** — I'm the only worker; my capacity is effectively unlimited
- **No need for flow predictability** — stakeholders are just the user, who sees the board directly

## When to Think "Kanban" (the Metaphor)

Use the board metaphor for:
- **Visual status** — columns (pending → in_progress → done) give a one-shot view of what's active
- **Kanban-first discipline** — read kanban before digging into files; update kanban before touching memory
- **Task-as-card** — each workstream is one card with body, assignee, priority, deadline
- **LINKS** — parent→child dependencies between workstreams

## When to Think "Task Tracker" (the Tool)

Use task-tracker thinking for:
- **Creating tasks** — `kanban.py add` validates title, generates readable ID
- **CRUD operations** — `kanban.py` CLI is the only interface; never raw SQL
- **Deadlines** — stored as column, surfaced by heartbeat, no auto-escalation
- **Active task filter** — `kanban.py list --active` is the canonical query for the heartbeat script; no raw SQL WHERE clauses
- **Table output with urgency** — `kanban.py list --format table` includes colour-coded deadline warnings; used by `heartbeat-data.sh`
- **Body opening convention** — first 80 chars must be descriptive for workstream matching; `kanban.py` warns on noise patterns (`## Status:`, etc.)
- **Bulk operations** — when seeding 3+ records with the same pattern, raw SQL is acceptable (document as exception)

## Origin

Established 6 Jun 2026 — user asked about adding deadlines to kanban, then observed: "we really need a task tracker with visual status." Correct insight: the classic kanban tooling would add WIP limits and flow analytics that serve no purpose here. Keep the name, drop the dogma.
