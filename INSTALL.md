# Installing ADR Kit

ADR Kit has separate native distributions for Claude Code, OpenAI Codex, and
the standalone GitHub Copilot CLI. They share deterministic Python engines,
but they do not share manifests, cache paths, or client-specific instructions.

## Requirements

- Python 3.9 or newer.
- At least one supported CLI on `PATH`: `claude`, `codex`, or standalone
  `copilot`.
- A cloned ADR Kit checkout when using the automatic installer.

No API key is required for installation or the default deterministic tools.

## Automatic detected-client install

From the ADR Kit checkout:

```bash
python scripts/install-agent-envs.py --detect-only
python scripts/install-agent-envs.py
```

Detection requires both a real executable and the expected version signature:

| Client | Executable | Required signature |
| --- | --- | --- |
| Claude Code | `claude` | `Claude Code` |
| OpenAI Codex | `codex` | `codex-cli` |
| GitHub Copilot CLI | `copilot` | `GitHub Copilot CLI` |

The default `auto` mode installs every detected client. It does not treat
`gh copilot`, a VS Code extension, or a directory under a home folder as proof
that a CLI is installed.

Useful options:

```bash
# Preview native commands without changing client state
python scripts/install-agent-envs.py --dry-run

# Require and install an explicit subset
python scripts/install-agent-envs.py --clients codex,copilot

# Require all three CLIs
python scripts/install-agent-envs.py --clients all

# Install from another checkout or marketplace root
python scripts/install-agent-envs.py --source "/path/with spaces/adr-kit"
```

Re-running the installer is safe. Claude and Copilot use their update paths.
Codex is refreshed only when the installed plugin version differs. Post-install
validation is on by default; `--skip-validation` is intended only for offline
packaging tests.

## Claude Code

Manual install:

```text
/plugin marketplace add rvdbreemen/adr-kit
/plugin install adr-kit@rvdbreemen-adr-kit
/reload-plugins
/adr-kit:init
```

Claude Code continues to use:

- `.claude-plugin/plugin.json`
- repository-root `skills/`
- repository-root `agents/`
- the existing SessionStart, PreToolUse, and PostToolUse hooks

The Codex and Copilot distributions do not change this contract.

Validate from a terminal:

```bash
claude plugin validate .
claude plugin details adr-kit@rvdbreemen-adr-kit
```

Expected: 14 skills, one `adr-generator` agent, and three hooks.

## OpenAI Codex

Manual install:

```bash
codex plugin marketplace add rvdbreemen/adr-kit
codex plugin add adr-kit@rvdbreemen-adr-kit-codex
codex plugin list --json
codex mcp list
```

Codex loads the separate `codex/` distribution through
`.agents/plugins/marketplace.json`. It contains:

- `.codex-plugin/plugin.json`
- 14 Codex-native skills under `codex/skills/`
- `.mcp.json` with the `adr-kit` server
- a self-contained, generated copy of the deterministic engines

Claude slash commands are not Codex commands. In Codex, open `/skills` and
invoke the namespaced skills, for example:

```text
$adr-kit:context
$adr-kit:judge
$adr-kit:lint
$adr-kit:adr
```

The MCP tools are `adr_context`, `adr_judge`, `adr_status`, and `adr_quality`.
Each accepts an optional absolute `project_root`; the Codex skills always pass
the active workspace so the server never mistakes its plugin cache for the
project.

## Standalone GitHub Copilot CLI

This integration targets the `@github/copilot` CLI invoked as `copilot`.

Manual install:

```bash
copilot plugin marketplace add rvdbreemen/adr-kit
copilot plugin install adr-kit@rvdbreemen-adr-kit-copilot
copilot plugin list
copilot mcp list
copilot skill list
```

Copilot loads `.github/plugin/marketplace.json`, which points only to the
separate `copilot/` distribution. That distribution has a root `plugin.json`,
14 Copilot-compatible skills, and `.mcp.json`. It does not load the Claude
manifest or Codex manifest.

On Windows, a sandboxed caller may have read-only access to the user's normal
`~/.copilot` directory. For CI or isolated smoke tests, set `COPILOT_HOME` to a
writable temporary directory. A normal user terminal should use the default
home.

## Portable fallback

Cursor, Claude Cowork, and agents without plugin support can still vendor the
portable source files:

- `skills/adr/SKILL.md`
- `agents/adr-generator.md`
- `instructions/adr.coding.md`
- `instructions/adr.review.md`
- `bin/adr-mcp`

Use the client's documented project skill and instruction directories. Keep
`bin/` together because several engines import `adr_schema.py` or call sibling
scripts.

## Validation

Run the repository checks:

```bash
python scripts/sync-agent-plugins.py --check
python -m pytest tests/test_agent_installer.py tests/test_adr_mcp.py
```

Then validate the installed client:

```bash
claude plugin details adr-kit@rvdbreemen-adr-kit
codex mcp list
copilot plugin list
copilot mcp list
copilot skill list
```

## Updating

Pull the new tag and re-run:

```bash
python scripts/install-agent-envs.py
```

Project ADRs under `docs/adr/` are never part of the plugin update.

## Uninstall

```bash
claude plugin uninstall adr-kit@rvdbreemen-adr-kit
codex plugin remove adr-kit@rvdbreemen-adr-kit-codex
copilot plugin uninstall adr-kit
```

Remove the corresponding marketplace only when no other plugin uses it.
Uninstalling ADR Kit preserves the project's `docs/adr/` directory.
