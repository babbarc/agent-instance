# Patch Hunk Classification Protocol

## When to use this

An existing patch fails dry-run after an upstream Hermes update, and you need to decide which hunks to keep, regenerate, or drop. Or you inherit a patch with undocumented changes and need to evaluate what it does.

## Step 1 — Trace provenance

Find when the patch was first introduced and whether a commit message explains why:

```bash
cd /opt/data/home && git log --all --oneline -- .hermes/patches/<file>
cd /opt/data/home && git show <first-commit> --stat -- .hermes/patches/
```

Look at the original commit message and any follow-up commits. If the patch was part of an "initial" snapshot commit, there's no documented reasoning — you'll need to infer intent from the diff itself.

## Step 2 — List every hunk

```bash
grep '^@@' ~/.hermes/patches/<file>.patch
```

Each `@@` line is one atomic change. Number them and read each in context.

## Step 3 — Classify each hunk

| Category | Signal | Action |
|----------|--------|--------|
| **Custom addition** | Content that exists ONLY in the patch, not in upstream at all (new regex patterns, new functions, new guard clauses). These are deliberate user-specific customisations. | **Keep** — the point of the patch |
| **Upstream feature removed** | The upstream `.original` has a feature that the patch deletes (e.g. a function, a context var, a security pattern). The patch deliberately removes something upstream ships. | **Question** — was this removal intentional? Could be stale (patch predates the feature) or deliberate (security/privacy choice) |
| **Old version of upstream code** | The patch has an older implementation of something upstream now does differently (e.g. inline code when upstream moved to a shared library, older function signature). | **Stale** — regenerate from current upstream, re-apply only custom additions |
| **Whitespace / escape drift** | The hunk changes only whitespace, escape sequences, or comment formatting without semantic change. | **Drop** — no-op diff, likely from patch generation against a slightly different upstream snapshot |

## Step 4 — Decide for each upstream-feature-removed hunk

For hunks that remove features upstream ships, ask:

1. **Can I find a session or commit message that explains why?** — Search session history for keywords related to the removed feature.
2. **Does the removed feature conflict with a custom addition?** — If yes, they may be coupled and both intentional.
3. **Is the removed feature relevant to how this agent operates?** — E.g. removing tool-correlation tracking means approval prompts lose context. That's a deliberate choice.
4. **Would removing this weaken security?** — E.g. removing `_HERMES_CONFIG_PATH` patterns means `sed -i` on config.yaml bypasses approval. Flag this to the user.

Present your findings to the user as a table:

| Hunk | What it does | Type | Keep? |
|------|-------------|------|-------|
| 1-3 | Remove observability context vars | Upstream feature removed | ? |
| 4-6 | Remove config-path security patterns | Upstream feature removed | ? |
| 7 | Add email/WhatsApp approval gates | Custom addition | Yes |
| 8-9 | Remove execute_code session approval | Upstream feature removed | ? |

Let the user decide. Then regenerate the patch with only the hunks they want to keep.

## Step 5 — Regenerate

1. Save the current upstream: `cp /opt/hermes/<relative-path>/<file> /tmp/<file>.new`
2. Copy to a working copy: `cp /tmp/<file>.new /tmp/<file>.patched`
3. Apply only the keep-hunks to `/tmp/<file>.patched`
4. Generate patch: `diff -u /tmp/<file>.new /tmp/<file>.patched > ~/.hermes/patches/<file>.patch`
5. Fix headers for `patch -p0 -d /opt/hermes`:
   ```bash
   sed -i "1s|/tmp/<file>.new|<relative-path>/<file>|" ~/.hermes/patches/<file>.patch
   sed -i "2s|/tmp/<file>.patched|<relative-path>/<file>|" ~/.hermes/patches/<file>.patch
   ```
6. Verify: `patch --dry-run -p0 -d /opt/hermes < ~/.hermes/patches/<file>.patch`
7. Verify Python syntax: `python3 -c "import ast; ast.parse(open('/opt/hermes/<relative-path>/<file>').read()); print('OK')"`
8. Verify only intended diffs: `diff -u <(patch --dry-run -p0 -d /opt/hermes < ~/.hermes/patches/<file>.patch -o /dev/null 2>/dev/null; cat /opt/hermes/<relative-path>/<file>) ~/.hermes/patches/<file>.patch | head`

## References

- `hermes-infrastructure` — mechanism for 99-hermes-patches.sh and the boot-time patch application loop
- `hermes-development/references/brain-architecture-audit.md` — Dimension 6 covers patch state auditing
