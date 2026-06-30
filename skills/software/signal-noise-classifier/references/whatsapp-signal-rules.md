# WhatsApp Signal Rules

> Criteria file for the signal-noise-classifier skill. Assesses WhatsApp message importance by sender, content, and context.
> Format: Always-Flag → Signal → Noise → Tiebreaker.

## Always-Flag Exceptions

These override all other rules:

- Messages from primary family contacts that need a response or decision
- Anything related to an active goal
- Status updates about active life events (visa applications, family paperwork)

## Signal Categories

Report items matching any of these:

- Time-sensitive family matters needing a decision or action today
- Plans changing (cancellations, reschedules, new commitments)
- Direct questions addressed to the user that need a response
- Anything urgent — judged by language, context, or sender relationship
- Headhunters and recruiters (job opportunities, interview scheduling)
- Interview logistics (confirmations, prep, follow-ups)

## Noise Categories

Skip these:

- Casual chat or social banter between friends
- Memes, photos, videos, gifs without actionable context
- Group banter without direct relevance to the user
- Routine check-ins ("good morning", "how are you") without a specific ask
- Broadcast messages and newsletters

## Tiebreaker Rule

1. Relates to an active goal? → Treat as signal
2. Sender is a known close contact (family, close friend)? → Lean toward signal
3. If unclear — err on the side of signal (over-reporting beats missing something)

## Related

- `email-signal-rules.md` — same pattern for email
- Active goals define the current importance context
