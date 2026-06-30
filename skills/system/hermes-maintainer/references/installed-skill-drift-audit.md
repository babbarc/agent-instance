# Installed Skill Drift Audit

When checking whether installed skills have been modified:

## Detection

```bash
# Check all base Hermes skills
cd /opt/data
for f in $(find /opt/hermes/skills -name 'SKILL.md' | sed 's|/opt/hermes/skills/||'); do
  if [ -f "skills/$f" ]; then
    diff -q /opt/hermes/skills/$f skills/$f 2>/dev/null || echo "MODIFIED: $f"
  fi
done

# Check optional skills
for f in $(find /opt/hermes/optional-skills -name 'SKILL.md' | sed 's|/opt/hermes/optional-skills/||'); do
  if [ -f "skills/$f" ]; then
    diff -q /opt/hermes/optional-skills/$f skills/$f 2>/dev/null || echo "MODIFIED: $f"
  fi
done
```

## Remediation Workflow

For each modified skill, classify the changes:

1. **Software version tracking** — CLI flags that changed, auth commands that evolved. Just revert to base.
2. **Instance-specific config** — custom paths, account names, credential architecture. Extract to a reference file under the appropriate learned skill, then revert.
3. **Workflow improvements** — useful debugging steps, extra instructions. Extract to the learned skill's references/ directory, add a pointer from the umbrella's SKILL.md references section, then revert.
4. **Reference files added** — supporting docs placed in the installed skill's directory. Move to the corresponding learned skill (system-architect for architecture docs, credential-pre-flight for security docs, etc.), then revert.

Never leave a modified installed skill — either the content was worth saving (in which case extract it to a learned skill first) or it wasn't (in which case just revert). The base Hermes pack is the authoritative version.
