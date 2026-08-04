---
id: TASK-120
title: Probe a real Claude Code surface instead of certifying against a simulation
status: To Do
assignee: []
created_date: '2026-08-04 01:55'
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
- [ ] #1 A probe asks an installed Claude Code CLI which lifecycle events it emits, and records the answer as evidence rather than as a fixture
- [ ] #2 The matrix distinguishes `native` evidence from `simulated only` per client and per platform, and says which run produced it
- [ ] #3 A runner with no installed client records `not-run` and does not fail
- [ ] #4 The Codex permission-decision question is answered from the client itself, replacing the degradation recorded from reading the adapter
- [ ] #5 The shell tool's hookability is probed rather than inferred from the manifest
<!-- AC:END -->
