# Installing ADR Kit

Coding agent? Use the shorter, client-neutral
[INSTALL-AGENT.md](INSTALL-AGENT.md) runbook first. This document is the
long-form reference for manual client commands, portability notes, updates,
and removal.

ADR Kit has separate native distributions for Claude Code, OpenAI Codex, and
the standalone GitHub Copilot CLI, plus a native OpenCode plugin package. They
share deterministic Python engines, but they do not share manifests, cache
paths, or client-specific instructions. OpenCode is tested separately and does
not expand the three-client certification gate.
After installation, follow the
[ADR Grilling user guide](docs/adr-grilling.md) to create, reconstruct, resume,
and explicitly finish a decision.

## Requirements

- Python 3.10 or newer.
- Invoke the automatic installer with the intended interpreter (`python`,
  `python3`, `py -3`, or an absolute executable). It validates a child process
  and embeds the resolved absolute path in prepared Codex and Copilot MCP
  manifests.
- At least one supported CLI on `PATH`: `claude`, `codex`, or standalone
  `copilot`.
- A cloned ADR Kit checkout when using the automatic installer.
- OpenCode 1.18 or newer when using the native OpenCode plugin. OpenCode loads
  the plugin with Bun; no Node or npm dependency is required at runtime by the
  plugin itself.

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
# Read the complete plan without writing
python scripts/install-agent-envs.py --plan
python scripts/install-agent-envs.py --plan --format json

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

# Remove ADR Kit-owned registrations and prepared payloads
python scripts/install-agent-envs.py --uninstall --clients codex
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

Re-running the installer is idempotent. The desired-state plan includes
effective opt-outs, migrations, backups, activation, validation, rollback, and
removals before mutation. A major-version migration pauses until the reviewed
command is repeated with `--yes`. Post-install validation checks native
registration and MCP listing, while prepared-source validation starts
`adr-mcp`, completes MCP initialize plus tools/list, and executes the packaged
Claude SessionStart wrapper through the platform shell before any client is
changed. Failure of one selected client is reported after the installer
continues with the others. Each client has an independent lock and transaction
evidence file. Activation failure re-registers the retained previous healthy
payload when available; successful clients remain installed.
`--skip-validation` is intended
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
- plugin-root `hooks/hooks.json` with six bounded lifecycle outcomes
- plugin-root `.mcp.json`

The Codex and Copilot distributions do not change this contract.

## Project guidance and settings

Native plugin installation and project registration are separate, inspectable
steps. Preview project changes first:

```bash
python scripts/setup-project.py --project-root "/path/to/project" --dry-run
python scripts/setup-project.py --project-root "/path/to/project"
```

Project setup owns only:

- generated `.adr-kit/ADR-guide.md`;
- the ADR Kit marker block in `AGENTS.md`;
- the ADR Kit marker block in `CLAUDE.md`;
- the ADR Kit marker block in `.github/copilot-instructions.md`; and
- an ADR Kit-owned `.githooks/pre-commit`.

An old generated guide is backed up under `.adr-kit/backups/`. User additions
belong in `.adr-kit/ADR-guide.local.md` or outside managed markers. Setup
refuses duplicate, nested, reversed, or incomplete markers before writing.
Legacy `.agents/adr-kit-guide.md`, `.claude/adr-kit-guide.md`, and the Claude
`ADR-KIT STUB` block migrate once with content-addressed backups. Singular
`AGENT.md` is not created.

Inspect effective settings and their source:

```bash
python scripts/settings.py --project-root "/path/to/project" show
python scripts/settings.py --project-root "/path/to/project" --format json show
```

Global defaults live in `%APPDATA%\adr-kit\settings.json` on Windows and
`${XDG_CONFIG_HOME:-~/.config}/adr-kit/settings.json` on macOS/Linux.
Per-project overrides live in `.adr-kit/settings.json` and take precedence.
Use `set ... --scope global` for a global value; project is the default scope.

```bash
python scripts/settings.py --project-root "/path/to/project" set update.offline true
python scripts/settings.py --project-root "/path/to/project" set clients.codex.enabled false
python scripts/settings.py --project-root "/path/to/project" unset clients.codex.enabled
```

Pre-commit defaults on. Setting `pre_commit.enabled` to `false` and rerunning
setup removes only the ADR Kit-owned pre-commit file; setting it to `true`
reinstalls it. A custom `core.hooksPath` or unrelated pre-commit hook is never
replaced automatically.

Local judgment has no default provider or model tag. Run settings with
`--probe-models` for a bounded local identity check that does not invoke a
model. One verified candidate can become active in the optional judgment
workflow; missing, unreachable, or multiple candidates remain actionable
unavailable/degraded/ambiguous states. Paid/cloud judgment is disabled until
explicit opt-in. Deterministic checks continue independently.

Validate from a terminal:

```bash
claude plugin validate .
claude plugin details adr-kit@rvdbreemen-adr-kit
```

