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

`docs/adr/ADR-INDEX.json` is a versioned node-and-edge catalog with lifecycle
metadata, decision summaries, enforcement scope, and declared ADR links.
Agents use it to shortlist records and then read the linked Markdown ADRs;
Markdown remains authoritative. `ADR-INDEX.md`, `ADR-INDEX.json`, and the
generated README block must never be hand-edited.

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

The installer uses separate native payloads:

| Client | Distribution | Workflow invocation |
| --- | --- | --- |
| Claude Code | repository root `.claude-plugin/`, `skills/`, `agents/` | `/adr-kit:context`, `/adr-kit:init` |
| OpenAI Codex | `codex/` | `$adr-kit:context`, `$adr-kit:init` |
| GitHub Copilot CLI | `copilot/` | namespaced ADR Kit skills |

Do not point Codex or Copilot at the Claude plugin cache.

Before calling a client API, the installer validates the complete source and
creates a persistent prepared marketplace in the operating system's per-user
data directory. Its Codex and Copilot MCP manifests contain the exact absolute
Python interpreter running the installer. On macOS and Linux it also restores
executable modes for packaged Unix entry points. Re-running with the same
release and interpreter is idempotent.

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
with the selected interpreter before client mutation. If that preflight fails,
stop: do not hand-edit an installed manifest or continue with a partial
marketplace.

## 6. Initialize the project

Run the native `init` workflow once in the project:

- Claude Code: `/adr-kit:init`
- OpenAI Codex: `$adr-kit:init`
- GitHub Copilot CLI: invoke the installed ADR Kit `init` skill

Initialization adds managed project guidance, audits existing architectural
decisions, proposes initial ADRs for review, and offers the deterministic
pre-commit gate. Use `setup` instead when the user wants guidance only, without
the audit or hook.

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
