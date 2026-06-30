# Scratchpad Offloading Techniques

Research-backed approaches for preventing LLM reasoning tokens from leaking into delivered output.

## Decision Tree

```
Scratchpad leaking into output?
├─ Use native API thinking mode separation?
│  └─ DeepSeek V4 Flash: reasoning_content separate from content
│
├─ Use Output-First Inversion?
│  └─ Deliverable first, reasoning after WHY: delimiter
│
├─ Use Temp File Side-Channel?
│  └─ Write triage/plan to /tmp/hb-scratchpad-{ts}.txt via terminal()
│
└─ Suppress via prompt structure?
   ├─ Remove XML scratchpad tags
   ├─ Add output templates (Pattern A/B/C)
   └─ First-character constraint
```

## Research Grounding

- **DeepSeek V4 Flash reasoning_content:** Separate API field from content. Prompt-level `<scratchpad>` still leaks to content — both need fixes.
- **Chain of Unconscious Thought (CoUT, arXiv 2505.19756):** Proves models CAN reason internally without visible tokens — validates "think silently" isn't impossible.
- **Hidden Scratchpad Problem (Tian Pan, Apr 2026):** Scratchpad faithfulness rates 39.7–89.9%. For reasoning models on sensitive inputs: 25–41%.

## When to NOT Use Temp Files
- No `terminal` toolset enabled
- Extreme token efficiency needed
- Pure data pass-through with no analysis
