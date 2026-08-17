# ADR Kit installation runbook for coding agents

Use this client-neutral runbook when a coding agent is responsible for
detecting, previewing, installing, validating, and initializing ADR Kit.
Detailed client background and manual recovery steps remain in
[INSTALL.md](INSTALL.md).

Do not read the full README before starting: this runbook contains the
minimum complete installation contract.

## Agent quick contract

After locating the ADR Kit checkout, discover formats and verify their
templates without reading other documentation:

```bash
python <absolute-adr-kit-checkout>/bin/adr profiles --format json
```

MADR is the preferred default. If the user chooses another format, accept only
an `id` returned by this command and use the matching `template` path. The
complete pre-made catalog is `madr`, `nygard`, and `canonical`. Do not infer a
custom profile from an arbitrary template filename or generate a replacement
when a catalog template reports `available: false`; repair or reinstall ADR Kit
first.

After initialization, agents should use the generated machine index before
opening the whole ADR set:

```bash
python <absolute-adr-kit-checkout>/bin/adr-index <absolute-target-project>/docs/adr
python <absolute-adr-kit-checkout>/bin/adr-index --check <absolute-target-project>/docs/adr
python <absolute-adr-kit-checkout>/bin/adr-context --format json --adr-dir <absolute-target-project>/docs/adr "<current task>"
```

`docs/adr/ADR-INDEX.json` is the versioned local selective-context query
database. It contains lifecycle state, summaries, retrieval metadata,
Decision Contracts, enforcement scope, fingerprints, and declared ADR links.
Agents query it to shortlist records and then read only the linked Markdown
ADRs; Markdown remains authoritative. `ADR-INDEX.md`, `ADR-INDEX.json`, and
the generated README block must never be hand-edited. See
[docs/selective-context.md](docs/selective-context.md).

## Safety and prerequisites

- Work from a pinned release tag or a reviewed checkout.
- Require Python 3.10 or newer. The default tools are stdlib-only and need no
  API key.
- Preview client mutations before installing.
- Do not replace an existing project `AGENTS.md`, `CLAUDE.md`, hooks, or ADR
  directory. Use the supplied idempotent setup and upgrade workflows.
- Keep LLM-backed judge and guardian passes opt-in. Deterministic lint,
  context, index, doctor, and Enforcement checks remain key-free.

## 1. Detect the environment

From the ADR Kit checkout:

```bash
python --version
python scripts/install-agent-envs.py --detect-only
python scripts/install-agent-envs.py --plan --format json
```

Use `python3`, `py -3`, or an absolute interpreter path when that is the
platform's normal Python command. The installer probes the child runtime and
requires Python 3.10+; it does not assume that a command literally named
`python` exists.

The detector recognizes native Claude Code (`claude`), OpenAI Codex (`codex`),
and standalone GitHub Copilot CLI (`copilot`) installations from executable
and version output. It does not treat `gh copilot`, an editor extension, or a
home-directory name as an installed CLI.

If no native client is detected, continue with the MCP, Agent Skills, or direct
CLI fallback below.

OpenCode is configuration-based rather than discovered by the three-client
installer. If `opencode` is present, configure the native plugin separately as
described in [docs/clients/opencode.md](docs/clients/opencode.md); do not add it
to the installer client list.

## 2. Preview the install

```bash
python scripts/install-agent-envs.py --dry-run --project-root <absolute-target-project>
python scripts/install-agent-envs.py --agents auto --dry-run --project-root <absolute-target-project>
```

Limit the preview when the user named specific clients:

```bash
python scripts/install-agent-envs.py --clients claude,codex --dry-run --project-root <absolute-target-project>
python scripts/install-agent-envs.py --clients copilot --dry-run --project-root <absolute-target-project>
```

Report the detected clients and planned native commands. Obtain user approval
before changing client registration.

## 3. Install through native client APIs

Install every detected client:

```bash
python scripts/install-agent-envs.py --project-root <absolute-target-project>
```

Or install an approved subset:

```bash
python scripts/install-agent-envs.py --clients codex,copilot --project-root <absolute-target-project>
```

Inspect the desired-state plan before mutation. Detected clients are selected
by default; `clients.claude.enabled`, `clients.codex.enabled`, and
`clients.copilot.enabled` provide global defaults with project overrides.
Breaking-version migrations require `--yes`. Each client has its own lock,
validation, evidence, and previous-payload rollback. Stable update checks run
from setup or deferred maintenance, never from lifecycle hooks.

The installer uses separate native payloads:

