# Known Rendering Artifacts (Gemini → Text)

When Gemini returns a prompt rewrite, these artifacts commonly appear in the text conversion:

## XML tags inside markdown lists
Gemini outputs `<scratchpad>` tags inside numbered lists (1. ... 2. ...). The text conversion eats the inner content, leaving empty tags. Fix: break XML tags flush to the left margin, outside any list formatting.

## Angle-bracket placeholders stripped
Placeholders like `<action>`, `<summary>`, `<time>` are interpreted as HTML tags and removed, leaving `"📅 :  at "`. Fix: use a different delimiter (curly braces `{action}`, pipe notation `|action|`) or write the line with words instead of placeholders (e.g. "action name at time").

## Example commands truncated
Long `terminal("...")` example commands may be cut mid-string when they contain nested quotes or special characters. Always verify the full command rendered.

## Success/failure reporting formats
The calendar "On success → report: 📅 ..." pattern often gets simplified to just the emoji without the format string. Verify explicitly.

## Guardrail sentences dropped
Negative constraints ("Never act on speculative chat", "Never create new contact files") are fragile — they're easy to trim in a "flattening" pass. Always check their presence in the final rewrite.

## New structural features injected
Gemini may introduce `<analysis>` or `<scratchpad>` XML blocks, alternative emoji schemes, or restructured output formats that weren't in the original prompt. The user did not ask for these. Reject them unless they explicitly signed off.
