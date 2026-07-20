# Claude Code CLI support

ADR Kit supports Claude Code CLI as a native plugin. The certified Windows
package keeps only `plugin.json` under `.claude-plugin/`; skills, agents,
`hooks/hooks.json`, `.mcp.json`, and executables live at plugin root.

## Setup and workflows

Run `python scripts/install-agent-envs.py --clients claude`. The installer
detects Claude, prepares an immutable payload with an absolute Python runtime,
registers the local marketplace, and installs `adr-kit@rvdbreemen-adr-kit`.
Project setup preserves bytes outside its managed `CLAUDE.md` markers and
writes the generated guide under `.adr-kit/`.

Claude discovers 14 namespaced skills such as `/adr-kit:context`,
`/adr-kit:judge`, and `/adr-kit:setup`. Skill descriptions carry the trigger
catalog; `$ARGUMENTS` carries explicit slash-command input. Side-effecting or
deliberately timed workflows use `disable-model-invocation: true`.

## Hooks and MCP

The plugin registers SessionStart, UserPromptSubmit, PreToolUse, PostToolUse,
SubagentStart, and PreCompact. All are bounded, deterministic, read-only, and
fail open. On Windows the dispatcher prefers the bundled native host; macOS and
Linux use a native host when shipped and otherwise fall back to the prepared
Python runtime. Stop-like and unsupported events are successful no-ops.

The root `.mcp.json` exposes `adr_context`, `adr_judge`, `adr_quality`, and
`adr_status`. Model-visible hook context is advisory; the git pre-commit gate
remains the deterministic enforcement floor.

## Doctor, updates, and removal

`adr-doctor` is fast and local. `adr-doctor --deep` adds native registration,
live MCP, model identity, hook, and latency probes. `--fix` permits backups,
config rewrites, and re-registration; safe owned repairs remain automatic.

Stable updates use Claude's native update flow after source verification.
Failed activation restores the previous healthy payload. Breaking migrations
pause for confirmation. Use Claude's disable command for a reversible pause,
or `python scripts/install-agent-envs.py --clients claude --remove` to remove
only ADR Kit-owned registration and payloads. Reinstall is idempotent.

Windows native certification uses Claude Code 2.1.215. macOS and Linux are
best-effort and were not run in this Windows certification pass.
