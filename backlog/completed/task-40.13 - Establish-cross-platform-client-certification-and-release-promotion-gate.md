---
id: TASK-40.13
title: Define early certification contract and all-three release gate
status: Done
assignee:
  - Codex
created_date: '2026-07-19 17:53'
updated_date: '2026-07-19 20:25'
labels:
  - ci
  - certification
  - release
dependencies:
  - TASK-40.1
modified_files:
  - schemas/client-certification.schema.json
  - scripts/client_certification.py
  - scripts/build-client-adapters.py
  - tests/certification/simulated-pass.json
  - tests/certification/simulated-fail.json
  - tests/test_client_certification.py
  - tests/test_release_allowlist.py
  - docs/client-support.md
  - .github/workflows/validate.yml
  - .github/workflows/release-candidate.yml
  - README.md
  - CHANGELOG.md
parent_task_id: TASK-40
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Define and implement the evidence schema, validator, simulated pass/fail fixtures, and release-gate algorithm for Claude Code CLI, Codex CLI, and Copilot CLI before native work is certified. The gate fails while any required Windows evidence is missing, stale, or failing; the three certification tasks later supply real evidence. macOS/Linux are best-effort. No future client participates.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A versioned certification schema records client/version/surface/OS, contract date, required outcomes, fixture/native results, cold/warm latency evidence, degradations, update/rollback evidence, candidate commit, and source links.
- [x] #2 The schema, validator, and simulated passing/failing fixtures represent independent Claude, Codex, and Copilot evidence before live certification.
- [x] #3 The release-gate algorithm requires generator/schema/hook/installer/doctor/package fixtures, strict ADR lint/index checks, and the regression suite.
- [x] #4 The gate fails when any required Windows evidence for Claude Code CLI, Codex CLI, or Copilot CLI is missing, stale, tied to another candidate commit, or failing.
- [x] #5 The native-smoke contract covers install/list, workflow discovery/invocation, instructions, required hook outcomes/backstops, MCP initialize/list/call, second-install no-op, verified update, rollback, doctor, and uninstall preservation.
- [x] #6 Login-dependent maintainer-run smoke is allowed only when tied to the release-candidate commit, supported client version, environment fingerprint, and retained redacted evidence.
- [x] #7 macOS/Linux status records attempted result or not-run reason as best-effort and never promotes an untested surface.
- [x] #8 CLI, IDE, cloud, preview, wrapper, and legacy surfaces are separate identities; the three CLI certifications promote no other surface.
- [x] #9 Performance evidence reports benchmark method ID, cold/warm state, p50/p95/max/sample count, and hard-timeout results against approved budgets.
- [x] #10 Generated support documentation derives claims from evidence and lists only Claude Code CLI, Codex CLI, and Copilot CLI as TASK-40 support.
- [x] #11 Rollback/uninstall evidence proves preservation of unrelated config, instruction bytes outside markers, local guide, previous healthy payload, and source checkout.
- [x] #12 Live three-client evidence is enforced only on release-candidate workflows; ordinary pull requests validate schemas, simulated gate behavior, and available fixtures without requiring authenticated native clients.
- [x] #13 No TASK-43 client or generic-support result is part of this schema's required TASK-40 release evidence.
- [x] #14 A release candidate consolidates all defaults, hook policy, schema, and migration changes for the intended stable release; stable publication requires the full three-client gate against that exact candidate commit.
- [x] #15 Release tooling permits at most one non-emergency stable release per calendar day. An override requires an emergency incident/reason, affected versions, rollback proof, changelog entry, and follow-up review evidence.
- [x] #16 A shipped default or hook-policy reversal requires a superseding Proposed ADR and a new release candidate; it cannot be hidden in a same-day patch.
- [x] #17 Certification records entrypoint/module size inventory and executable delta against the measured baseline (27 `bin` entries, 3 `scripts`); over-budget state fails unless an approved exception is linked.
- [x] #18 Certification records runtime/development dependency sets, exact-pin rationales, licenses, security/update ownership, and confirms development-only tools are absent from runtime artifacts.
- [x] #19 Release archive tests build from the allowlist and fail on backlog, `.superpowers`, VCS/CI internals, tests, caches, local state, secrets, or unapproved files.
- [x] #20 Release-candidate evidence includes every deterministic generator's versioned Windows benchmark and fails on a hard-timeout breach, target breach after calibration, unapproved >20% p95 regression, unexpected unchanged-output rewrite, unbounded input-root scan, or missing best-effort macOS/Linux status.
- [x] #21 Certification rejects lowest-common-denominator adapters: each client record proves native manifest layout, native discovery/invocation syntax, client-specific skill metadata and concise prompt behavior, native hook file/event casing and platform command form, and no deprecated prompt surface is advertised as first-class.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Size M. Define the minimal schema, validator, evidence freshness rule, candidate-commit binding, simulated pass/fail records, and generated three-client support mapping immediately after TASK-40.1. Implement a gate that correctly blocks while live client evidence is absent; TASK-40.7.1/.2/.3 later populate it. Do not weaken the gate for planning branches and do not include TASK-43.

