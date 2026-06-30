# Trace Before Fix

## The Trap

When the user reports a logic bug in a prompt, flow, or decision system, the instinct is to find where the failure manifests and add a bypass/exception there. This is a band-aid.

The failure point is a symptom, not the root cause.

## Step 0a — Check Existing Diagnostics First

Before writing code or tracing flows:

- Search for debugging guides, troubleshooting docs, or `references/` files related to the failing component
- Check if this is a known failure mode with a documented fix
- Look in: `references/*.md` under the relevant skill directory, `$HERMES_HOME/memory/reference/`, and the component's own tests
- Follow an existing guide step by step before innovating
- Only dive into source code if the guide doesn't cover the symptom

## Step 0b — Cross-Reference Session Search Against Raw Data

`session_search()` summaries are LLM-generated and can omit critical details. After reading a summary:

1. Read the last ~20 user messages from the raw session transcript — focus on what was unresolved at the end
2. Check tool call results from the raw transcript — the summary may skip errors or fixes
3. Only after verifying the raw transcript, synthesize and report

## Step 1 — Trace the Full Flow

Trace the full flow end-to-end before proposing any change. Read every step the item passes through. Don't stop at the first place it fails.

## Step 2 — Identify the Actual Contradiction

Two instructions that conflict, a step that duplicates another, a gate that blocks legitimate items.

## Step 3 — Plan the Minimum Change, Present Before Acting

Before writing code — sketch the minimal change. One function, one condition, one fallback path. If your plan touches infrastructure (containers, services, config files) when the symptom is in a script or tool, you've crossed a boundary. Stop and redesign.

Present the plan for approval before executing.

## Step 4 — Fix the Structure, Not the Symptom

Remove the redundant gate instead of adding a bypass. Simplify the flow instead of patching the edge case. The fix must respect the routing authority universally.

## Infrastructure Boundary Rule

When a script or tool fails:
- **Fix the script logic** — add the missing fallback, adjust the timeout, handle the edge case
- **Do NOT manage infrastructure** — never `podman start`, `systemctl`, or container management from within a tool script
- The browser-proxy is a long-lived daemon that manages Chrome lifecycle. If the tool needs the browser, navigate to a page — the proxy handles the rest. Containers are the infrastructure layer's concern, not the script's.

## Signal

You're doing it wrong if:
- Your first proposal adds a new conditional or exception
- You propose modifying the gate instead of removing it
- The user says "i don't want to add bypass for every single thing"
- You propose managing containers when the symptom is in a script
