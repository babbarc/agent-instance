# Tool Debugging — Trace Plugin Source Before Speculating

When a Hermes native tool errors unexpectedly, the fastest path to a root cause is reading the plugin's handler code — not speculating about API keys, external auth, or environment issues.

## Procedure

1. **Find the plugin directory** — `ls /opt/data/plugins/<plugin-name>/`. The plugin name matches the entry in `config.yaml` `plugins.enabled`.
2. **Read the handler** — `read_file /opt/data/plugins/<plugin-name>/tools.py`. If no `tools.py`, read `__init__.py`. The handler function receives a dict of tool args and returns a string.
3. **Trace what the tool actually does.** Does it:
   - Call an external API with a registered Hermes credential? → Check `hermes auth list`.
   - Run a CLI binary via subprocess? → Check PATH and the binary's own auth state. If the binary works in a terminal but fails from the plugin, compare `HOME` between the gateway process (`cat /proc/<pid>/environ | tr '\0' '\n' | grep '^HOME='`) and the terminal — many CLIs read config/credentials from `$HOME`.
   - Connect via MCP? → Check `mcp_servers` in config.yaml.
   - Call a Hermes internal API? → Check patches at `~/.hermes/patches/`.
4. **Report the architecture, don't speculate.** If unsure after reading the handler, report exactly what you found (binary path, API call, subprocess invocation) and ask.
