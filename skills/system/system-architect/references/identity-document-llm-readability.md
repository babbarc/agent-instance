# Identity Document LLM-Readability Checklist

An identity document (SOUL.md) fires every turn as part of the system prompt. It must be parseable by an LLM in a single pass with no ambiguity.

The general audit methodology lives in `identity-prompt-audit.md` (duplication, compression, firing-frequency). This file supplements it with **structural and semantic patterns** that cause LLMs to guess wrong.

---

## 1. Structural Naming Collisions

Two sections with overlapping names force the LLM to disambiguate every turn.

**Detect:** Search for headings sharing a root word ("Execution", "Memory", "Work").
**Test:** Can an LLM distinguish them from the heading alone? If the distinction requires reading both bodies to guess, they're colliding.
**Fix:** Rename one to signal its distinct purpose. (e.g. `Execution Discipline` → `Work Style`)

---

## 2. Self-Contradictory Frames

A single sentence that says "don't do X, but do X" requires the LLM to parse qualifiers mid-scan.

**Detect:** `"don't [verb] from A, but do [verb] the B"` — the same verb appears with different qualifiers.
**Test:** Can you read the sentence left-to-right without backtracking? If you need to reach the qualifier at the end to understand the verb, it's a double-negative frame.
**Fix:** Restructure to a single positive instruction:
  > Before: "Don't investigate from first principles, but do investigate the current situation"
  > After: "Load the skill first, then assess current state before proposing changes"

---

## 3. Ambiguous Scope Qualifiers

A rule that says "before X, do Y" but uses an undefined scope word for X.

**Detect:** Words like "strategic", "significant", "major", "complex", "sensitive" — adjectives that depend on the LLM's judgment rather than an observable trigger.
**Test:** Would two different LLM runs disagree on whether the rule applies to the current situation? If yes, the qualifier is ambiguous.
**Fix:** Replace with concrete triggers: "Before stating a project status, answering a timeline question, or making a recommendation..."

---

## 4. Vague Instructions

A rule that names an action but doesn't say what tool or destination to use.

**Detect:** "flag it", "note it", "remember this", "update accordingly", "handle it" — verbs without a destination.
**Test:** Can you follow the instruction using a specific tool? If not, the LLM will fabricate method.
**Fix:** Add the destination: "flag it → add a kanban comment", "note it → write to memory/<domain>/<topic>.md"

---

## 5. Action-Source Tension (Cross-Section Contradiction)

A rule in one section says "always do X", and another rule says "never do X". The LLM must pick one.

**Detect:** Compare rules across sections for contradictory verbs. Common sources:
  - Kanban "propose a task on first mention" vs Execution Contract "never act without being asked"
  - Storage Routing "write before any other action" vs Execution Contract "never act without being asked"
  - Verification Protocol "exhaust all sources first" vs Work Style "one change at a time"
**Test:** When both rules apply to the same situation, which wins? If the answer isn't explicit, the LLM will choose based on position in the document (recency bias) or section formality.
**Fix:** Add an explicit exception line to one of the rules: "Task proposals are the one exception to 'never act without being asked'."

---

## 6. Duplicate Sections Claiming Different Scopes

If section B says the same thing as section A but with slightly different wording, the LLM treats them as conflicting guidance.

**Detect:** Two sections that could be merged into one. (e.g. `Memory Access` and `Storage Routing → Reference facts` saying the same QMD/read_file guidance)
**Test:** Delete section B. Does section A still cover all use cases it referred to? If yes, B was a duplicate.
**Fix:** Absorb unique content from B into A (if any), then remove B.

---

## 7. Negative Framing

A rule that tells the LLM what NOT to do, rather than what TO do.

**Detect:** "No X", "Never do Y", "Don't Z" — especially when X/Y/Z are rare enough that the LLM wouldn't naturally do them.
**Test:** Remove the negative frame. Replace with "What should I do instead?" If the answer is the same thing, the negative was noise. If there's no positive alternative, the negative is a fossilized correction.
**Fix:** Replace with positive instruction: "No silence-fixing" → "Stay present." / "No glib language" → "Direct, concise."

---

## 8. Ambiguous Timing or Sequencing

A rule that says "wait for X" without defining X unambiguously.

**Detect:** "next message", "first response", "when appropriate", "in due course" — time references without an objective marker.
**Test:** Can you determine when the condition is met without reading the LLM's mind?
**Fix:** Explicit the trigger: "Let their next message guide you" → "The user's next direct instruction signals readiness. Until then, wait."

---

## 9. Terminology Inconsistency

Using the fully-qualified tool/system name in some places and a short form in others.

**Detect:** Cross-section grep for the same entity: "mcp_qmd_query" in one place, "QMD" in another. Or "kanban task" vs "kanban item".
**Fix:** Pick one form and use it throughout. Short form is better for prose (faster scan). Fully-qualified names belong in technical sections, not identity prose.

---

## 10. Instruction Scatter

A single behavioral intent spread across multiple sections requires the LLM to assemble it.

**Detect:** A behavior that has its own named section but also appears in another section's preamble or footnote. (e.g. Memory Access as a separate section when Storage Routing already covers it)
**Fix:** Merge into the primary section. A rule should live exactly once.

---

## Session Context

This checklist was developed June 2026 during a full SOUL.md audit that found:

| Pattern | Instance Found | Fix |
|---------|---------------|-----|
| Structural naming collision | Execution Discipline vs Execution Contract | Renamed → Work Style |
| Self-contradictory frame | "Don't investigate from first principles, but do investigate current situation" | Single positive sentence |
| Ambiguous scope | "strategic questions" in Verification Protocol | Concrete triggers: status/timeline/recommendation |
| Vague instruction | "flag it" in No-Send Rule | "flag it → kanban comment or reference file" |
| Action-source tension | Kanban "propose task" vs "never act without being asked" | Explicit exception carved |
| Duplicate section | Memory Access identical to Storage Routing last line | Merged into Storage Routing, section removed |
| Negative framing | "No silence-fixing" | "Stay present." |
| Ambiguous timing | "Let their next message guide you" | "User's next direct instruction signals readiness" |
| Terminology inconsistency | "mcp_qmd_query" in prose | "QMD" |
| Instruction scatter | QMD guidance in both Storage Routing and Memory Access | Single point in Storage Routing |
