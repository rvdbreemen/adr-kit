# Installing ADR Kit

Coding agent? Use the shorter, client-neutral
[INSTALL-AGENT.md](INSTALL-AGENT.md) runbook first. This document is the
long-form reference for manual client commands, portability notes, updates,
and removal.

ADR Kit has separate native distributions for Claude Code, OpenAI Codex, and
the standalone GitHub Copilot CLI. They share deterministic Python engines,
but they do not share manifests, cache paths, or client-specific instructions.

## Requirements

- Python 3.10 or newer.
- Invoke the automatic installer with the intended interpreter (`python`,
  `python3`, `py -3`, or an absolute executable). It validates a child process
  and embeds the resolved absolute path in prepared Codex and Copilot MCP
  manifests.
- At least one supported CLI on `PATH`: `claude`, `codex`, or standalone
  `copilot`.
- A cloned ADR Kit checkout when using the automatic installer.

No API key is required for installation or the default deterministic tools.

## Select the ADR format

New records default to MADR. Set a project default in
`docs/adr/.adr-kit.json`:

```json
{
  "template": {
    "profile": "madr"
  }
}
```

Supported values are `madr`, `nygard`, and `canonical`. Create a record with
`python bin/adr new "Title" --adr-dir docs/adr`, or override one record with
`--profile`. Existing canonical ADRs remain valid. Preview an optional
conversion with `python bin/adr-migrate --dry-run --to-profile madr docs/adr`.
Choose MADR for explicit agent guidance, Nygard for concise human scanning,
or canonical for maximum compatibility with pre-v0.34 adr-kit repositories.

Before accepting a format choice from a user, query the installed pre-made
catalog:

```bash
python bin/adr profiles --format json
```

Only returned profile ids are selectable. Each entry reports the exact shipped
template and whether it is available. If a template is missing, repair the
installation; do not invent a profile or synthesize a substitute template.

Every profile keeps the same lifecycle metadata and Enforcement contract.
MADR is the default because its explicit problem, drivers, options, outcome,
trade-offs, and confirmation fields minimize agent inference. This is an
agent-reliability choice, not a claim that MADR is globally the most used
format: no authoritative census exists. See the
[format evaluation](docs/research/adr-format-evaluation.md) and
[ADR-005](docs/adr/ADR-005-selectable-agent-friendly-adr-formats.md) for the
scoring, adoption signals, and compatibility rationale.

## Automatic detected-client install

From the ADR Kit checkout:

```bash
python scripts/install-agent-envs.py --detect-only
python scripts/install-agent-envs.py --project-root "/path/to/project"
```

Detection requires both a real executable and the expected version signature:

| Client | Executable | Required signature |
| --- | --- | --- |
| Claude Code | `claude` | `Claude Code` |
| OpenAI Codex | `codex` | `codex-cli` |
| GitHub Copilot CLI | `copilot` | `GitHub Copilot CLI` |

The default `auto` mode installs every detected client. It does not treat
`gh copilot`, a VS Code extension, or a directory under a home folder as proof
that a CLI is installed. A timeout, launch error, or invalid version signature
for one client is isolated and does not hide or block other detected clients.

Useful options:

```bash
# Preview native commands without changing client state
python scripts/install-agent-envs.py --dry-run --project-root "/path/to/project"

# Require and install an explicit subset
python scripts/install-agent-envs.py --clients codex,copilot

# Require all three CLIs
python scripts/install-agent-envs.py --clients all

# Install from another checkout or marketplace root
python scripts/install-agent-envs.py --source "/path/with spaces/adr-kit"

# Override the interpreter or prepared-marketplace data location
python scripts/install-agent-envs.py --python /opt/python/bin/python3
python scripts/install-agent-envs.py --install-root "/persistent/user/data/adr-kit"
```

The installer validates every required manifest before a client mutation. It
then creates a versioned prepared marketplace in the platform's per-user data
directory:

- Windows: `%LOCALAPPDATA%\adr-kit\marketplaces`
- macOS: `~/Library/Application Support/adr-kit/marketplaces`
- Linux: `${XDG_DATA_HOME:-~/.local/share}/adr-kit/marketplaces`

This copy contains the resolved Python executable in both native MCP manifests
and executable Unix entry-point modes. The first run may re-register an older
checkout/Git marketplace against this prepared source; later runs recognize
the same source and use update/no-op paths.

Re-running the installer is idempotent. Post-install validation checks native
registration and MCP listing, while prepared-source validation starts
`adr-mcp` and completes MCP initialize plus tools/list before any client is
changed. Failure of one selected client is reported after the installer
continues with the others. Client-native marketplace operations are not
transactional, so a failed client may need its normal plugin install command
re-run; successful clients remain installed. `--skip-validation` is intended
only for offline packaging tests. After validation, the installer runs
`adr-migrate --plan` against `<project-root>/docs/adr`. The scan is read-only
and fail-open: it prints deterministic preview commands or guided migration
notices but never changes ADR files or invalidates an otherwise successful
client install. See [format migration](docs/format-migration.md).

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

Registration visibility is only the first check. In each installed client,
invoke `adr_context` against a scratch project or run the context skill once to
prove that the configured Python command and packaged engine can actually
start.

After project initialization, run `python bin/adr-index docs/adr` in the
project. This generates the compact `ADR-INDEX.md`, the versioned
`ADR-INDEX.json` metadata and relationship graph, and the README index from the
same ADR sources. Agents may explore the JSON graph to shortlist decisions, but
must open the linked Markdown ADR before enforcing or citing it. Verify all
three generated views with `python bin/adr-index --check docs/adr`.

### Known portability limitations

- Generated payload drift checks normalize CRLF and LF before comparison, so
  the same generated content is stable across Windows and Unix checkouts.
- The automatic installer restores Unix executable modes and embeds the exact
  Python runtime. Manual Git marketplace installation still depends on the
  archive's executable modes and static `python` command.
- If the embedded Python executable is moved or removed, rerun the automatic
  installer with the replacement interpreter.
- Native marketplace mutations are isolated per client but are not one atomic
  transaction across Claude, Codex, and Copilot.

See the [2026-07-18 source audit](docs/reviews/2026-07-18-source-audit/FINDINGS.md)
for evidence and remediation recommendations.

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
`bin/` together because several engines import `adr_schema.py`,
`adr_format.py`, or call sibling
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
