# Codex CLI support

ADR Kit supports Codex CLI through `codex/.codex-plugin/plugin.json`, root
`skills/`, `hooks/hooks.json`, `.mcp.json`, and bundled local executables.

Install with `python scripts/install-agent-envs.py --clients codex`. Workflows
are discoverable skills; invoke them explicitly with names such as
`$adr-kit:context` and `$adr-kit:grill ADR-NNN`. Deprecated local custom prompts
are not advertised as a plugin command surface. Project setup adds a concise
managed `AGENTS.md` block and keeps the detailed guide separate.

The package exposes the five key-free MCP tools `adr_context`, `adr_judge`,
`adr_status`, `adr_quality`, and read-only `adr_readiness`. The
[ADR Grilling user guide](../adr-grilling.md) documents the complete
Proposed-to-Accepted flow.

Codex receives SessionStart, UserPromptSubmit, PreToolUse, PostToolUse,
SubagentStart, and PreCompact through its native hook file. Changed command
hooks remain subject to Codex trust review. ADR Kit never bypasses that review.
All hook errors fail open; pre-commit is the enforcement floor.

`adr-doctor --deep` resolves the installed manifest, actual interpreter and MCP
target, plugin registration, trust/review state, hook package, and latency. It
also detects the regression class where a current manifest points at a removed
older cache. `--fix` can back up and re-register owned state.

The current Codex plugin manager uses remove/add for a verified update and for
disable/re-enable when no native toggle is available. Rollback restores the
previous healthy cache. Removal never edits unrelated Codex config. Windows
native certification uses Codex CLI 0.144.6; macOS/Linux are best-effort and
were not run in this Windows pass.
