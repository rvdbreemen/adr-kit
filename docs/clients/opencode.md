# OpenCode Support

ADR Kit ships a native OpenCode plugin backed by the same deterministic Python
engines used by the other clients. The OpenCode package is intentionally
separate from the certified Claude Code, Codex, and Copilot CLI registry. It is
tested as its own native surface and does not change the three-client release
gate.

## Install

The checkout is already configured for OpenCode. Start OpenCode from this
repository and its root `opencode.json` loads the local package:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["./"]
}
```

For another project, use the public npm package:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["@rvdbreemen/adr-kit-opencode@0.52.2"]
}
```

Version `0.52.2` is published. Future versions are staged automatically by
`.github/workflows/release-publish.yml`, which calls the reusable
`.github/workflows/publish-opencode-npm.yml` workflow. They become available
after a maintainer approves the staged package with npm 2FA. If a future version
has not yet been approved, point OpenCode at a reviewed checkout:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": [
    ["/absolute/path/to/adr-kit", {"python": "/absolute/path/to/python"}]
  ]
}
```

The plugin finds the package runtime automatically. Set `ADR_KIT_ROOT` when a
copied local plugin needs to use a separate checkout. Set `ADR_KIT_PYTHON` or
the `python` option when `python` is not the correct executable.

Restart OpenCode after changing plugin or config files. Configuration is loaded
at startup, not hot-reloaded.

## Native Surface

At config time the plugin adds only missing entries:

- canonical ADR Kit skills through `skills.paths`;
- ADR Kit instructions and the project `.adr-kit/ADR-guide.md` when present;
- an `adr-decisions` reference for `docs/adr` when present;
- `/adr-kit-<workflow>` commands for the canonical workflow registry; and
- the local `adr-kit` stdio MCP server.

Existing user entries are preserved. Disable individual registration paths with
plugin options such as `{"mcp": false, "commands": false}`. Set
`ADR_KIT_OPENCODE_MCP=0` to disable only automatic MCP registration. Manual MCP
registration follows the OpenCode schema:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "adr-kit": {
      "type": "local",
      "command": [
        "python",
        "/absolute/path/to/adr-kit/bin/adr-mcp",
        "--root",
        "/absolute/path/to/project"
      ],
      "cwd": "/absolute/path/to/project",
      "enabled": true,
      "environment": {
        "PROJECT_ROOT": "/absolute/path/to/project"
      }
    }
  }
}
```

The server exposes `adr_context`, `adr_judge`, `adr_status`, `adr_quality`,
and read-only `adr_readiness`. It supports the MCP handshake revisions already
implemented by ADR Kit and the stateless MCP 2026-07-28 discovery envelope.

## Hooks

The native plugin uses OpenCode's documented hooks:

- `chat.message` runs task retrieval for the incoming prompt;
- `experimental.chat.system.transform` injects bounded advisory context;
- `tool.execute.before` checks edit paths and the pull-request shell moment;
- `tool.execute.after` provides the post-edit backstop;
- `experimental.session.compacting` carries ADR context forward;
- `tool.definition` reminds edit tools to query ADR Kit;
- `shell.env` exposes `ADR_KIT_ROOT`; and
- `event` cleans session-local state.

The hooks call `hooks/adr-hook.py`, not a TypeScript reimplementation. Advisory
failures time out and fail open. The existing shared pull-request guard may deny
an OpenCode shell call when it returns an explicit deny decision. Normal edit
context never blocks an edit. When an interactive prompt receives an
`AUTO_GRILL_PENDING` handoff, the plugin translates the shared client-neutral
grill command to OpenCode's native `/adr-kit-grill` command before injecting it.

The deterministic enforcement floor remains outside OpenCode:

```bash
python /absolute/path/to/adr-kit/scripts/setup-project.py \
  --project-root /absolute/path/to/project
```

This installs the ADR Kit-owned pre-commit gate without replacing user-owned
guidance or unrelated hooks. Do not use a plugin hook as a substitute for the
commit floor.

## CI

CI is client-independent. Copy the workflows appropriate for the project from
`templates/github-workflows/`:

- `adr-judge.yml` for declarative pull-request enforcement;
- `adr-index-check.yml` for generated-index freshness;
- `adr-readiness.yml` for Proposed ADR readiness; and
- `adr-audit.yml` or `adr-guardian-audit.yml` for report-only health sweeps.

These workflows work whether changes come from OpenCode, Claude Code, Codex,
Copilot, an editor, or a human. The OpenCode plugin does not add a second CI
implementation.

## Support Boundary

OpenCode has native plugin support for this package, but it is not included in
`clients/capabilities.json` or the generated three-client support matrix. The
three-client installer, native doctor, Windows evidence bundle, and release
certification gate remain unchanged. OpenCode does not claim those clients'
native update, rollback, doctor, or certification guarantees.

Report OpenCode API or runtime compatibility issues with the OpenCode version,
platform, package version, and the result of the focused OpenCode smoke tests.
