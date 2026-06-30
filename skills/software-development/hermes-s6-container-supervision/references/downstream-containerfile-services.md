# Adding s6 Services via Downstream Containerfile

The `hermes-s6-container-supervision` skill documents adding services to the
**upstream** Hermes Dockerfile (via `docker/s6-rc.d/`). This reference covers
the **downstream** pattern — injecting an s6 service from a user's custom
Containerfile that derives from the upstream image.

## When to Use This

You're extending a `Containerfile` that starts from `FROM nousresearch/hermes-agent:latest`
and you want an additional supervised process (cupsd, avahi, sidecar watcher, etc.)
to start at boot alongside the existing services.

## The Pattern

Instead of modifying the upstream `docker/s6-rc.d/` (which would require forking
the upstream repo), create the service directory and register it in the user
bundle via `RUN` commands:

```dockerfile
# 1. Create the s6-rc service directory
COPY my-service-run.sh /etc/s6-overlay/s6-rc.d/my-service/run
RUN chmod +x /etc/s6-overlay/s6-rc.d/my-service/run && \
    echo "longrun" > /etc/s6-overlay/s6-rc.d/my-service/type && \
    mkdir -p /etc/s6-overlay/s6-rc.d/my-service/dependencies.d

# 2. Register in the user bundle so it auto-starts
RUN touch /etc/s6-overlay/s6-rc.d/user/contents.d/my-service
```

The `run` script must use `#!/command/with-contenv sh` shebang and follow the
same conventions as upstream services (drop privileges via `s6-setuidgid`,
use foreground mode for s6 supervision).

## Architecture

```
/etc/s6-overlay/s6-rc.d/
├── my-service/          ← created by COPY + RUN in Containerfile
│   ├── run              ← executable script, #!/command/with-contenv sh
│   ├── type             ← contains "longrun"
│   └── dependencies.d/  ← empty directory (or with symlinks)
└── user/
    ├── type             ← "bundle" (inherited from upstream)
    └── contents.d/
        ├── dashboard    ← inherited from upstream
        ├── main-hermes  ← inherited from upstream
        └── my-service   ← added by `touch` in Containerfile
```

## Key Differences from Upstream Pattern

| Aspect | Upstream (docker/s6-rc.d/) | Downstream (Containerfile) |
|--------|---------------------------|---------------------------|
| Location | `docker/s6-rc.d/<name>/` in repo | `/etc/s6-overlay/s6-rc.d/<name>/` in image |
| Bundling | `COPY docker/s6-rc.d/` in Dockerfile picks up all files | Manual `COPY` + `RUN` for each service |
| Registration | Create `docker/s6-rc.d/user/contents.d/<name>` (empty file) | `RUN touch /etc/s6-overlay/s6-rc.d/user/contents.d/<name>` |
| Dependencies | Create `dependencies.d/base` for base bundle wait | Create empty `dependencies.d/` (no base needed unless explicit) |

## Example: CUPS Print Spooler

The network-printer plugin's CUPS service uses this pattern:

```dockerfile
COPY cupsd-run.sh /etc/s6-overlay/s6-rc.d/cupsd/run
RUN chmod +x /etc/s6-overlay/s6-rc.d/cupsd/run && \
    echo "longrun" > /etc/s6-overlay/s6-rc.d/cupsd/type && \
    mkdir -p /etc/s6-overlay/s6-rc.d/cupsd/dependencies.d
RUN touch /etc/s6-overlay/s6-rc.d/user/contents.d/cupsd
```

The run script starts cupsd in foreground for s6 supervision and runs
first-boot printer queue setup as a background process before foregrounding.

## Pitfall: Multiple RUN Layers vs COPY

Creating service files via `RUN` (echo/cat) adds image layers. For complex
`run` scripts, prefer `COPY` — cleaner and avoids escaping issues with
embedded shell scripts.

## Pitfall: Service Dependencies

If your service needs network or another service, add dependency symlinks in
`dependencies.d/`. For most services that just need filesystem + basic users,
an empty `dependencies.d/` works — cont-init.d completes before s6-rc starts.
