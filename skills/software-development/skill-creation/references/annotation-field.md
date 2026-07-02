# Annotation Field — LLM-Optimised Skill Hints

## Purpose

The `annotation` field in SKILL.md frontmatter provides a **crisp, keyword-rich one-liner** that replaces the `description` in the `<available_skills>` block of the system prompt. It is optimised for LLM scanning — not for human readers browsing the skills directory.

The full `description` still appears when the skill is loaded via `skill_view()`.

## Why It Exists

`extract_skill_description()` in `agent/skill_utils.py` truncates descriptions at **60 characters** (line 688: `if len(desc) > 60: return desc[:57] + "..."`). Previously, 73% of skill descriptions were truncated mid-sentence, hiding trigger keywords the LLM needs to identify when to load a skill.

The annotation replaces the description in this constrained display context.

## Guidelines

### Length
- **≤57 characters** — never truncates
- **≤60 characters** — safe (the truncation threshold)
- **≥61** — will be cut to 57 + `...` — avoid

### Style (optimised for DeepSeek v4)
| Principle | Good | Bad |
|-----------|------|-----|
| Front-load the trigger word | `Structural changes: cron, profiles, DB, memory` | `Load before modifying cron jobs, profiles, DB schemas, memory tree, or system equilibrium` |
| Comma-separated keywords | `Passwords/secrets/tokens: pass-to, CDP inject` | `Mandatory pre-flight protocol for ANY work involving passwords, credentials...` |
| Concrete nouns, not prose | `Patent: search, prior art, USPTO filing` | `This skill helps you search for patents and understand prior art...` |
| Omit articles (a/an/the) | `Bookkeeping, trial balance, financial statements` | `The basics of accounting from bookkeeping to financial statements` |
| Action verb first | `Review PRs: diff, inline comments via gh` | `This is a skill for doing code review on pull requests` |

### When to Add

- **Every new skill** — mandatory. Without one, the truncated description appears in the index.
- **Existing skills** — added during annotation bulk passes.

### Fallback Chain

```
annotation field present?  →  use annotation (truncated to 60 chars if needed)
annotation absent?         →  use description (truncated to 60 chars)
description absent?        →  empty (skill name shown with no description)
```

## Example

```yaml
---
name: skill-creation
description: "Create, review, or audit a Hermes skill. Use when creating skills from scratch, reviewing existing skills for quality, or auditing the skill library for consolidation opportunities."
annotation: "Create/review/audit skills: SKILL.md rules, gates"
version: 1.0.0
---
```

In the system prompt index:
```
    - skill-creation: Create/review/audit skills: SKILL.md rules, gates
```

Instead of the old truncated version:
```
    - skill-creation: Create, review, or audit a Hermes skill. Use when creatin...
```
