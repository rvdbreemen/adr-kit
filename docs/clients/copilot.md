# GitHub Copilot CLI support

ADR Kit supports GitHub Copilot CLI with root `plugin.json`, `skills/`,
`hooks.json`, `.mcp.json`, and local executables. Install with
`python scripts/install-agent-envs.py --clients copilot`.

Copilot discovers the 14 ADR Kit skills through `/skills`. The package does not
claim Claude namespaced commands, Codex `$skill` syntax, or a separate prompt
surface. Managed `.github/copilot-instructions.md` content remains inside
replaceable ADR Kit markers; user content stays byte-identical outside them.

Copilot hooks use lower-camel event names and declare both `bash` and
`powershell` commands. Session start and prompt submission provide proactive
context. Copilot PreToolUse cannot inject arbitrary model context, so ADR Kit
does not fake deny/retry behavior: PostToolUse and the deterministic pre-commit
gate are the edit backstops.

`adr-doctor --deep` checks native registration, lower-camel hook shape, both
platform commands, MCP initialize/list/call, version state, and latency.
Verified update and rollback preserve the previous payload and unrelated
configuration. On Copilot CLI versions without a working native enable/disable
subcommand, ADR Kit uses uninstall/reinstall plus the project/global settings
opt-out. Windows native certification uses Copilot CLI 1.0.71; macOS/Linux are
best-effort and were not run in this Windows pass.
