# Kanban vs Memory Tree — Boundary

**Principle (established 5 Jun 2026):** If kanban owns task state, memory files must not duplicate it. One source of truth per fact.

## What Goes Where

| Domain | Kanban (task state) | Memory tree (reference data) |
|--------|-------------------|------------------------------|
| **Property purchase** | Status (pending/in_progress/rejected), active offer details, next steps, timeline of events, decisions made | Features, sq ft, comp sales, financials (asking price, stamp duty calc), area research, contact info for agents/solicitors |
| **Property sale** | Listing status, viewing activity, offer status, solicitor progress | Address, title/lease details, service charges, EPC, Deed of Variation records, agent details |
| **Visa application** | Application progress (% done), which pages complete/paused, next user input needed | Passport numbers, Aadhaar, DOB (goes in contacts/), visa category rules |
| **Tax filing** | Status (data gathering / submitted / filed), document collection progress | Tax reference numbers, HMRC deadlines, prior year filings |
| **Baby shower** | Venue booked, guest list sent, date confirmed | — (pure task state, no durable reference data needed) |

## Identifying Contamination

A memory file has task-state contamination if it contains any of:
- **Status indicators** at the top: "Status: 🟡 OFFER MADE", "Status: ✅ Complete"
- **Progress checklists**: `- [ ] Viewing booked`, `- [x] Offer made`
- **Next-step action items**: `TBD: Instruct solicitor`, `Next: Get AIP`
- **Session-level progress**: "✅ Completed pages, ⏸️ Paused pages"
- **Tables with ✅/⏳ status columns** for documents or tasks

## How to Clean

1. **Migrate** the state into the kanban task body — `kanban.py update <task_id> --body "..."` and `kanban.py comment <task_id> "..."` for timeline events
2. **Strip** status markers from memory file — replace tables with bullet lists, remove progress checklists, replace "Status:" lines with a one-line note pointing to kanban
3. **Delete** memory files that were *pure* task trackers (e.g. a progress page with no reference data)
4. **Keep** durable reference facts: dimensions, prices, research data, contact info, technical specs, historical records

## Verifying Cleanliness (audit checklist)

From a kanban list, for each `in_progress` / `pending` task:
- Is there a corresponding memory file with task state?
- If yes, does that memory file have status lines, checklists, or progress indicators?
- If yes, migrate to kanban and strip.

## Origin

This principle was established when a Cissbury Ring North offer was rejected — Joy updated memory files but forgot the kanban, creating a desync. User corrected: "if something is fully tracked in kanban, why have it in memory tree too?" The audit found 2 more instances (Tejal visa progress tracker, purchase-plan status columns) which were then cleaned.
