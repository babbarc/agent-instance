# Testing Designed Workflows

When asked to verify or test a system, you MUST test the EXISTING designed
workflow — not invent your own approach.

## Steps

1. **Find the designed workflow.** Read the relevant skill, reference doc,
   or SKILL.md that governs the system under test. The designed workflow is
   the sequence of steps documented there.

2. **Map each step to a test.** For each step in the workflow, plan one
   test that proves it works end-to-end. The test executes the exact same
   mechanism the workflow uses — not a substitute.

3. **Execute in order.** Test step 1 before step 2. If step 1 fails, step 2
   is moot — don't test it. Report the failure at the failing step.

4. **Report results per step.** For each step state:
   - The step's input (what the workflow expects)
   - The step's actual output
   - Whether it matches the expected outcome

5. **Stop when you have an answer.** Do NOT chase tangents (identifying who
   a person is, investigating why something failed historically, exploring
   alternative approaches). If the test reveals a bug, report it. Do NOT
   fix it mid-test unless asked.

## What NOT to do

- Do NOT invent alternative resolution paths. If the workflow says "the
  pre-run script resolves JIDs via lid-mapping", test that path — don't
  grep for pushNames or search by name.
- Do NOT go deeper than the workflow specifies. If the workflow stops at
  "flag as !!UNKNOWN:!!", stop there. Don't investigate who the person is.
- Do NOT substitute your own judgment for the workflow's decision gates.
  If the workflow says "skip unless !!UNKNOWN:!!", test that gate — don't
  decide for yourself whether to skip.
- **Do NOT declare success without verifying.** Saying "✅ Correctly
  unresolved — skip" without checking whether the pre-run script actually
  ran against the data is a false pass. Verify that the designed mechanism
  produced the expected output — not that the output happens to match your
  assumption.
- **Do NOT test with substitutes.** If the workflow processes through a
  specific file (`deltas.ndjson`), test with that file, not with an
  ad-hoc grep of the same data. Using different tools (grep vs the actual
  pre-run script) exercises different code paths and doesn't validate the
  workflow.
- **Do NOT chase tangents during a test.** If the test reveals an unknown
  contact, the designed workflow's answer is "flag as !!UNKNOWN:!!".
  Investigating who they are (searching Google Contacts by name, reading
  session history) is a separate task, not part of the test. Complete the
  test, report the result, then ask if the user wants you to investigate
  the unknown.

## When to deviate (rare)

Only deviate from the designed workflow when:
- A step physically cannot execute (binary missing, file not found, API down)
- The user explicitly asks you to try a different approach

## Rationale

Ad-hoc testing produces inconsistent results and wastes cycles on
tangents that don't validate the actual system. The designed workflow
was designed by someone who understood the system — testing it as-is
is the only way to know if it works in production.
