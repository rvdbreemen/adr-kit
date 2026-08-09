---
id: TASK-44
title: 'Harden TASK-40 against scope, complexity, dependency, release, and model drift'
status: Done
assignee:
  - Codex
created_date: '2026-07-19 19:12'
updated_date: '2026-07-19 19:19'
labels:
  - planning
  - guardrails
  - release
  - dependencies
dependencies: []
documentation:
  - docs/plans/cross-client-plugin-implementation-plan.md
  - docs/reviews/cross-client-plugin-planning-findings.md
  - docs/research/cross-client-plugin-hooks-report.md
modified_files:
  - docs/plans/cross-client-plugin-implementation-plan.md
  - docs/reviews/cross-client-plugin-planning-findings.md
priority: high
ordinal: 44000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Incorporate the transferable lessons from Fable's KennisBank v0.17.1 review into the three-client ADR Kit program without importing KennisBank product behavior. Add measurable guardrails for detected-client defaults, executable/module growth, zero-baseline runtime dependencies, stable release cadence, allowlisted public artifacts, and explicit local-model validation. Update the durable plan and relevant TASK-40 work orders only; do not start implementation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Installer defaults are derived from detected Claude/Codex/Copilot state and settings; no static client set installs an absent client.
- [x] #2 The current 991-line installer baseline is recorded and TASK-40.5 requires decomposition into orchestration entrypoints and single-responsibility modules with enforceable size/exception rules.
- [x] #3 Public executable growth is budgeted and reported; client-specific behavior is data-driven instead of creating one script per client/event.
- [x] #4 ADR Kit preserves its zero-runtime-dependency baseline unless a separate Proposed ADR justifies a dependency; development tools are kept out of runtime installation.
- [x] #5 Exact dependency pins require a documented compatibility reason and update policy; dependency and license reports are release evidence.
- [x] #6 Release candidates consolidate migrations and policy changes before stable publication; same-day stable churn or policy reversal requires an explicitly documented emergency exception.
- [x] #7 Public archives/plugins are built from an explicit allowlist and tests reject internal backlog, agent-workflow, cache, test, and developer-only paths.
- [x] #8 Local-model judgment has no guessed model tag; provider/model selection is explicit or unambiguous, missing models produce actionable degraded status, and judgment never silently no-ops.
- [x] #9 The plan, findings, TASK-40 epic, and relevant subtasks contain the guardrails with objective acceptance evidence and clear ownership.
- [x] #10 Strict ADR lint, ADR index, whitespace, graph, and scope checks pass; no implementation starts.
- [x] #11 The plan and owning TASK-40 work orders make deterministic generation performance release-gated: bounded declared inputs, zero unchanged rewrites, profiled incremental execution, Windows-native clean/warm budgets, regression threshold, hard timeouts, and preserved determinism/atomicity.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Record the measured ADR Kit baseline: 991-line installer, 282-line doctor, 27 bin entrypoints, 3 scripts, and no runtime dependency manifest. 2. Add engineering budgets and exception policy to the durable plan. 3. Harden TASK-40.1 architecture policy; TASK-40.2 generation/packaging and dependency evidence; TASK-40.4 settings/model selection; TASK-40.5 detection and decomposition; TASK-40.6 model health and fast/deep separation; TASK-40.13 release cadence/artifact/dependency gates; and TASK-40 epic completion. 4. Record the Fable feedback disposition in the findings. 5. Audit graph/scope and run ADR/index/whitespace checks. 6. Finalize TASK-44 without starting implementation.

7. Incorporate the maintainer's generator-performance requirement into TASK-40.1, TASK-40.2, TASK-40.13, the epic, and the durable plan; verify the numeric budgets and ownership are consistent.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Measured ADR Kit baseline before setting budgets: `scripts/install-agent-envs.py` 991 physical lines; `bin/adr-doctor` 282; 27 files directly under `bin`; 3 directly under `scripts`; no requirements/pyproject/setup/package runtime dependency manifest found.

Completed the planning-only hardening pass. Updated the durable plan and adversarial findings; hardened TASK-40, TASK-40.1, TASK-40.2, TASK-40.4, TASK-40.5, TASK-40.6, and TASK-40.13. Added maintainer-requested deterministic-generation performance contracts: bounded declared inputs, zero unchanged rewrites, profiling-led incremental execution, Windows clean/full p50/p95 1/2 s with 5 s timeout, warm unchanged p50/p95 150/500 ms with 1 s timeout, and an unapproved >20% p95 regression release block. Verification passed: strict lint for 9 ADRs; ADR index unchanged; whitespace checks; 12-record active TASK-40 inventory; internal acyclic dependency graph; all implementation records remain To Do; active title/modified-path scope scan; and guardrail/performance consistency scan. No implementation code was started.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Hardened the approved three-client ADR Kit plan using the transferable lessons from the Fable KennisBank review without importing KennisBank behavior. Recorded the actual 991-line installer, 282-line doctor, 27-bin/3-script, and zero-runtime-manifest baselines; added enforceable complexity, dependency, release-cadence, artifact-allowlist, and explicit model-health rules; and assigned each gate to the owning TASK-40 work order. Added a release-gated deterministic-generation performance contract with bounded inputs, zero unchanged rewrites, profiling-led incremental execution, Windows clean/warm budgets, hard timeouts, and regression evidence. Strict ADR lint, index, whitespace, dependency-graph, scope, task-status, and consistency checks pass. TASK-40 and every implementation work order remain To Do; no implementation began.
<!-- SECTION:FINAL_SUMMARY:END -->