| Client | Distribution | Workflow invocation |
| --- | --- | --- |
| Claude Code | repository root `.claude-plugin/`, `skills/`, `agents/` | `/adr-kit:context`, `/adr-kit:init` |
| OpenAI Codex | `codex/` | `$adr-kit:context`, `$adr-kit:init` |
| GitHub Copilot CLI | `copilot/` | namespaced ADR Kit skills |

OpenCode uses the repository-root `opencode.json` and `package.json` plugin
entrypoint, or an explicit package entry in the target project's `opencode.json`.
It is a separate native package and is not part of the three-client installer
or certification registry.

Do not point Codex or Copilot at the Claude plugin cache.

All shipped skill descriptions are English. Claude Code context hooks request
raw-output suppression and have no routine progress label; relevant ADR context
still reaches the model through `additionalContext`. Codex and Copilot use
their native skill and MCP surfaces without installing noisy lifecycle hooks.

Before calling a client API, the installer validates the complete source and
creates a persistent prepared marketplace in the operating system's per-user
data directory. Its Codex and Copilot MCP manifests contain the exact absolute
Python interpreter running the installer. On macOS and Linux it also restores
executable modes for packaged Unix entry points. Re-running with the same
release and interpreter is idempotent.

For Copilot the installer also checks, before touching any registration, that
the plugin directory can be replaced at all. If it cannot, the run stops with a
diagnosis and changes nothing. The usual cause is an editor that has the ADR Kit
plugin loaded as an MCP server and holds the directory open; closing that editor
window releases it, while killing the server process alone does not, because the
editor restarts it within seconds. Do not work around this by deleting the
plugin directory: report the diagnosis and let the operator close the editor.

Release archives also record those Unix executable modes for manual installs;
the prepared path restores them defensively and remains preferred because it
also resolves `python` versus `python3` deterministically.

Prepared marketplace roots are platform-native:

- Windows: `%LOCALAPPDATA%\adr-kit\marketplaces`
- macOS: `~/Library/Application Support/adr-kit/marketplaces`
- Linux: `${XDG_DATA_HOME:-~/.local/share}/adr-kit/marketplaces`

## 4. Review existing ADR formats

Install and update automatically run this read-only scan when `--project-root`
points at the target project:

```bash
python <absolute-adr-kit-checkout>/bin/adr-migrate --plan <absolute-target-project>/docs/adr
```

For MADR, Nygard, or canonical files that only need metadata or filename
normalization, follow the exact `--dry-run` command in the report. For detected
Y-Statements, Tyree/Akerman records, arc42 decision sections, hybrids, and
unknown shapes, invoke the reported migrate skill and review the mapping.
Never apply a migration merely because installation detected it.

Preview retrieval metadata and Decision Contract candidates independently:

```bash
python <absolute-adr-kit-checkout>/bin/adr-migrate --suggest-retrieval --dry-run <absolute-target-project>/docs/adr
```

This mode is read-only and requires human review. After approved metadata is
applied, rebuild the index and run `adr-context --check-probes`.

## 5. Validate registration and runtime

Use the commands for every installed client:

```bash
claude plugin details adr-kit@rvdbreemen-adr-kit
codex plugin list --json
codex mcp list
copilot plugin list
copilot mcp list
copilot skill list
```

Then run one real `adr_context` call against the active project. Registration
visibility alone does not prove that the configured Python command or packaged
engine starts.

The installer already performs a packaged MCP initialize/tools-list handshake
with the selected interpreter and a platform-shell SessionStart hook smoke
before client mutation. If that preflight fails, stop: do not hand-edit an
installed manifest or continue with a partial marketplace.

## 6. Initialize the project

Run the native `init` workflow once in the project:

- Claude Code: `/adr-kit:init`
- OpenAI Codex: `$adr-kit:init`
- GitHub Copilot CLI: invoke the installed ADR Kit `init` skill
- OpenCode: invoke `/adr-kit-init` or the `init` skill exposed by the native
  plugin

Initialization adds managed project guidance, audits existing architectural
decisions, proposes initial ADRs for review, and installs the deterministic
pre-commit gate by default.

The client-neutral project registration path is:

```bash
python <absolute-adr-kit-checkout>/scripts/setup-project.py --project-root <absolute-target-project> --dry-run
python <absolute-adr-kit-checkout>/scripts/setup-project.py --project-root <absolute-target-project>
python <absolute-adr-kit-checkout>/scripts/settings.py --project-root <absolute-target-project> show
```

