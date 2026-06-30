## Pitfalls

### Misreading patch state

When investigating a suspected issue in patched Hermes source code, the installed file may already have patches applied. The `.original` backup shows upstream state.

| Mistake | Correction |
|---------|------------|
| "The tool description still has X — this needs fixing." | "The patch removed X from the file on disk but the running process loaded pre-patch. It just needs a restart." |

A patch applied to disk but not yet picked up (Python module caching) can make the live system appear different from the file on disk — verify both before making claims.
