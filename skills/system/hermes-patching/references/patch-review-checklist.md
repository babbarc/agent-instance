# Patch Review Checklist — Cross-Contradiction & Quality Audit

Use this checklist when auditing an existing set of Hermes patches or reviewing a new patch before committing. Covers six dimensions.

## 1. Cross-Layer Contradiction Check

### Tool schema vs system-prompt guidance

For every constant in `agent/prompt_builder.py` that has a corresponding tool schema description, diff the two:

| Tool | System Prompt Constant | What to check |
|------|----------------------|---------------|
| `memory` (in tools/memory_tool.py) | `MEMORY_GUIDANCE` | Tool says "replace/remove require approval" but guidance says nothing about it? |
| `skill_manage` (in tools/skill_manager_tool.py) | `SKILLS_GUIDANCE` | Both say the same thing about when to create/update? Tool is now minimal after 2026-06-07 condensation — does guidance pick up the slack? |
| `clarify` (in tools/clarify_tool.py) | `WORKFLOW_GUIDANCE` (CLARIFY phase) | Clarify tool says "don't guess intent" and WORKFLOW_GUIDANCE says the same? |

**Concrete example (2026-06-20):** `memory_tool.py` description was rewritten to include "APPROVAL REQUIRED before calling: replace, remove. Ask the user first. Do NOT invoke the tool until they confirm." But `MEMORY_GUIDANCE` in `prompt_builder.py` says nothing about this — it just says "Save the 2-3 behavioral rules that must fire every turn." The LLM reading MEMORY_GUIDANCE feels encouraged to use memory freely, but destructive ops get rejected without user approval.

### Between-patch contradictions

Two patches in different files that say opposite things about the same concept:

| Patch A | Patch B | Conflict |
|---------|---------|----------|
| `background_review.py`: "Warnings, troubleshooting, and pitfalls go in `references/<topic>.md`" | `prompt_builder.py` SKILLS_GUIDANCE: "Distill aggressively — condense edge cases to **one-line warnings**, skip pitfalls that wouldn't block" | A says warnings go in references/ files. B says condense to one-line warnings (implying SKILL.md). Same content, two different locations prescribed. |

When this fires, pick the **more prescriptive** of the two and update the other to match. Background_review's "references/ only" is the stronger constraint — update SKILLS_GUIDANCE to say "condense to one-line warnings in `references/<topic>.md`."

## 2. Dead Config Scan

Check `~/.hermes/config.yaml` (or `/opt/data/config.yaml`) for settings the patched code no longer reads.

| Config key | Patched away in | Why it's dead |
|------------|----------------|---------------|
| `tool_use_enforcement` | `system_prompt.py` (2026-06-20) | The entire `_tool_use_enforcement` gating logic was removed. WORKFLOW_GUIDANCE is now unconditional. Setting does nothing. |

**Action:** Present dead settings to the user. Offer to remove or comment them out. Never leave a setting that looks live but does nothing — it's a maintenance trap for the next person.

## 3. Dead Code Scan

Check for constants, imports, or functions the patch renamed or removed but left behind as orphaned references.

| Symbol | File | Why it's dead |
|--------|------|---------------|
| `TOOL_USE_ENFORCEMENT_MODELS` | `prompt_builder.py` | Comment says "Kept for reference" but no file imports it. Was removed from `system_prompt.py` imports by the 2026-06-20 patch. |

**Detection method:** Use the AST stale-reference scan from `references/diagnosis.md`:
```python
python3 -c "
import ast
names = {n.id for n in ast.walk(ast.parse(open('/opt/hermes/agent/prompt_builder.py').read())) if isinstance(n, ast.Name) and n.id[0].isupper()}
for sym in ['TOOL_USE_ENFORCEMENT_MODELS']:
    print(f'{sym}: {\"DEFINED but check imports\" if sym in names else \"not used\"}')"
```

Then verify the symbol isn't imported anywhere:
```bash
grep -rn 'TOOL_USE_ENFORCEMENT_MODELS' /opt/hermes/agent/ --include='*.py'
```

If it's only defined and commented but never imported by any file, it's dead.

## 4. Unicode Consistency Check