It writes generated `.adr-kit/ADR-guide.md` and independent ADR Kit blocks in
`AGENTS.md`, `CLAUDE.md`, and Copilot instructions. It preserves user bytes
outside markers and never overwrites `.adr-kit/ADR-guide.local.md`. To request
guidance-only setup, set `pre_commit.enabled` to `false` before applying setup;
set it back to `true` and rerun to re-enable the owned hook.

After initialization, validate the target project. Replace both placeholders
with absolute paths:

```bash
python <absolute-adr-kit-checkout>/bin/adr-doctor --fix-index <absolute-target-project>/docs/adr
python <absolute-adr-kit-checkout>/bin/adr-lint --strict <absolute-target-project>/docs/adr
```

## Fallback A: MCP

For any coding agent with a stdio MCP client, register:

```json
{
  "mcpServers": {
    "adr-kit": {
      "command": "python",
      "args": [
        "/absolute/path/to/adr-kit/bin/adr-mcp",
        "--root",
        "/absolute/path/to/project"
      ]
    }
  }
}
```

The server exposes `adr_context`, `adr_judge`, `adr_status`, and `adr_quality`.
Keep the full `bin/` directory together because engines import shared helpers.

## Fallback B: Agent Skills

For clients that implement the
[Agent Skills](https://agentskills.io/) format, vendor the required
`skills/<name>/SKILL.md` files into the client's project skill directory.
Start with `adr`, `context`, `judge`, `lint`, and `init`. Also vendor `bin/`,
`schemas/`, and `templates/` together so skill commands resolve the same
deterministic engines and profile templates.

The repository-root skills use Claude Code's native invocation conventions;
the `codex/skills/` and `copilot/skills/` packages carry their respective
client adaptations. An unlisted Agent Skills client should translate only the
invocation wrapper, never ADR metadata or lifecycle semantics. When that
translation is unavailable, use MCP or direct Python commands instead of
guessing client configuration.

If a client uses neither native plugins nor Agent Skills, add
`instructions/adr.coding.md` and `instructions/adr.review.md` to its project
instructions and use the direct CLI fallback.

## Fallback C: Direct Python commands

The core lifecycle is usable from any agent that can run Python. Replace the
checkout and target placeholders with absolute paths:

```bash
python <absolute-adr-kit-checkout>/bin/adr new "Short imperative title" --adr-dir <absolute-target-project>/docs/adr
python <absolute-adr-kit-checkout>/bin/adr profiles --format json
python <absolute-adr-kit-checkout>/bin/adr-context --adr-dir <absolute-target-project>/docs/adr --format json "current task"
python <absolute-adr-kit-checkout>/bin/adr-context --adr-dir <absolute-target-project>/docs/adr --check-probes
python <absolute-adr-kit-checkout>/bin/adr-migrate --plan <absolute-target-project>/docs/adr
python <absolute-adr-kit-checkout>/bin/adr-lint --strict <absolute-target-project>/docs/adr
python <absolute-adr-kit-checkout>/bin/adr-index --check <absolute-target-project>/docs/adr
python <absolute-adr-kit-checkout>/bin/adr-doctor <absolute-target-project>/docs/adr
```

New ADRs default to MADR. Set `template.profile` in
`docs/adr/.adr-kit.json` to `madr`, `nygard`, or `canonical`, or pass
`adr new --profile ...` for one record. These are the only shipped selectable
profiles. First query `adr profiles --format json`, then use the selected
entry's template; never invent a profile name. Existing canonical records
remain valid. MADR is the default because explicit problem, driver, option, outcome,
trade-off, and confirmation fields give agents less meaning to infer from
prose. This is an agent-reliability choice, not a claim of highest global
usage; no authoritative format census exists. Nygard is the concise option,
and canonical is the compatibility option. Read the
[format evaluation](docs/research/adr-format-evaluation.md) or
[ADR-005](docs/adr/ADR-005-selectable-agent-friendly-adr-formats.md) when the
project needs the full scoring and rationale.

Preview any conversion:

```bash
python <absolute-adr-kit-checkout>/bin/adr-migrate --dry-run --to-profile madr <absolute-target-project>/docs/adr
```

The complete detection matrix and safety contract are in
[docs/format-migration.md](docs/format-migration.md).

## Final handoff

Report:

1. detected clients and selected install path;
2. exact registration and runtime validation results;
3. initialization mode (`init`, `setup`, or deferred);
4. selected ADR profile and any compatibility adjustment;
5. remaining platform limitation or manual action.
