# Scheduler Preamble Override

The cron scheduler injects this preamble before every cron prompt:
> Just produce your report/output as your final response and the system handles the rest.

This biases the LLM toward text-only output — it skips tool calls entirely.

## How to Counter It

1. **Open with a strong action directive:** First line of prompt must be a terminal() command or an explicit "MUST call terminal()" rule.
2. **Use terminal() command format** in rules (not backtick docs) so the LLM reads them as tool calls, not reference material.
3. **Add a rule:** "CRITICAL OVERRIDE: You MUST call terminal() to execute routing actions before writing the summary."
4. **Frame the task as "execute actions, then report"** not "write a report."
