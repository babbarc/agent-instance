# Skill Library Health — Instance Data Distillation

> Run as part of the periodic Brain Architecture Audit when the learned skill count exceeds 35 or the average line count exceeds 250.

## Process

### 1. Inventory learned skills

Cross-reference active skills against base and optional Hermes skill packs:

```bash
comm -13 <(cat /opt/hermes/skills /opt/hermes/optional-skills | xargs -I{} find {} -name 'SKILL.md' | sed 's|.*/skills/||; s|/optional-skills/||; s|/SKILL\.md$||' | sort -u) <(find skills -name 'SKILL.md' | sed 's|^skills/||; s|/SKILL\.md$||' | sort)
```

### 2. Check each learned skill against 5 principles

1. **Generic** — Any names, amounts, dates, JIDs, project paths? → move to reference
2. **Clean** — Short sections, numbered steps, one-pass LLM parse? → restructure
3. **Distilled** — Any postmortems, debug journeys, date-stamped logs? → distill
4. **Deterministic** — Any "consider this" or "you may want to"? → replace with exact steps
5. **No duplication** — Does this overlap with another skill? → merge

### 3. Classify and prioritize

| Class | Criteria | Action |
|-------|----------|--------|
| ✅ **Clean** | Passes all 5 checks, <300 lines | Keep as-is |
| 🟡 **Needs minor distill** | Some example instance data, <400 lines | Patch remove personal data |
| 🔴 **Heavy bloat** | Instance data, postmortems, >400 lines | Rewrite SKILL.md, move instance data to references |
| 📦 **Merge candidate** | Overlaps with another skill | Absorb into umbrella via skill_manage delete with absorbed_into |

### 4. Execution order

1. **Distill first** — strip instance data from worst offenders (move to reference files)
2. **Merge** — absorbing overlapping skills into umbrella skills
3. **Prune** — delete truly stale skills with `absorbed_into=""`

### 5. Verification

After changes:

```bash
# No personal data remains
grep -l "the user\\|the partner\\|user@email.com\\|partner@email.com\\|agent@system.local" skills/*/SKILL.md

# Line counts make sense
find skills -name 'SKILL.md' -exec wc -l {} \; | sort -rn | head -20
```

### Delegation pattern for bulk work

For distillation of 3+ skills, spawn parallel subagents each responsible for one skill or one cluster:

```
delegate_task(
  tasks=[{goal: "Distill skill X", ...}, {goal: "Distill skill Y", ...}]
)
```

Each subagent reads the SKILL.md, writes the distilled version, and verifies. This works because each distillation is independent.
