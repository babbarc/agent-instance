# Assumption Rampage (June 2026)

A multi-turn cycle where the agent **assumed what a web dialog offered** instead of reading it from the actual snapshot:

1. Assumed the Contacts CSV export included "Other contacts" without expanding the group selector dropdown to verify.
2. Assumed the file landed in the download path without checking whether it existed.
3. Blamed the environment ("Browserbase doesn't support downloads to local disk") instead of checking the actual dialog options first.
4. Introduced "Other contacts" as a concept the user pushed back on — wasting turns defending a framework built on assumption.

**Prevention sequence (from operate-browser SKILL.md):**
open dialog → read ALL options from snapshot → present findings → ask user → act on their direction.
