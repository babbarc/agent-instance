# Document Placement-Cost Analysis

A principle for deciding where a rule, section, or guardrail lives in the identity/documentation stack.

## The Three Factors

Every piece of system documentation has three costs:
- **Frequency** — how often does it fire? (Every turn? Once per session? Once per week?)
- **Real estate** — how many lines/bytes does it consume?
- **Criticality** — when it fires, how important is it that the LLM knows it?

## Placement Map

| Fires | Real estate | Criticality | Best home |
|-------|------------|-------------|-----------|
| Every turn | Low (<5 lines) | High | SOUL.md (universal/generic operational) |
| Every turn | High (>5 lines) | Moderate | Skill (loaded on demand) |
| Every turn | Any | User-specific fact/preference | USER.md — but only **broad behavioural preferences**, never raw personal details |
| Per-session | Any | High | Skill specific to the task |
| Per-week | Any | Any | Cron-specific skill or inline in cron prompt |
| Rare | Any | Critical | SOUL.md (must be there when it fires) |
| Rare | Any | Low | Don't document. Remove. |

## How to Evaluate

Before writing a new section, ask:

1. **How often will this rule fire?** — Be honest. If you're creating a rule about how to handle a specific tool, ask yourself how often you use that tool per session.
2. **Does every agent need this, or just one profile?** — Universal → SOUL.md. Profile-specific operational/behavioural guidance → SOUL.md. User-specific personal preferences, correction style → USER.md.
3. **Is the rule a behavioral guardrail, a procedural how-to, or a personal preference?** — Guardrails (what to do / not do) → SOUL.md. How-to (steps, commands, workflow) → skill. Personal preferences and habits (how the user likes things done, how they correct you) → USER.md.
4. **Could this rule apply to any user, or is it tied to this specific person?** — If it only makes sense for this specific user (their preferences, their household, their habits), it belongs in USER.md — even if it feels like an operational rule. SOUL.md must be generic enough to work for any user.
5. **Is this a broad behavioural preference, or a specific personal detail about someone?** — Broad preferences about HOW to operate (check both inboxes, lead with veggie options, format numbers with £) → USER.md. Specific personal details about the user or their family (diet, DOB, phone, email, address, relationships) → contacts/ files, not USER.md. USER.md describes how to work with the user, not who they are.

## Real Examples from Session

### Example 1: Skill Integrity section (4 Jun 2026)

**The problem:** Skill Integrity section (11 lines, 4 principles) was initially placed in SOUL.md.

**The evaluation:**
- Frequency: ~1 in 5 sessions (skill_manage create/patch/merge is not a daily action)
- Real estate: 11 lines, ~500 tokens every turn
- Criticality: High when it fires, but doesn't need to be read on turns where no skill work is happening
- Universal? Yes — all agents create skills, not just Joy

**The fix:** Moved to .hermes.md as a situational trigger. Only 6 lines, loaded as a context file when the cwd is $HERMES_HOME. The frequency didn't justify SOUL.md real estate; the criticality is handled by .hermes.md being available as a project context file.

### Example 2: User's Preferences → USER.md (4 Jun 2026)

**The problem:** A "User's Preferences" section (6 lines: numbers with £ signs, food planning, people-first framing, cross-account inbox, headers preference) was in SOUL.md.

**The evaluation:**
- Frequency: Every turn (preferences affect every output)
- Real estate: 6 lines
- Criticality: High — these format/behaviour rules should fire on every output
- User-specific? Yes — these are about the user's personal communication preferences, not generic EA operational guidance

**The issue:** SOUL.md was being treated as a catch-all for "everything important," but it should be generic operational/behavioural guidance. User-specific facts belong in USER.md.

**The fix:** Moved to USER.md alongside existing entries (Draft it, Right tool, Patch management, Correction style, Upstream thinker). USER.md is the right home for all user-specific personal preferences. SOUL.md was left with only generic operational guidance that any EA profile serving any user could use.

**The distinction clarified:**
- **SOUL.md** = generic operational/behavioural guidance (Prime Directive, Kanban-First, Execution Discipline, Execution Contract, Verification Protocol, Communication format, Feedback Response). This file describes HOW the agent operates — applicable to any user. (Formerly had a companion `guards.md` for universal rules but the file was never loaded and has been deleted.)
- **USER.md** = user-specific personal preferences, correction style, habits. This file describes HOW TO WORK WITH the user — broad behavioural preferences only, no raw personal details.
- **Contacts/ files** = personal details about people (diet, DOB, phone, email, address, relationships). This is WHERE THE USER IS, not how to work with them.

### Example 3: USER.md vs Contacts Boundary (4 Jun 2026)

| **The problem:** USER.md contained specific personal details about the user and the partner — "the partner is vegetarian — lead with veggie options" and "Cross-account inbox: check both the user's and the partner's Gmail."

**The evaluation:**
- Frequency: Every turn (food planning and inbox checking are daily actions)
- Real estate: 2 entries, ~20 lines total
- Criticality: High — these drive real behaviour
- Broad preference or personal detail? "Lead with veggie options when planning food" is a broad behavioural preference. "the partner is vegetarian" is a personal detail about the partner.

**The principles applied:**
1. The dietary fact "the partner is vegetarian" was already in `contacts/partner-shah.md` line 22 (Diet: Vegetarian) — correct home.
2. The behavioural directive "lead with veggie options when planning food" belongs in USER.md as a broad preference — it tells the agent HOW to plan food, not WHO the partner is.
3. "Cross-account inbox" is a broad behavioural preference about WHICH inboxes to check — belongs in USER.md but should not name people by name: "check both the user's and their spouse's email for property, financial, legal correspondence."

**The fix:** Keep broad behavioural directives in USER.md. Ensure specific personal details reference contacts/ files rather than duplicating them. The rule: if you're naming a specific person and stating a fact about them, check if that fact is already in their contacts file — if yes, remove the duplicate from USER.md and rephrase the directive generically.

Don't put a rule in SOUL.md because "I might forget it otherwise." If it fires that rarely and isn't critical, the right answer is:
- Not documented (removed)
- Or a skill that the LLM chooses to load when needed

Fear of forgetting is a signal to evaluate if the rule is actually necessary, not a signal to increase the permanent context budget.