Expected: 15 skills, one `adr-generator` agent, six hooks, and one MCP server.

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
- 15 Codex-native skills under `codex/skills/`
- `hooks/hooks.json` with SessionStart, prompt, edit, subagent, and compact outcomes
- `.mcp.json` with the `adr-kit` server
- a self-contained, generated copy of the deterministic engines

Claude slash commands are not Codex commands. In Codex, open `/skills` and
invoke the namespaced skills, for example:

```text
$adr-kit:context
$adr-kit:judge
$adr-kit:lint
$adr-kit:adr
$adr-kit:grill ADR-NNN
```

The five MCP tools are `adr_context`, `adr_judge`, `adr_status`, `adr_quality`,
and read-only `adr_readiness`. Each accepts an optional absolute
`project_root`; the Codex skills always pass the active workspace so the server
never mistakes its plugin cache for the project.

After installation, use the
[ADR Grilling user guide](docs/adr-grilling.md) for subject-based authoring,
PR/range or source reconstruction, the Proposed queue, explicit acceptance, and
the model-free pull-request readiness gate.

## Standalone GitHub Copilot CLI

This integration targets the `@github/copilot` CLI invoked as `copilot`.

Manual install:

```bash
copilot plugin marketplace add rvdbreemen/adr-kit
copilot plugin install adr-kit@rvdbreemen-adr-kit-copilot
copilot plugin list
copilot mcp list
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
- Release archives record executable Unix modes for every directly invoked
  hook and engine, and CI exercises the manual archive contract on macOS and
  Linux. The automatic installer restores those modes defensively and embeds
  the exact Python runtime. A manual native Codex or Copilot install still uses
  the static interpreter from its checked-out `.mcp.json`; use the automatic
  installer on `python3`-only hosts.
- If the embedded Python executable is moved or removed, rerun the automatic
  installer with the replacement interpreter.
- Native marketplace mutations are isolated per client but are not one atomic
  transaction across Claude, Codex, and Copilot.

See the [2026-07-18 source audit](docs/reviews/2026-07-18-source-audit/FINDINGS.md)
for evidence and remediation recommendations.

Copilot loads `.github/plugin/marketplace.json`, which points only to the
separate `copilot/` distribution. That distribution has a root `plugin.json`,
15 Copilot-compatible skills, lower-camel `hooks.json`, and `.mcp.json`. Open
`/skills` inside Copilot CLI for discovery. It does not load the Claude or
Codex manifest.

On Windows, a sandboxed caller may have read-only access to the user's normal
`~/.copilot` directory. For CI or isolated smoke tests, set `COPILOT_HOME` to a
writable temporary directory. A normal user terminal should use the default
home.

## OpenCode

The repository root carries an OpenCode config and npm-style plugin entrypoint.
From this checkout, start OpenCode in the repository and restart it after any
plugin change. For another project, add the package or a reviewed checkout to
`opencode.json`; see [OpenCode support](docs/clients/opencode.md) for the exact
config, options, MCP registration, hook behavior, and CI setup.

The plugin discovers the canonical skills and workflow commands, adds the local
`adr-kit` MCP server without overwriting an existing entry, injects bounded ADR
context through OpenCode's system transform, carries context through
compaction, and calls the shared Python hook runtime around edits. Set
`ADR_KIT_ROOT` and `ADR_KIT_PYTHON` when the plugin and Python checkout are in
different locations. Set `ADR_KIT_OPENCODE_MCP=0` to opt out of automatic MCP
registration.

OpenCode projects still need the client-independent pre-commit and CI floor:

```bash
python /absolute/path/to/adr-kit/scripts/setup-project.py \
  --project-root /absolute/path/to/project
```

Copy the required `templates/github-workflows/` files into the project's
`.github/workflows/`. The OpenCode plugin does not replace those gates.

## Portable fallback

Agents without native plugin support can still vendor the portable source
files:

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
python scripts/build-client-adapters.py --check
python -m pytest tests/test_agent_installer.py tests/test_adr_mcp.py
```

Then validate the installed client:

```bash
claude plugin details adr-kit@rvdbreemen-adr-kit
codex mcp list
copilot plugin list
copilot mcp list
```

Routine successful integration activity is quiet by design. All three clients
receive bounded fail-open hooks plus native skills and MCP. Copilot's
PreToolUse contract cannot inject arbitrary context, so proactive context,
PostToolUse, and pre-commit provide that outcome without fake deny/retry logic.

## Updating and rollback

Verified stable updates run only from project setup or deferred maintenance,
never from a lifecycle hook. Effective settings control frequency, offline
mode, notification/manual behavior, and an optional exact pin. Pull the new
tag and re-run:

```bash
python scripts/install-agent-envs.py
```

Project ADRs under `docs/adr/` are never part of the plugin update.
The installer authenticates the repository identity, validates the prepared
payload digest, retains one previous payload, and records each client's update
trigger and last-check state.

## Uninstall

```bash
python scripts/install-agent-envs.py --uninstall
```

Uninstall removes only ADR Kit-owned registrations and marked prepared
payloads. It preserves user configuration, `.adr-kit/ADR-guide.local.md`, and
the project's `docs/adr/` directory.
