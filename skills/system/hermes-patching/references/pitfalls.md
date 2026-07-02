## Pitfalls

### Misreading patch state

When investigating a suspected issue in patched Hermes source code, the installed file may already have patches applied. The `.original` backup shows upstream state.

| Mistake | Correction |
|---------|------------|
| "The tool description still has X — this needs fixing." | "The patch removed X from the file on disk but the running process loaded pre-patch. It just needs a restart." |

### Post-update file migration

After an upgrade, Hermes source files may move between directories (e.g. `agent/` → `tools/`). If the patch headers still reference the old path, `patch -p0` will fail to find the target file. The same applies to the `cp` lines in the init script.

| Check | Why |
|-------|-----|
| `head -3 ~/.hermes/patches/*.patch` | If the `---` path points to a directory that no longer exists under `/opt/hermes/`, the patch won't apply on next boot. |
| The `cp` lines in `/etc/cont-init.d/99-hermes-patches` | Must reference the current file location, not the pre-upgrade one. |

### Removing patches from root-owned files (container trap)

The one-liner ``cp .original /opt/hermes/...`` only works when the hermes user owns the target file. In a container deployment (or when ``ls -la`` shows ``root root``), ``/opt/hermes/`` files are root-owned and the ``hermes`` user cannot write to them — every ``cp``, ``patch -R``, or ``write_file`` attempt fails with ``Permission denied`` or ``Write denied``.

| Mistake | Correction |
|---------|------------|
| Try ``cp .original /opt/hermes/...`` on a root-owned file, then hit permission errors, then escalate to ``sudo``/``doas``/``pkexec`` (none exist in the container). | Read the init script at ``/etc/cont-init.d/99-hermes-patches``. The loop's ``[ -f \"$patch_file\" ] \|\| continue`` guard means **removing the ``.patch`` file is sufficient** — the init script skips it on next boot and the clean upstream file from the image stays. Don't touch the installed file. |
| Keep trying to revert the live file because the user said to remove the patch. | Distinguish: "remove from mechanism" (delete ``.patch`` — takes effect on restart) vs "revert live file" (restore ``.original`` — takes effect immediately). If the file is root-owned, only option A is available without restarting the container first. |

A patch applied to disk but not yet picked up (Python module caching) can make the live system appear different from the file on disk — verify both before making claims.
