# Document Signal Rules

> Criteria file for the signal-noise-classifier skill. Used by the weekly local scan to assess document importance.
> Format follows the framework's standard categories.

## Always-Flag Exceptions

These override all other rules. If any of these are true, the item is IMPORTANT regardless of anything else:

- PDFs from known property-related sources (solicitors, estate agents, lease documents)
- Passports, visa documents, BRP copies, or identity documents
- Anything in a subfolder that matches an active goal from life-goals.md

## Signal Categories

Items matching any of these should be ingested:

| Category | File types | Criteria |
|----------|------------|----------|
| Property documents | PDF, DOC, DOCX | Sale contracts, lease agreements, service charge docs, ground rent invoices |
| Financial statements | PDF, XLS, XLSX | Bank statements, investment summaries, tax certificates |
| Bills and invoices | PDF | Energy bills, council tax, insurance docs |
| Legal documents | PDF, DOC, DOCX | Contracts, agreements, terms and conditions |
| Identity documents | PDF, JPG, PNG | Passports, BRP, visas, driving licence |
| Personal records | PDF, JPG, PNG | Medical records, certificates, educational docs |

## Noise Categories

Items matching any of these should be SKIPPED (not ingested):

- Temporary or cache files (*.tmp, ~$*, .DS_Store, Thumbs.db)
- Files already ingested (same filename exists in .hermes-docs)
- General reference materials not tied to any active goal
- Duplicates of existing documents

## Tiebreaker Rule

When a document doesn't clearly match signal or noise:

1. Check the subfolder — if it's in a named subfolder (e.g., "Solicitor", "Bank Statements", "Property"), it's likely important
2. Check if it relates to an **active goal** from life-goals.md — if yes, treat as signal
3. If the file is a PDF larger than 10KB, lean toward signal (PDFs are rarely throwaway)
4. If unclear, flag it — better to over-ingest than lose a document

## Related

- `email-signal-rules.md` — same pattern for email
- `life-goals.md` — active goals to cross-reference against
