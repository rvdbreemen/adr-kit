# adr-kit roadmap

This document captures the project's direction. It is not a release contract.
It exists to make contribution and prioritisation decisions predictable.

## Status

`adr-kit` is at v0.33.0 and remains pre-1.0. The Claude, Codex, and standalone
Copilot distributions, 14 workflows, local ADR lifecycle, deterministic
enforcement, context injection, guardian, MCP server, and generated indexes are
all shipped. File layout and conventions may still change before v1.0.0.

The [2026-07-18 source audit](docs/reviews/2026-07-18-source-audit/FINDINGS.md)
is the current engineering baseline. Its high-severity enforcement and
portability findings take priority over new surface area.

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

**Field check (2026-07-18, v0.33.0 plus unreleased work):** all five dogfood
ADRs pass strict lint, both generated ADR indexes are current, and 558 tests
are collected. The payload sync gate is newline-stable across CRLF and LF
checkouts. An isolated
performance threshold can still be noisy under concurrent load.
High-severity source findings remain open, so v1.0 criteria are not met.

## Planned work (signals, not commitments)

Priority is shaped by user evidence and the source audit:

- Harden `adr-judge`: isolate regex evaluation, validate runtime config types,
  fail safely on oversized diffs, decode Git-quoted paths, and evaluate
  `require_pattern` against the staged/post-diff snapshot.
- Make lifecycle updates transactional and enforce legal status/supersession
  transitions before either ADR is written.
- Align context ranking and generated validators with their documented
  lifecycle and Enforcement semantics.
- Finish the external ADR tooling catalog contribution and repository
  automation follow-ups already tracked in Backlog.

## Recently landed

- **TASK-29:** the automatic installer now prepares a persistent
  platform-local marketplace with its validated Python runtime embedded,
  restores Unix entry-point modes, isolates client failures, completes a real
  MCP handshake, and runs its compatibility contract on Windows, macOS, and
  Linux.
- **TASK-26:** MADR is the default for new records; Nygard and the legacy
  canonical profile are selectable through one semantic registry. Profile
  migration is dry-run capable and idempotent, and all native client payloads
  share the same templates and engines.
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
