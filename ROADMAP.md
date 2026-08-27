# adr-kit roadmap

This document captures the project's direction. It is not a release contract.
It exists to make contribution and prioritisation decisions predictable.

## Status

`adr-kit` remains pre-1.0; the current version is whatever
[the latest release](https://github.com/rvdbreemen/adr-kit/releases/latest)
says, because a number written here goes stale on the next tag. The Claude,
Codex, and standalone Copilot distributions, the native OpenCode package,
17 workflows, local ADR lifecycle, deterministic
enforcement, index-first selective context, human-gated ADR grilling with
deterministic readiness, guardian, MCP server, and generated indexes are all
shipped. File layout and conventions may still change before v1.0.0.

The [2026-07-18 source audit](docs/reviews/2026-07-18-source-audit/FINDINGS.md)
is the current engineering baseline. All implementation findings are closed
or explicitly accepted with a tested compatibility rationale; regression
coverage remains part of the release gate.

If a breaking change becomes necessary before v1.0.0, it will land as a minor
version, be called out in the changelog, and include a tested migration note.

## Toward v1.0.0

`v1.0.0` is the signal that the public layout and core contracts will not
change without a deprecation window. Current release criteria are:

- Close or explicitly accept every P1 finding in the current source audit.
- Test the minimum supported Python version and Windows plus Unix packaging
  contracts in CI.
- Exercise native plugin installation, MCP startup, and one workflow per client
  in release smoke tests.
- Accumulate 90 days of field time without a needed breaking change.
- Reach at least five unrelated installations beyond the maintainer's own.
- Confirm the four verification gates have blocked at least one real-world PR.
- Publish and test the v0.x to v1.0 migration path on a non-trivial ADR set.

**Field check (2026-07-18, v0.34.0):** all dogfood ADRs
pass strict lint; the README, Markdown, and JSON graph indexes are current;
payload sync is newline-stable; and the supported Python/OS matrix covers
manual packaging, prepared installation, MCP startup, lifecycle rollback,
bounded enforcement, and concurrent state updates. The external field-time
and unrelated-installation criteria remain open, so v1.0 criteria are not met.

## Planned work (signals, not commitments)

Priority is shaped by user evidence:

- Accumulate the field evidence required for v1.0 readiness.
- Finish the external ADR tooling catalog contribution and repository
  automation follow-ups already tracked in Backlog.
- Keep migration and compatibility checks current as client plugin APIs evolve.

## Recently landed

- **TASK-52:** schema-v2 `ADR-INDEX.json` became the shared local
  selective-context query engine. CLI, MCP, lifecycle hooks, health probes,
  doctor, status, and guardian now use one explainable retrieval contract;
  metadata enrichment stays dry-run-first and human-approved.
- **TASK-32:** source-audit closure: bounded regex workers, schema-validated
  runtime config, exact Git snapshot semantics, rollback-safe lifecycle and
  release mutations, cross-process state transactions, executable release
  modes, and expanded packaging/documentation CI.
- **TASK-29:** the automatic installer now prepares a persistent
  platform-local marketplace with its validated Python runtime embedded,
  restores Unix entry-point modes, isolates client failures, completes a real
  MCP handshake, and runs its compatibility contract on Windows, macOS, and
  Linux.
- **TASK-26:** MADR is the default for new records; Nygard and the legacy
  canonical profile are selectable through one semantic registry. Profile
  migration is dry-run capable and idempotent, and all native client payloads
  share the same templates and engines.
- **v0.40.0:** index-first selective context: schema-v2 `ADR-INDEX.json` as
  the shared query database, retrieval metadata and Decision Contracts,
  project retrieval probes, and authority-aware lifecycle injection.
- **v0.39.0:** one declarative registry of every version-bearing file plus a
  bump writer, so a release is written rather than hand-edited (ADR-013).
- **v0.38.0:** the enforced three-marketplace release runbook, version
  consistency gate, tag-triggered publish workflow, and `/release-adr-kit`
  (ADR-012).
- **v0.37.0:** ADR Grilling across the lifecycle, the deterministic
  `adr-readiness` contract, the fifth MCP tool, and the active Proposed queue
  (ADR-011).
- **v0.35.0-v0.36.0:** native certification for all three CLI clients through
  one outcome contract and capability registry, plus the generated client
  support matrix (ADR-010).
- **v0.34.0:** selectable MADR/Nygard/canonical formats, versioned JSON ADR
  graph index, three-platform native installer with a real MCP handshake, and
  the closed source-audit hardening set (bounded regex, fail-closed judge
  config, exact staged Git semantics, transactional lifecycle and state).
- **v0.33.0:** separate native Codex and standalone Copilot distributions,
  detected-client installer, generated payload gate, and workspace-aware MCP.
- **v0.32.0:** canonical frontmatter, strict local governance, generated README
  index, lifecycle commands, after-the-fact acceptance, and local doctor.
- **v0.31.0:** layered session/edit/task context injection and compact ADR index.
- **v0.20.0-v0.30.x:** context lookup, watcher, MCP, team-safe numbering,
  guardian team mode and trends, dependency/retirement workflows, CI action,
  pre-commit framework support, migration, and audited overrides.

## Out of scope (deliberate non-goals)

- **Multi-language skill bodies.** Project ADRs can use another language, but
  upstream agent instructions remain English.
- **Rendered ADR visualisation.** Diagrams and interactive graph UIs are out of
  scope. The shipped `adr-related` dependency report remains textual.
- **Bundling unrelated governance plugins.** ADR Kit stays single-purpose.
- **Client-exclusive core behavior.** Client integrations may differ, but core
  workflows must degrade gracefully outside any one vendor.
- **Heavy framework wrapping.** Stdlib Python is the runtime floor; no compiled
  assets, JavaScript runtime, hosted service, or external Python framework.

## How decisions get made

Significant changes to plugin layout, default conventions, enforcement, or
user-visible behavior need an ADR or a PR description with equivalent context,
alternatives, consequences, and evidence. Small fixes and documentation
corrections do not need a new decision record.

See [CONTRIBUTING.md](CONTRIBUTING.md). Project-specific policy belongs in the
consuming project; generic improvements that benefit any user are welcome.
