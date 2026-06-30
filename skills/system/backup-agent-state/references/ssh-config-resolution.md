# SSH Config Resolution

When the system HOME (from `/etc/passwd`) differs from the shell's `~`,
SSH reads config from the **system** HOME, not the shell one.

## Detection

Run `ssh -v -p <port> git@<host>` and check which `IdentityFile` paths SSH
attempts. If it tries `/system/home/.ssh/id_X` but your key is at
`/shell/home/.ssh/id_X`, the resolution is wrong.

## Fix

1. Use **absolute paths** in `~/.ssh/config`:
   ```
   IdentityFile /shell/home/.ssh/id_ed25519_alps  # NOT ~/.ssh/...
   ```
2. Also copy/symlink assets to the system HOME so SSH finds them:
   ```bash
   cp ~/.ssh/config /system/home/.ssh/config
   cp ~/.ssh/known_hosts /system/home/.ssh/known_hosts
   ln -s ~/.ssh/id_ed25519_alps /system/home/.ssh/id_ed25519_alps
   ```

## Self-hosted Gitea/GitLab SSH pattern

```
Host alps
    HostName alps
    Port 2222
    User git
    IdentityFile /shell/home/.ssh/id_ed25519_alps
    IdentitiesOnly yes
```

Remote URL: `alps:namespace/repo.git` (SCP-style, uses SSH Host block)

Test with: `git ls-remote alps:namespace/repo.git`
