# adr-kit

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/tag/rvdbreemen/adr-kit?label=release&sort=semver)](https://github.com/rvdbreemen/adr-kit/releases)

**Architecture decisions your AI coding agents actually follow.**

> **Coding agent installing ADR Kit?** Read
> **[INSTALL-AGENT.md](INSTALL-AGENT.md)** and stop there. It is the short,
> client-neutral runbook for detection, preview, installation, project
> initialization, and verification across native and portable agent setups.

**Agent choosing an ADR format?** Run
`python bin/adr profiles --format json`. MADR is the preferred default.
If the user chooses another format, accept only a returned profile id and
use its returned shipped template path. ADR Kit currently ships complete
templates for `madr`, `nygard`, and `canonical`; never invent a profile name
or synthesize an unregistered template.

**Agent finding the ADRs for a task?** Read
`docs/adr/ADR-INDEX.json` first, or run
`python bin/adr-context --format json "<task>"`. Use its status, scope,
relationship graph, relevance signals, and source paths to shortlist records;
then open the referenced Markdown ADRs before applying a constraint. Regenerate
all indexes with `python bin/adr-index docs/adr` and verify them with
`python bin/adr-index --check docs/adr`. Never hand-edit either generated index.

`adr-kit` turns Architecture Decision Records from passive documentation into active guardrails. Your agent gets the relevant decisions injected while it codes, every commit is checked against the accepted decisions, and a guardian watches for decisions that go stale. One toolkit covers the whole lifecycle: capture, enforce, maintain, retire.

Ships native, separate plugins for Claude Code, OpenAI Codex, and the standalone GitHub Copilot CLI, plus portable files for Cursor, Claude Cowork, and any agent that supports the [Agent Skills](https://agentskills.io/) format. The engines are dependency-free Python 3.10+ (stdlib only, no build step, no API key required for any default path).

> **Pre-1.0**: functional and in daily use, but conventions may still evolve before v1.0.0. Pin a tag if you need stability across upgrades.
>
> **Audit posture**: the [2026-07-18 source audit](docs/reviews/2026-07-18-source-audit/FINDINGS.md) drove fail-closed enforcement, exact staged-snapshot handling, transaction-safe lifecycle/state updates, and cross-platform packaging fixes. ADR Kit remains a development guardrail, not a sandbox, branch-protection replacement, or sole merge control.

## Why

AI coding agents are fast, confident, and have no memory of why your system is built the way it is. Left alone, they will cheerfully reintroduce the database driver you migrated away from, bypass the repository layer you standardized on, and make new architectural decisions without telling anyone. Human teams have the same failure mode, just slower.

ADRs are the established answer: short markdown files in your repo that record the problem, the decision, the alternatives rejected, and the consequences accepted. What was always missing is **enforcement**. A decision nobody re-reads is a decision nobody follows.

`adr-kit` closes that loop three times over:

1. **Before the agent edits**: the decisions relevant to the task are ranked and injected as context.
2. **While the agent edits**: a hook nudges it the moment a change touches files governed by a decision.
3. **When the work lands**: declarative rules from each ADR are checked against the diff at commit time and in CI, deterministically and key-free.

And because decisions age, a periodic guardian flags drift between code and decisions, retirement candidates, and decisions that were made but never recorded.

## Install

Coding agents should follow [INSTALL-AGENT.md](INSTALL-AGENT.md). The sections
below are the human-oriented quick reference.

### Install every detected CLI

From a cloned checkout:

```bash
python scripts/install-agent-envs.py --detect-only
python scripts/install-agent-envs.py --project-root /path/to/project
```

The installer verifies real executable and version output for `claude`, `codex`,
and the standalone `copilot` CLI. It installs ADR Kit through every detected
client's native plugin API on Windows, macOS, and Linux. Before touching a
client, it validates the complete source and the Python 3.10+ interpreter that
is running the installer. It prepares a persistent user-local marketplace with
that exact interpreter embedded in the Codex and Copilot MCP configuration,
then completes a real MCP initialize/tools-list smoke test.
Use `--clients codex,copilot`, `--dry-run`, or `--source /path/to/adr-kit` for
explicit and automated installs. The post-install format scan is read-only:
it reports deterministic preview commands or guided migration steps and never
rewrites an ADR.

### Claude Code

```
/plugin marketplace add rvdbreemen/adr-kit
/plugin install adr-kit@rvdbreemen-adr-kit
/reload-plugins
/adr-kit:init
```

The first three install the plugin. The fourth is the one-shot per-project bootstrap: it wires a slim stub into your `CLAUDE.md` (full guide lands at `.claude/adr-kit-guide.md`), **audits your existing codebase for decisions already in effect** (the database you chose, the framework you committed to, the patterns you standardized on) and walks you through recording them as Accepted ADRs in batches, then installs the pre-commit enforcement hook. Idempotent: safe to re-run.

That is the whole setup. From the next session on, your agent knows the decisions, gets nudged when it touches them, and receives a local check when it commits.

Prefer a lighter start? `/adr-kit:setup` writes only the `CLAUDE.md` stub and guide, skipping the audit and the hook; you can add those later with `/adr-kit:init` or `/adr-kit:install-hooks`.

The Claude integration remains rooted in `.claude-plugin/`, the original
`skills/`, and the existing three hooks.

### OpenAI Codex

```bash
codex plugin marketplace add rvdbreemen/adr-kit
codex plugin add adr-kit@rvdbreemen-adr-kit-codex
codex mcp list
```

Codex does not use Claude's `/adr-kit:...` slash-command syntax. ADR Kit
workflows appear as namespaced skills: open `/skills`, or invoke
`$adr-kit:context`, `$adr-kit:judge`, `$adr-kit:lint`, and the other skills.
The separate `codex/` distribution contains all 14 workflows and the key-free
four-tool MCP server. See the official [Codex skills](https://learn.chatgpt.com/docs/build-skills)
and [plugin](https://learn.chatgpt.com/docs/build-plugins) contracts.

### Standalone GitHub Copilot CLI

```bash
copilot plugin marketplace add rvdbreemen/adr-kit
copilot plugin install adr-kit@rvdbreemen-adr-kit-copilot
copilot plugin list
copilot mcp list
copilot skill list
```

This targets `@github/copilot` invoked as `copilot`, not `gh copilot` or VS
Code agent mode. The separate `copilot/` distribution follows GitHub's
[Copilot plugin contract](https://docs.github.com/en/copilot/concepts/agents/about-plugins)
and installs 14 skills plus the same key-free MCP server.

### Cursor, Claude Cowork, and other agents

[INSTALL.md](INSTALL.md) documents the native plugin layouts and portable
fallbacks.

On top of the file install, every tool that speaks MCP (Cursor, Cline, Windsurf, Copilot, Codex) can connect to the bundled [MCP server](#mcp-server-binadr-mcp) for the enforcement and context tools; see below.

The CLI engines under `bin/` require Python 3.10+, with no pip install. The
automatic installer embeds the absolute interpreter that launched it, so
Windows `python.exe` and Unix `python3`-only installations need no manual MCP
manifest edit. See [INSTALL.md](INSTALL.md).

### Upgrading

Three layers, each with a clear path:

- **The plugin itself**: updates through the normal Claude Code plugin update flow. The engines (judge, guardian, context ranker) always resolve the newest installed version automatically, so hooks you installed earlier keep running current code without any action.
- **Copied artifacts** (the git pre-commit wrapper, the project-scoped settings entry, the guide file): these freeze at install time by nature. Since v0.27.0 they carry version stamps, and the guardian tells you at session start when one lags the installed plugin (`wrapper: ... STALE`). Run `/adr-kit:upgrade` and they are refreshed idempotently; the same command still handles the legacy v0.11 to v0.12 footprint migration. You can inspect the state any time with `bin/adr-guardian artifacts`.
- **Existing ADR sets**: MADR and Nygard are first-class selectable profiles,
  and the older adr-kit canonical profile remains valid without rewriting.
  `bin/adr-migrate --plan docs/adr` detects metadata/filename upgrades and
  common external formats without writing. It prints deterministic dry-run
  commands where safe and guided migration instructions otherwise.

## The lifecycle: capture, guard, maintain

### Capture decisions (and stop rationalizing them away)

- **`/adr-kit:adr`** loads the full authoring guide. Its two signature disciplines, borrowed and battle-tested from earlier skills (see [Credits](#credits)):
  - **Anti-rationalization guards**: a table of the excuses agents and humans use to skip writing an ADR ("it is obvious", "I will document it later", "the code speaks for itself"), each with a counter-argument. Fires before the decision goes unrecorded.
  - **Four verification gates**: Completeness, Evidence, Clarity, Consistency. An ADR cannot flip from `Proposed` to `Accepted` until it passes all four, and a reviewer can block on a single named gate ("fails Evidence, add measurements").
- **`adr-generator` agent** scaffolds the ADR for you: decision tree for "does this need an ADR?", a proposed `## Enforcement` block when the decision has a code surface, and a post-write quality check.
- **`/adr-kit:init`'s audit** mines an existing codebase for decisions already in effect, so you start with a real decision log instead of an empty directory.
- **`/adr-kit:review`** audits a finished branch or PR: it enforces the existing ADRs against the committed range diff and, crucially, hunts for **new decisions the branch introduced but never recorded**, reading both the diff and the stated intent (commit messages, PR description), because decisions are often confessed in prose while the diff looks like plumbing. Found candidates are deduped against your existing set and drafted as `Proposed`, never auto-accepted.
- **`bin/adr-suggest`** (opt-in) runs the same missing-decision detector per commit and prints a one-line nudge. It never blocks.

### Guard the agent while it works

- **Context lookup (`/adr-kit:context`, `bin/adr-context`)**: give it a topic ("mqtt discovery", "caching") and it returns the 3 to 5 most relevant ADRs with path, status, format, one-line decision, enforcement scope, declared relationships, invariant metadata, and five explainable ranking signals. Proposed ADRs can appear, so treat the result as a shortlist and open each source ADR before applying it.
- **In-flight nudges (`bin/adr-watch`, v0.24.0+)**: a PostToolUse hook fires after every Edit/Write in Claude Code and checks the touched file against the Accepted ADRs (Enforcement path globs first, keyword relevance second):

  ```
  [adr-watch] ADR-007 (no direct DB calls outside repository layer) may apply to src/db/foo.py
  ```

  Deterministic, key-free, under 100ms, never blocks, and a per-session cooldown keeps it from nagging. This closes the gap between session-start context and commit-time enforcement: the agent is corrected **while the file is still open**.
- **Edit-tier injection (`bin/adr-watch --pre-edit`, v0.31.0+)**: a PreToolUse hook fires *before* every Edit/Write and injects the top-ranked governing ADR's `## Decision` text (bounded to a token budget), so the agent honours the decision **as it writes**, not after. The PostToolUse nudge above stays as a confirmation backstop. Same deterministic matcher, key-free, exits 0. Formalised in [ADR-004](docs/adr/ADR-004-layered-adr-context-injection.md).
- **Decision indexes (`bin/adr-index`)**: generates two deterministic, timestamp-free views from the same format-aware records. `docs/adr/ADR-INDEX.md` is the compact one-row-per-ADR session map imported by `CLAUDE.md`; `docs/adr/ADR-INDEX.json` is the versioned agent graph containing semantic metadata and sorted declared relationship edges. Markdown ADRs remain authoritative.
- **Commit-time enforcement (`bin/adr-judge` + pre-commit hook)**: every ADR can carry a fenced JSON `## Enforcement` block with declarative rules (`forbid_pattern`, `forbid_import`, `require_pattern`, each optionally scoped by `path_glob`). On every `git commit` the hook runs those rules against the staged diff with file:line citations. Fast, deterministic, no LLM, no API key. ADRs whose rules are too nuanced for regex can set `llm_judge: true` for an opt-in model-reviewed pass instead.
- **PR-time enforcement in CI**: the same judge can run as a composite GitHub Action or through the `pre-commit` framework, giving local and CI workflows the same deterministic rule set. See [CI integration](#ci-integration) and the audit notice above for current limitations.
- **Audited escape hatch**: hotfix has to land despite a FAIL? `ADR_KIT_OVERRIDE="ADR-003: hotfix for incident 42" git commit ...` downgrades that one ADR's violations to loud warnings, refuses an empty reason, logs the override locally, and pairs with an `ADR-Override:` commit trailer convention you can reconcile later with `adr-judge --audit-overrides`. Guardrails with a paper trail instead of `--no-verify` folklore.

### Maintain the decision log (decisions age; the kit notices)

- **The Guardian (`bin/adr-guardian`, `/adr-kit:guardian`)**: a session-start staleness detector with two tiers. The cheap tier (daily, free) checks for code drift against Enforcement rules, retirement candidates, and lint health. The LLM tier (bi-weekly, asks before spending) hunts for missing ADRs and runs the full model-reviewed audit. Findings get mixed responses by type: drift is surfaced loudly with file:line, missing decisions are offered for authoring, stale ADRs get a retirement draft for review. Never runs in the background, never spends without asking.
  - **Team mode (v0.22.0+)**: a weekly CI cron sweep maintains a single "ADR guardian audit" tracking issue (created on findings, updated, closed when clean) so the whole team sees ADR health, not just whoever opened a session today. Copy `templates/github-workflows/adr-guardian-audit.yml` into your repo.
  - **Trend history (v0.29.0+)**: every sweep appends to a 52-entry trend log, and the nudge shows the delta: `trend: drift 2 -> 0, retire 1 -> 2, coverage 40% -> 45%`. A KPI with memory, not a snapshot.
- **Health dashboard (`bin/adr-status`)**: totals, status breakdown, average age, enforcement health, retirement candidates, and since v0.29.0 the **Enforcement coverage percentage** of your Accepted ADRs. JSON, markdown, or table.
- **Quality scoring (`bin/adr-quality`)**: grades every ADR A to D across the four gates (Completeness 40%, Evidence 20%, Clarity 20%, Consistency 20%), with per-gate issue codes. Exits 1 below grade B, so you can gate CI on ADR quality.
- **Generated index refresh (`bin/adr-index docs/adr/`)**: atomically rebuilds the sentinel-owned `docs/adr/README.md` block plus `ADR-INDEX.md` and `ADR-INDEX.json`. `--check` exits non-zero when any generated view is missing or stale, or duplicate ADR ids exist. Use `--format graph --adr-dir docs/adr` to inspect the graph without writing.
- **Local doctor (`bin/adr-doctor`)**: runs strict lint plus generated-index freshness checks, then nudges on shipped-but-still-Proposed ADRs, old Proposed ADRs, Accepted ADRs whose `verified_in` files changed after acceptance, and missing named gates. Material drift auto-triggers a local `bin/adr-audit --root ...` pass and includes the audit summary in the doctor output. `--fix-index` repairs the generated index before checking it.
- **Lifecycle commands (`bin/adr`, v0.32.0+)**: local `propose`, `accept`, `supersede`, `reject`, and `document` commands update frontmatter, the Status section, append-only Status History, reciprocal supersession links, and then refresh the generated README index.
- **After-the-fact acceptance (`bin/adr document` + `bin/adr accept --auto`)**: mark already-shipped behavior with `documents_shipped:true` and local `verified_in` pointers, then auto-accept only when strict lint and quality checks pass. `--auto-mode assist` reports eligibility without mutating until confirmed.
- **Retirement audit (`/adr-kit:retire`, `bin/adr-retire`)**: ranks Accepted ADRs for retirement using four deterministic signals (status age, technology removal, supersession, policy drift). Read-only; a recommendation always needs a human.
- **Dependency graph (`/adr-kit:related`, `bin/adr-related`)**: who does ADR-007 point at, and who points back? Outbound and inbound edges per declared reference kind, with dangling links flagged. The same normalized edges are available repository-wide in `ADR-INDEX.json`.
- **Guided supersession (`/adr-kit:supersede`)**: replace a decision without rewriting history. The skill shows the dependency graph first, drafts the successor as `Proposed`, and asks before changing lifecycle state. The lifecycle CLI enforces legal transitions and all acceptance gates, rejects competing chains, and updates both records plus generated indexes in one rollback-safe transaction.
- **Team-safe numbering (`bin/adr-renumber`, v0.23.0+)**: two branches both claim ADR-043, both pass CI in isolation, the collision appears after merge. The lint gate fails the duplicate with both files named, and `adr-renumber` moves one to a free number, dry-run first, updating every cross-reference in the set (and never touching ADR-0430 when you renumber ADR-043).
- **Lint (`/adr-kit:lint`, `bin/adr-lint`)**: validates every ADR against the gates with file:line citations and three result tiers (PASS, ADVISORY, FAIL). Every run also emits read-only migration notices for supported legacy files, Y-Statements, Tyree/Akerman records, arc42 decision sections, hybrids, and unknown ADR shapes. It provides an exact deterministic preview when safe and guided review otherwise; it never migrates automatically. The CLI form is deterministic and CI-ready; `--strict` enables canonical frontmatter validation, local `verified_in` evidence resolution, reciprocal supersession checks, and binding gate lookup for CI. The skill form adds model judgement on the Evidence and Clarity gates.

## MCP server: `bin/adr-mcp`

A deliberately thin MCP server (stdio, newline-delimited JSON-RPC 2.0, Python stdlib only, zero dependencies) that exposes the guardrails to any MCP client: Cursor, Cline, Windsurf, Copilot, or Claude Code itself. Four tools, all key-free:

| Tool | Arguments | Wraps |
| --- | --- | --- |
| `adr_context` | `query` (string), `limit?` (int) | `adr-context --format json` |
| `adr_judge` | `diff` (string) | `adr-judge` (declarative pass only) |
| `adr_status` | none | `adr-status --format json` |
| `adr_quality` | `adr_id?` (string) | `adr-quality --format json` per ADR |

```bash
# Claude Code
claude mcp add adr-kit -- python /path/to/adr-kit/bin/adr-mcp --root "$(pwd)"
```

For Cursor, Cline, and other stdio clients, place the following in the
client's MCP configuration file (for example `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "adr-kit": {
      "command": "python",
      "args": ["/path/to/adr-kit/bin/adr-mcp", "--root", "/path/to/your/project"]
    }
  }
}
```

Why only four tools? Contrast is the feature: the 73-tool approach already exists elsewhere. adr-kit ships the smallest surface that carries the guardrails and nothing that needs an API key.

## Slash commands

`/adr` and `/adr-kit:adr` invoke the same skill; the prefix form is canonical.

| Command | Type | Auto-invocable | When to use |
|---|---|---|---|
| `/adr [title]` | knowledge / guide | yes | Author or review an ADR: anti-rationalization guards, four gates, supersession workflow. |
| `/adr-kit:init` | one-time bootstrap | no | Once per project: CLAUDE.md stub, codebase audit to Accepted ADRs, pre-commit hook. |
| `/adr-kit:setup` | one-time write | no | Lighter alternative: stub plus guide only, no audit, no hook. Idempotent. |
| `/adr-kit:context [topic]` | read-only lookup | yes | Load the 3 to 5 most relevant ADRs before implementing; verify lifecycle status in the source ADR. |
| `/adr-kit:judge` | deliberate check | yes | Interactively review a staged diff against the ADRs, including the LLM pass for `llm_judge: true` ADRs, with three resolution paths per violation. |
| `/adr-kit:review [base-ref]` | deliberate check | yes | Audit a branch/PR range: enforce ADRs on the committed diff, then discover undocumented decisions from diff plus stated intent and draft them as Proposed. |
| `/adr-kit:guardian [cheap\|llm\|all]` | health sweep | yes | Run the due guardian tier(s); LLM tier asks before spending unless project configuration explicitly enables autorun. |
| `/adr-kit:lint [path]` | deliberate check | no | Validate ADRs against the four gates; PASS / ADVISORY / FAIL with citations. Read-only. |
| `/adr-kit:related [ADR-NNN]` | deliberate check | yes | Dependency graph for one ADR: inbound and outbound edges, dangling refs flagged. Read-only. |
| `/adr-kit:supersede [ADR-NNN]` | guided write | no | Replace a decision: graph first, Proposed draft, approval-gated status flip, verified chain. |
| `/adr-kit:retire [path]` | deliberate check | no | Rank Accepted ADRs for retirement on four deterministic signals. Read-only. |
| `/adr-kit:migrate [path]` | guided rewrite | no | Add invariant metadata or convert between MADR, Nygard, and canonical profiles. Preview, then confirm. |
| `/adr-kit:install-hooks` | installer | no | Install or remove the pre-commit hook and the project-scoped guardian hook entry. |
| `/adr-kit:upgrade` | refresh driver | no | Refresh stale copied artifacts after a plugin update; also the legacy v0.11 to v0.12 migration. |

The `Auto-invocable` column reflects the shipped skill metadata. Mutating skills and several deliberate read-only commands set `disable-model-invocation: true`; `judge`, `review`, and `guardian` currently do not. Model invocation does not by itself authorize file mutation, and cost-bearing guardian work still follows its confirmation/configuration rules.

## ADR conventions

- **Filename**: `ADR-XXX-kebab-case-title.md`, 3-digit zero-padded, in `docs/adr/`.
- **Heading**: `# ADR-XXX Title`.
- **Body profile**: MADR is the default. Nygard and the legacy canonical
  adr-kit profile are selectable. Tools map their headings to shared semantic
  roles instead of assuming one spelling.
- **Status values**: `Proposed`, `Accepted`, `Deprecated`, `Superseded by ADR-YYY`, `Amended by ADR-YYY`.
- **Status history**: an append-only YAML block records every transition (`date`, `status`, `changed_by`, `reason`, `changed_via`); the lint audit gate validates chronology and agreement with `## Status`.
- **Canonical frontmatter**: `bin/adr-migrate` can add a local metadata block above legacy ADR prose without changing the body. The schema is [`schemas/adr-frontmatter.schema.json`](schemas/adr-frontmatter.schema.json) and carries the fields agents need for higher-quality local recall:
  - `id`, `title`, `status`, `date`: the stable identity and lifecycle state.
  - `binding`, `gate`: whether the decision constrains future work and which consuming-repo gate proves it.
  - `documents_shipped`, `verified_in`: evidence for after-the-fact ADRs that document already-shipped behavior.
  - `supersedes`, `superseded_by`: lifecycle links that tools can check for reciprocity.
  - `format`: optional per-file `madr`, `nygard`, or `canonical`
    discriminator; legacy files are detected by headings.

Create the next Proposed record with:

```bash
python bin/adr profiles
python bin/adr new "Short imperative title" --adr-dir docs/adr
python bin/adr new "Concise Nygard record" --profile nygard --adr-dir docs/adr
```

The strict filename contract remains uppercase `ADR-` plus a three-digit
number. Existing canonical records remain valid. `adr profiles` is the
authoritative pre-made profile catalog: each entry includes its installed
template path and availability. If a user selects a non-default format, use
only an id from that catalog. A profile cannot be selected merely by adding an
arbitrarily named template file.

Choose a profile by how much authoring structure the team wants:

| Profile | Best fit | Trade-off |
| --- | --- | --- |
| `madr` (default) | Agent-assisted decisions needing explicit drivers, options, outcome, confirmation, and pros/cons | Most complete, but longer to author |
| `nygard` | Compact human-written records centered on context, decision, and consequences | Faster to scan, with adr-kit extension sections required for deterministic gates |
| `canonical` | Existing adr-kit repositories and the pre-v0.34 section layout | Maximum backward compatibility, with less explicit decision guidance than MADR |

### Why MADR is the default

MADR is the default because it is the most agent-friendly of the commonly used
lightweight ADR formats, not because adr-kit claims it has the largest global
usage. No authoritative format census exists. This is an agent-reliability
choice. In adr-kit's
[weighted evaluation](docs/research/adr-format-evaluation.md), MADR scored
4.52/5: its explicit problem, drivers, options, outcome, pros/cons, and
confirmation slots reduce how much an agent must infer from free-form prose.
Nygard remains selectable because it has the strongest concise-format and
public-tooling signal. The canonical profile remains selectable so existing
adr-kit repositories never need a forced rewrite. The complete rationale and
compatibility decision are recorded in
[ADR-005](docs/adr/ADR-005-selectable-agent-friendly-adr-formats.md).

All three retain the same lifecycle metadata, status history, relationships,
references, and Enforcement contract.

## Configuration

All configuration lives in one optional file: `docs/adr/.adr-kit.json` (annotated sample: [`examples/.adr-kit.sample.json`](examples/.adr-kit.sample.json), schema: `schemas/adr-kit-config.schema.json`). Everything has safe defaults; you only add what you want to change.

### Lint policy: strict on new, advisory on legacy

```json
{
  "strict_from": "ADR-042",
  "ignore": ["ADR-001", "ADR-007"],
  "severity": {
    "completeness": "advisory_before_strict_from",
    "audit": "always_strict",
    "evidence": "advisory_before_strict_from",
    "clarity": "always_advisory",
    "consistency": "always_strict"
  },
  "template": {
    "profile": "madr"
  }
}
```

- `strict_from`: first ADR id on which the gates are enforced strictly; older ADRs lint in advisory mode.
- `severity`: per-gate override (`always_strict`, `always_advisory`, `advisory_before_strict_from`). Audit and consistency stay strict by default: broken status chains and duplicate numbers are real bugs regardless of age.
- `template.profile`: operational creation default: `madr` (default),
  `nygard`, or `canonical`. These are the shipped profile catalog; `--profile`
  overrides one `adr new` call.
- `template.required_sections`: advanced lint-only heading override. It does
  not register a new selectable profile, create a template, or add semantic
  role parsing.
- Per-file markers for one-off grandfathering: `<!-- adr-kit-lint: skip -->`, `skip <gate>[, ...]`, or `advisory` anywhere in an ADR.

### LLM passes: always opt-in, never surprise cost

```json
{
  "judge":   { "llm_enabled": false, "llm_model": "claude-sonnet-4-6", "llm_timeout_seconds": 120 },
  "suggest": { "enabled": false },
  "guardian": {
    "enabled": true,
    "drift_stale_days": 1,
    "llm_stale_days": 14,
    "nudge_cooldown_hours": 24,
    "llm_autorun": false
  },
  "watch": { "enabled": true, "cooldown_hours": 4 }
}
```

- The pre-commit hook's declarative pass is always on and free. The LLM judge pass is opt-in (`judge.llm_enabled`, or `ADR_KIT_LLM=1` per commit; `ADR_KIT_NO_LLM=1` to suppress). A flock guard serializes LLM passes across parallel commits.
- `suggest.enabled` (or `ADR_KIT_SUGGEST=1` per commit) turns on the advisory missing-decision nudge; it never blocks and silently skips on any failure.
- The guardian's cheap tier is free and daily; the LLM tier is bi-weekly and always asks first unless you set `llm_autorun: true` (not recommended; see ADR-001 in this repo).
- `watch` tunes the in-flight nudges; `cooldown_hours: 0` disables the cooldown, `enabled: false` silences the watcher.

State lives in `docs/adr/.adr-kit-state.json`: gitignored, per-machine, atomic writes, safe across parallel sessions.

## CI integration

### PR enforcement: `bin/adr-judge` (composite action)

```yaml
# .github/workflows/adr-judge.yml
name: ADR enforcement
on:
  pull_request:
    branches: [main]
jobs:
  adr-judge:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0        # both sides of the diff must be available
      - uses: rvdbreemen/adr-kit/.github/actions/adr-judge@v0.34.0
        with:
          adr-dir: docs/adr/
```

Declarative-only by default: no LLM, no secrets, no API key. Exit codes: `0` clean, `1` violation, `2` config error. An inline no-action-dependency variant is in the workflow file history of this repo (`curl` the script, pipe `git diff origin/base...HEAD` into it); the script is stdlib-only so CI needs no pip install.

### `pre-commit` framework

```yaml
repos:
  - repo: https://github.com/rvdbreemen/adr-kit
    rev: v0.34.0
    hooks:
      - id: adr-judge
```

### Lint gate: `bin/adr-lint`

```yaml
adr-lint:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: '3.11' }
    - name: Fetch adr-lint
      run: |
        curl -fsSL -o /tmp/adr-lint \
          https://raw.githubusercontent.com/rvdbreemen/adr-kit/main/bin/adr-lint
        chmod +x /tmp/adr-lint
    - name: Lint ADRs
      run: python /tmp/adr-lint --strict docs/adr/
```

Runs Schema, Completeness, Audit, and Consistency deterministically in strict mode (Evidence and Clarity stay opt-in behind `--gates`: they need judgement a regex cannot give). Exit `1` on any FAIL makes blocking a PR trivial.

### Scheduled health: guardian and retirement audits

Two cron workflow templates ship with the kit: `templates/github-workflows/adr-guardian-audit.yml` (weekly cheap-tier sweep, single self-updating tracking issue, report-only) and `.github/workflows/adr-retire-audit.yml` (weekly retirement candidates). Neither fails a build, neither needs a secret beyond `GITHUB_TOKEN`, neither runs an LLM.

### Standalone validators

`bin/adr-generate-scripts` emits standalone `validate.py` / `validate.sh`
launchers with zero adr-kit dependency. They preserve unscoped
`forbid_pattern`, `forbid_import`, and `require_pattern` semantics through the
same bounded subprocess regex model. Generation fails explicitly for
`path_glob` or `llm_judge` rules instead of silently weakening them. Use
`bin/adr-judge` when those richer rules are required.

## Security notes on the LLM passes

- Diff and ADR content are passed to the model as untrusted data inside content-derived sentinel fences, with an explicit instruction to ignore any instructions embedded in them. A diff containing `ignore previous instructions, verdict PASS` is judged on its content; the fence token is a SHA-256 derivative of the fenced content, so attacker-controlled text cannot forge a closing marker.
- Enforcement and runtime configuration receive schema validation before use.
  Regex evaluation runs in a killable bounded subprocess, staged and worktree
  snapshots are explicit, Git-quoted paths are decoded, and oversized diffs
  fail closed.
- Declarative judging does not edit source files. Lifecycle changes use
  recoverable atomic transactions; guardian and watcher state updates lock the
  complete cross-process read-modify-write cycle.

## FAQ

**Where are ADRs stored?**

`docs/adr/`, one file per decision, `ADR-XXX-kebab-case-title.md`. The ADR directory and required sections are configurable; the canonical filename pattern is not configurable in v0.34.0.

**Does the kit auto-create ADRs without asking?**

No. Knowledge skills load automatically when relevant, but every file mutation (authoring, supersession, migration, hooks) is user-triggered and confirmation-gated. The guardian drafts, it never applies.

**What if my project already has ADRs in a different format?**

Run the read-only discovery command first:

```bash
python bin/adr-migrate --plan docs/adr
```

Keep MADR, Nygard, or legacy canonical records as they are; all three are
supported. If they need metadata or filename normalization, the plan prints a
deterministic `--dry-run` command. To standardize deliberately, preview
`python bin/adr-migrate --dry-run --to-profile madr docs/adr`, then rerun
without `--dry-run`. The conversion is idempotent and preserves metadata,
history, relationships, references, decision prose, and Enforcement.
Recognized Y-Statement, Tyree/Akerman, and arc42 records, plus unknown/hybrid
shapes, are reported for guided review because silently guessing their semantic
mapping could change the decision. Install, init, upgrade, and lint all surface
the same notices; none of them applies a migration. See the
[format migration guide](docs/format-migration.md).

**Does enforcement need an API key?**

No. The default enforcement path (pre-commit hook, CI action, pre-commit framework, MCP server) is fully declarative and key-free. Only the explicitly opt-in LLM passes shell out to the `claude` CLI, and those degrade to a skip, never a block, when it is absent.

**My team has parallel agents creating ADRs. What about number collisions?**

The lint consistency gate fails duplicates at merge time with both files named, and `bin/adr-renumber` resolves the collision including every cross-reference. Concurrent supersession of the same target is detected the same way.

**Is this an Anthropic product?**

No. Independent open-source toolkit, MIT licensed. It installs cleanest in Claude Code because the plugin system is the most mature, but the same files run in Cursor, Copilot, Codex, and friends.

## Comparison

A plain ADR template gives you a markdown file with sections to fill in. What `adr-kit` adds:

| Concern | Plain ADR template | adr-kit |
|---|---|---|
| Format | one file | one file plus a generator agent and codebase audit |
| Pre-flight discipline | absent | anti-rationalization guards (9 excuses, 9 counter-arguments) |
| Acceptance bar | "fill it in" | four named verification gates before Proposed flips to Accepted |
| While coding | absent | context injection per task plus in-flight file nudges |
| Enforcement | absent | declarative rules vs every commit and PR, key-free; opt-in LLM judge |
| Aging | absent | guardian (drift, missing, stale), retirement audit, trend history, coverage KPI |
| Team workflows | absent | CI sweeps with tracking issue, collision-safe numbering, audited overrides, guided supersession |
| Tool integration | none | Claude Code plugin, Cursor / Copilot / Codex file installs, 4-tool MCP server |

If your team is happy with a plain template and the discipline lives in your culture, you do not need this. If you want the discipline to survive contact with an AI agent at 2 a.m., this is what `adr-kit` is for.

## Repository map

```
adr-kit/
├── skills/            # 14 Claude Code skills (unchanged native integration)
├── codex/             # separate Codex plugin, 14 skills, MCP, packaged engines
├── copilot/           # separate standalone Copilot CLI plugin
├── scripts/           # detected-client installer and payload sync check
├── agents/            # adr-generator subagent
├── bin/               # 20 stdlib-only Python entry points plus shared helpers
├── templates/         # selectable MADR/Nygard/canonical templates, guide, hooks, CI workflows
├── schemas/           # config + Enforcement JSON schemas
├── instructions/      # per-path rules for coding and review work
├── tests/             # comprehensive pytest unit and end-to-end suite
├── docs/adr/          # this repo's own ADRs (we eat the dog food)
└── docs/research/     # the landscape research behind the roadmap
```

## Project resources

- [ROADMAP.md](ROADMAP.md): direction, v1.0.0 criteria, deliberate non-goals.
- [INSTALL.md](INSTALL.md): per-tool manual install paths and the all-tools script.
- [MIGRATING-FROM-ADR-SKILL.md](MIGRATING-FROM-ADR-SKILL.md): switching from Jim van den Breemen's adr-skill.
- [CHANGELOG.md](CHANGELOG.md): full history, Keep a Changelog format.
- [CONTRIBUTING.md](CONTRIBUTING.md): dev loop, add-a-skill, release procedure, code style.
- [SECURITY.md](SECURITY.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- [2026-07-18 source audit](docs/reviews/2026-07-18-source-audit/FINDINGS.md): multi-perspective findings and verification evidence for v0.33.0.

## Credits

The default is [MADR](https://adr.github.io/madr/), with selectable
[Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
and backward-compatible canonical profiles. The
[format evaluation](docs/research/adr-format-evaluation.md) records the
evidence and trade-offs.

The two distinguishing authoring patterns, **anti-rationalization guards** and **verification gates**, were first combined into a single ADR skill by [Jim van den Breemen's adr-skill](https://github.com/Jvdbreemen/adr-skill); that pairing is what turns a template into a discipline tool. The original sources of the patterns: [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) (guards) and [trailofbits/skills](https://github.com/trailofbits/skills) (gates).

`adr-kit` builds on that foundation with the enforcement, guarding, and maintenance layers: the judge, the watcher, the guardian, the graph and supersession tooling, the MCP server, and the per-tool install paths.

## License

MIT. See [LICENSE](LICENSE). Issues and PRs welcome; the skill is intentionally domain-agnostic, so project-specific examples belong in your own copy, not upstream.
