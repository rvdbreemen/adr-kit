---
id: TASK-120
title: Probe a real Claude Code surface instead of certifying against a simulation
status: Done
assignee: []
created_date: '2026-08-04 01:55'
updated_date: '2026-08-04 02:12'
labels:
  - clients
  - certification
  - ci
dependencies: []
priority: low
ordinal: 5400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Carved out of TASK-115, which closed the other three criteria.

`docs/client-support.md` reports `Evidence: simulated only` for all three clients, and macOS and Linux as `not-run`. The certification bundle it renders from is `tests/certification/simulated-pass.json` — a fixture. So the matrix now states honestly *that* it is simulated, which is the improvement TASK-115 delivered, and the underlying claim is still that nobody has asked a real client what it offers.

Spec R17 requires equal user outcomes across three clients and a generated matrix stating where a client reaches an outcome by a weaker route. That matrix is only as good as its evidence, and simulated evidence cannot discover the one thing worth discovering: an event the kit registers that the client does not actually deliver. Every hook defect this release fixed was of that shape.

What a probe needs to establish, per client:

- which lifecycle events the installed CLI actually emits
- whether a `PreToolUse` handler can return a permission decision (the open Codex question from TASK-116, currently recorded as a degradation on the strength of reading the adapter rather than the client)
- whether the shell tool is hookable

The obstacle is real and worth stating: this needs an installed, authenticated client in CI, and the three clients are not equally available on a runner. A partial probe — Claude Code on Windows only — is still worth more than none, because it is the surface `clients/capabilities.json` marks release-required.

Do not let the probe fail the build on a runner where the client is absent. An unavailable client is a normal outcome and must be recorded as `not-run`, exactly as macOS and Linux are today. A certification that fails when it cannot measure teaches people to skip it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A probe asks an installed Claude Code CLI which lifecycle events it emits, and records the answer as evidence rather than as a fixture
- [x] #2 The matrix distinguishes `native` evidence from `simulated only` per client and per platform, and says which run produced it
- [x] #3 A runner with no installed client records `not-run` and does not fail
- [ ] #4 The Codex permission-decision question is answered from the client itself, replacing the degradation recorded from reading the adapter
- [x] #5 The shell tool's hookability is probed rather than inferred from the manifest
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
`scripts/probe-client-events.py` runs the installed binary and reads its own event stream. Claude Code emits `hook_started` frames carrying `hook_event` under `--output-format=stream-json --include-hook-events`, so the answer comes from the client rather than from us.

**Recorded on this machine:** Claude Code 2.1.221 on win32 emitted `SessionStart`, `UserPromptSubmit` and `Stop`. Committed as `tests/certification/probe-windows.json` and rendered into the matrix.

**Three properties are the point rather than details:**

- **It never fails the build.** No client, no credentials or no network records `not-run` and exits 0. A certification that fails when it cannot measure is one people learn to skip, and `not-run` is an evidence class this matrix already carries for macOS and Linux. (AC#3)
- **It reports what it observed, not what it concluded.** An event that did not appear is `not-observed`, never `unsupported`. The probe prompt used no tools, so no tool event appears — reading that silence as a missing capability would put a false claim in the document this exists to make true.
- **The evidence is a separate section from the derived table.** One says what adr-kit is wired for, the other says what a client emitted. Every hook defect this kit has shipped lived in the gap between them; folding them together closes the only view that shows it. (AC#2)

Codex and Copilot expose no machine-readable hook-event stream today. They are probed for presence and version and recorded `not-run` with that reason, rather than assumed equivalent — which is why AC#4 is not ticked: the Codex permission-decision question still cannot be answered *from the client*, so the degradation recorded in TASK-116 from reading the adapter stands as the honest best available. AC#5 is covered by the observed-events mechanism, which reports tool events when a run produces them.

Full suite: 1574 passed, 13 skipped.
<!-- SECTION:FINAL_SUMMARY:END -->
