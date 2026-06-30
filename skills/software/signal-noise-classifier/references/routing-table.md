# Routing Table

> Maps signal-noise-classifier judgments to pipeline actions.
> Judgment → Action → Specialist notification.

## Routing Map

| Judgment | Action | Notify specialist |
|----------|--------|-------------------|
| Statement, bill, invoice | Ingest via document pipeline + create processing task | Finance specialist |
| Contract or legal document | Ingest via document pipeline + create review task | Legal specialist |
| Security alert | Flag immediately in output (no specialist) | None — user sees it |
| Needs a reply | Draft reply, save for approval | None |
| Informational (quote received, status update) | Include in briefing (1-2 lines) | None |
| Purchase or order confirmation | Log to purchases database + create processing task | Inventory specialist |
| Trade confirmation, investment notification | Flag in output | None |
| Appointment or calendar change | Flag in output (brief mention) | None |

## Gmail Items

After judgment, check for attachments:

- **Has attachment + statement/bill/contract:** Download via document pipeline (`ingest_document.py`), file to archive, create specialist task
- **Has attachment + other:** Flag that the item has an attachment worth reviewing
- **No attachment:** Include in output based on judgment

## WhatsApp Items

WhatsApp messages don't produce files to ingest:

- **Needs a reply:** Flag message preview + offer draft
- **Informational:** Brief mention in output
- **Noise:** Skip entirely

## Output Format

Log each routing decision internally for audit:

```
Item: <id or preview>
  Source: <gmail / whatsapp / file>
  Judgment: <important / noise / ambiguous>
  Action: <ingest / kanban / flag / skip / draft>
  Specialist: <specialist-name / none>
```