The Hermes `patch` tool normalizes Unicode escapes in Python string literals (`\\u2014` → `—`). Once a file uses one style, all patches on that file should use the same style, or patch regeneration produces noisy diffs.

**Check each patched file:**
```bash
for f in approval.py clarify_tool.py memory_tool.py prompt_builder.py system_prompt.py skill_manager_tool.py background_review.py; do
    echo "=== $f ==="
    # Count escape sequences vs literal unicode chars
    escapes=$(grep -c '\\\\u[0-9a-fA-F]\\{4\\}' "/opt/hermes/$([[ $f == *.py ]] && echo "agent/$f" || echo "tools/$f" 2>/dev/null)" 2>/dev/null || grep -c '\\\\u[0-9a-fA-F]\\{4\\}' "/opt/hermes/agent/$f" 2>/dev/null)
    echo "  Escape sequences: $escapes (if 0, file uses literal chars)"
done
```

**Recommendation:** Prefer escape sequences everywhere. They survive diff regeneration and don't get byte-level normalized by the patch tool.

## 5. Regex Battery Test

For every new regex pattern in `approval.py`, verify against a test battery:

```python
import re

patterns = {
    "Gmail": r'python[23]?.*/google_api\\.py\\b.*\\bgmail (send|reply)\\b',
    "Outlook": r'python3.*mail_api\\.py\\b.*\\b(send|reply)\\b',
    # ... add all patterns
}

tests = {
    "Gmail": [
        ("python3 scripts/google_api.py gmail send", True),
        ("python3 scripts/google_api.py gmail list", False),  # not send/reply
        ("python4 google_api.py gmail send", False),  # no version match
    ],
    # ... test every pattern
}

for label, pat in patterns.items():
    for test_str, expected in tests[label]:
        actual = bool(re.search(pat, test_str, re.IGNORECASE))
        status = "OK" if actual == expected else "FAIL"
        print(f"{status}: {label} - {test_str!r} -> {actual} (expected {expected})")
```

**Checklist:**
- [ ] Word boundaries (`\\b`) used where needed to prevent partial matches (e.g., `\\bgmail\\b` not `gmail`)
- [ ] Non-capturing groups `(?:...)` used instead of capturing groups where only alternation is needed
- [ ] Path-like invocations with `/` or explicit paths vs bare command names — choose based on how the LLM actually calls these
- [ ] Each pattern rejects commands from other categories (selectivity)
- [ ] No false positives on legitimate system commands

## 6. Determinism Assessment

Score each patch on a 1-10 scale, where 10 = completely deterministic (the LLM will always make the same decision given the same input).

**What reduces determinism:**
- Vague encouragements ("be proactive", "consider saving", "prefer X")
- Overlapping guidance in two places that could conflict
- Complex conditionals the LLM must evaluate (model gates, config gates)
- Prose paragraphs the LLM must parse for actionable rules
- Instructions that contradict what a tool schema says

**What increases determinism:**
- Explicit state machines (CLARIFY/EXECUTE/BLOCKED)
- Structured sections with clear headings
- "If X then Y" rules instead of "prefer X"
- Removing guidance that encouraged guessing intent
- Moving implementational detail out of SKILL.md into references/

**Record keeping:** For patch sets, note the before/after determinism score. The 2026-06-20 set (system_prompt + prompt_builder + memory_tool patches) moved from ~5/10 (model-gated enforcement + prose guidance) to ~8/10 (unified workflow state machine + structured sections).

## Reference

Real contradictions found in the 2026-06-20 patch audit:
- Contradiction A: `memory_tool` tool description says "replace/remove require approval" but `MEMORY_GUIDANCE` doesn't mention this. Fix: add one line to MEMORY_GUIDANCE.
- Contradiction B: `background_review` says "warnings in references/" but SKILLS_GUIDANCE says "condense to one-line warnings." Fix: update SKILLS_GUIDANCE to reference the references/ rule.
- Dead config: `tool_use_enforcement: auto` in config.yaml — read by nothing after system_prompt.py patch.
- Dead code: `TOOL_USE_ENFORCEMENT_MODELS` in prompt_builder.py — defined, commented "Kept for reference," imported by nothing.