Add deterministic-generation performance evidence to the early certification schema and simulated pass/fail fixtures so regression gating exists before generator implementation is promoted.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Maintainer requirement added after TASK-40.2: shared outcomes remain canonical, but Claude, Codex, and Copilot plugin/skill/prompt adapters must be optimized for their native runtime. Current official-doc verification on 2026-07-19 found: Codex plugin components belong at plugin root, hooks should be declared as hooks/hooks.json, skills rely on concise front-loaded descriptions and progressive disclosure, and custom prompts are deprecated/local-only; Claude uses root skills/ and hooks/hooks.json, supports native argument-hint/disable-model-invocation/$ARGUMENTS and namespaced slash invocation; Copilot plugin.json supports skills and a root hooks.json, with lower-camel hook event names and separate bash/powershell commands. The release schema/gate must prove these client-native shapes rather than only semantic parity.

Implementation started after TASK-40.2 completed. The gate will encode native-optimization evidence as well as shared outcomes, using simulated three-client fixtures on ordinary PRs and requiring live Windows evidence only in explicit release-candidate mode.

Adversarial review fixed two publication and scope hazards: support documentation is written only after certification succeeds, and the archive collector walks only declared public roots while filtering caches/secrets/private paths instead of scanning or copying the repository root. Certification functionality was folded into the existing build entrypoint with `client_certification.py` as a support module, avoiding another public direct executable and preserving TASK-40's four-entrypoint budget.

The ordinary validation workflow uses `simulated-task40` evidence and never requires client login. `.github/workflows/release-candidate.yml` runs on Windows, checks out the exact requested commit, runs deterministic generation, strict ADR checks, and the full regression suite, then requires a real commit hash plus three native evidence records. Simulated evidence therefore proves gate behavior but can never promote a release.

Implemented versioned three-client certification schema and stdlib gate in the existing public adapter entrypoint, avoiding an executable-budget increase. Evidence binds exact client/surface/OS, candidate commit, contract date, outcomes, fixtures, native smoke, cold/warm benchmarks, degradations, lifecycle preservation, native optimization, inventory, dependencies, release policy, source links, and retained evidence. Ordinary CI validates independent simulated Claude/Codex/Copilot records and generated support-matrix drift; --release-candidate requires a real commit hash plus native evidence for all three.

The gate blocks missing clients, stale dates, mixed commits, non-Windows/CLI identity, failed fixtures/outcomes/smoke, absent best-effort reasons, latency/timeout/regression/write failures, executable/dependency/archive policy breaches, same-day release violations, un-ADR'd policy reversals, and lowest-common-denominator plugin/skill/prompt/hook shapes. docs/client-support.md explicitly labels current fixture results simulated only and promotes no IDE/cloud/future surface.

Verification: JSON/compile checks passed; simulated PR gate passes; simulated release-candidate gate fails with one real-hash error plus three missing-native errors; focused certification tests 7 passed; adapter drift check clean; git diff --check clean; full suite 689 passed, 4 skipped in 231.47s.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Established the early all-three certification and release-promotion gate. Added the evidence schema, independent pass/fail fixtures, candidate/freshness/native validation, performance and packaging policy checks, native-adapter optimization checks, generated support matrix, and PR CI integration. Simulated evidence can validate behavior but cannot promote a release. Full suite: 689 passed, 4 skipped.
<!-- SECTION:FINAL_SUMMARY:END -->
