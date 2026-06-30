# Cron Prompt Assessment Protocol

Systematic methodology for auditing cron prompts on two axes: prompt quality and preamble script injection opportunities.

## The Two-Axis Framework

### Aim 1 — Prompt Quality
- **Token efficiency** — How much is procedural instructions vs decision-making? Procedural instructions can move to a script.
- **LLM consistency** — Unambiguous instructions? Any forward references between sections?
- **Hallucination risk** — Empty failure gates? Fabricated date substitution?
- **Short-circuit placement** — Is the "nothing to report" gate before or after the decision layer?

### Aim 2 — Script Injection
- **What could move to a preamble script?** The script runs before the LLM prompt; its stdout is injected as context.
- **Token ROI** — Moving 500 chars to a script saves ~125 tokens/run × frequency.

## Assessment Procedure

1. **Gather materials** — Read full prompt from jobs.json, note frequency, toolsets, skills loaded.
2. **Scan for procedural instructions** — Every terminal() call is a script injection candidate.
3. **Scan for hallucination risks** — Date substitution, forward references, unguarded paths, missing short-circuit.
4. **Evaluate script candidates** — Data-source count, branching, output volume, token run cost.
5. **Cross-cron data overlap** — Another cron already covering this data at higher frequency?
6. **Alignment checks** — Data-window vs scoring rule match, injected vs consumed data, output priority for every action type.
