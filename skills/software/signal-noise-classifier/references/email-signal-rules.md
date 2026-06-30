# Email Signal Rules

> Criteria file for the signal-noise-classifier skill. Assesses email importance by source, content, and context.
> Format: Always-Flag → Signal → Noise → Tiebreaker.

## Always-Flag Exceptions

These override all other rules:

- Security alerts (new device login, password change, 2FA, account recovery)
- Emails from close family with a direct ask or needing a response
- Anything related to an active goal

### Security alert correlation

Multiple alerts from different services within 30-60 minutes should be assessed collectively, not individually. Check: were devices/locations familiar? Do they cluster to a single session? Cross-service alerts (finance + social + bank) are often routine; all-financial-only alerts are more concerning.

## Signal Categories

| Category | Criteria |
|----------|----------|
| Financial transactions | Large purchases above configurable threshold, direct debit changes, bank alerts |
| Legal/contractual | Property correspondence, lease documents, solicitor communications |
| Tax-related | Tax authority correspondence, filing reminders, dividend notifications |
| Visa/immigration | Home Office, visa updates, appointment confirmations |
| Healthcare | Medical provider bookings or changes |
| Career | Recruiter outreach, portfolio management, interview logistics |
| Property | Estate agent communications, property updates, viewing notifications |
| Investment | Platform notifications, trading confirmations |
| Bills | Bills above configurable threshold |
| Life event correspondence | Antenatal bookings, hospital registration, visa-related comms |
| Online booking confirmations | Reservation platforms requiring confirmation click (e.g. automated booking systems) — flag but don't kanban |

## Noise Categories — Gate 1 Hard Fail

These are discarded at Gate 1 (Categorical Relevance), not passed to Gate 2 or Gate 3:

- Marketing newsletters, promotional emails, deals/discounts from any publication, Substack, Medium, Beehiiv, or mailing list — **fail at Gate 1 regardless of sender name**
- Social media notifications (LinkedIn, Twitter, Instagram digests)
- Routine delivery/shipping updates (unless high-value)
- Automated receipts below configurable threshold
- Spam, phishing, unsolicited cold emails
- Regular monthly account statements (unless anomaly flagged)

**Why Gate 1 and not later:** Newsletters have never produced a signal in this system and never will. Letting them reach Gate 2 wastes inference on state checks, and letting them reach Gate 3 wastes urgency calibration. A hard fail at Gate 1 is the token-efficient choice.

## Tiebreaker Rule

1. Relates to an active goal? → Treat as signal
2. Relates to an active tracked task? → Treat as signal
3. Sender is a known contact? → Lean toward signal
4. If unclear — err on the side of signal (over-reporting beats missing something)

## Related

- `whatsapp-signal-rules.md` — same pattern for WhatsApp
- Active goals define the current importance context
