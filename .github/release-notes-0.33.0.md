# ADR Kit v0.33.0: Native Codex and multi-CLI installation

ADR Kit now ships first-class, separate plugins for OpenAI Codex and the
standalone GitHub Copilot CLI while preserving the existing Claude Code plugin.

## Highlights

- Codex gets a validated `.codex-plugin` distribution with 14 namespaced
  skills and the four-tool, key-free ADR MCP server.
- The standalone Copilot CLI gets its own marketplace and self-contained
  plugin with 14 skills and the same MCP server.
- `scripts/install-agent-envs.py` detects real `claude`, `codex`, and `copilot`
  executables from version output, installs every detected client through its
  native plugin API, and validates the result.
- MCP tools now accept `project_root` and `adr_dir`, so a server launched from
  a plugin cache always operates on the active workspace.
- Project pre-commit hooks resolve the newest engine across Claude Code,
  Codex, and Copilot CLI plugin caches.
- Generated Codex and Copilot payloads are checked byte-for-byte against the
  canonical engines, schemas, templates, and instructions.

## Install

From a cloned checkout:

```bash
python scripts/install-agent-envs.py --detect-only
python scripts/install-agent-envs.py
```

Manual client commands are documented in `README.md` and `INSTALL.md`.

## Compatibility

- Claude Code keeps its existing `.claude-plugin` manifest, 14 skills,
  `adr-generator` agent, and SessionStart, PreToolUse, and PostToolUse hooks.
- Codex uses the separate `codex/` distribution and namespaced skills such as
  `$adr-kit:context`.
- Copilot support targets the standalone `@github/copilot` CLI, not
  `gh copilot` or VS Code agent mode.

## Validation

- Official Codex plugin validator: PASS.
- Claude Code plugin validation and component inventory: PASS.
- Clean-home installer smoke tests for Claude Code, Codex, and Copilot CLI:
  PASS.
- Codex and Copilot MCP/skill discovery: PASS.
- Full automated suite: 524 passed, 3 skipped.
- Strict ADR lint, generated index, and ADR doctor: PASS with 0 findings.
- Markdown lint, JSON syntax, payload drift, and release-version checks: PASS.
