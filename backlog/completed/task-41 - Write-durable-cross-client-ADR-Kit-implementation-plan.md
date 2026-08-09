---
id: TASK-41
title: Write durable cross-client ADR Kit implementation plan
status: Done
assignee: []
created_date: '2026-07-19 17:54'
updated_date: '2026-07-19 18:59'
labels:
  - planning
  - documentation
  - cross-client
dependencies: []
documentation:
  - docs/research/cross-client-plugin-hooks-report.md
  - docs/plans/cross-client-plugin-implementation-plan.md
  - docs/reviews/cross-client-plugin-planning-findings.md
modified_files:
  - docs/research/cross-client-plugin-hooks-report.md
  - docs/plans/cross-client-plugin-implementation-plan.md
  - docs/reviews/cross-client-plugin-planning-findings.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create, adversarially review, and finalize a repository-owned implementation plan derived from TASK-38 and the corrected research report. Capture the maintainer interview as explicit product decisions, rewrite TASK-40 and every retained subtask as an independently actionable work order, archive canceled native-client work, remove dependency deadlocks, and verify that the resulting plan is executable. Scope is ADR Kit only; implementation remains out of scope.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The durable plan records Claude Code CLI, Codex CLI, and Copilot CLI as the only first-class clients, Windows native as the release baseline, and macOS/Linux as best-effort.
- [x] #2 The plan defines the Level-4 generic bundle, OpenCode quarterly/change-triggered discovery testing, Kilo/Kimi untested compatibility, and deferred Kilo VS Code without custom generic runtime adapters.
- [x] #3 Maintainer decisions for settings, pre-commit, update/rollback, breaking migrations, doctor repair, local/cloud judgment, generated/local guidance, detection, opt-outs, and screen batching are explicit.
- [x] #4 The task graph sequences policy and guide/settings before canonical artifacts, installer, doctor framework, hooks, independent native certification, and generic validation.
- [x] #5 TASK-40.7 is a non-deadlocking coordination parent, TASK-40.13 is an early evidence/gate contract, and doctor/hook ownership has no circular completion requirement.
- [x] #6 Every retained TASK-40 work order has bounded scope, detailed testable acceptance criteria, dependencies, implementation plan, earliest useful slice or stop boundary, and accurate labels/modified files where relevant.
- [x] #7 TASK-40.7.1, TASK-40.7.2, and TASK-40.7.3 independently own Claude, Codex, and Copilot normalization/certification and produce release-candidate-bound Windows evidence.
- [x] #8 TASK-40.10, TASK-40.11, TASK-40.12, and TASK-40.14 are archived with explicit cancellation reasons; no deferred native adapter remains in the active graph.
- [x] #9 The adversarial findings document preserves the original critique, records the interview resolution, and records the post-rewrite task audit and fixes.
- [x] #10 Plan and review documents contain only ADR Kit product scope, pass whitespace/lint checks, and agree with the active Backlog graph.
- [x] #11 No ADR Kit implementation work starts as part of TASK-41; TASK-40 and retained implementation tasks remain To Do.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Interview the maintainer to fix client, surface, OS, generic-support, automation, update, doctor, judgment, and release policies. Rewrite the durable plan and findings. Revise the TASK-40 epic and retained work orders, repurpose 40.8/40.9, create independent 40.7.1/.2/.3 certification tasks, and archive 40.10/.11/.12/.14. Run a second adversarial task audit, remove dependency/ownership deadlocks, verify documents and Backlog state, then finalize TASK-41 without starting implementation.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Completed the maintainer interview and rewrote the plan around exactly three first-class native CLI clients plus bounded generic support. Revised TASK-40 and every retained work order, repurposed TASK-40.8/.9, created independent TASK-40.7.1/.2/.3 certification tasks, and archived TASK-40.10/.11/.12/.14 with reasons. A second adversarial audit found and fixed hidden doctor/hook ownership and parent/child dependency deadlocks, early-gate evidence bootstrapping, unsafe/undefined update triggers, missing doctor audit mode, ambiguous best-effort evidence and OpenCode cadence, stale evidence binding, and repurposed-task metadata. Verification: active graph audit reported 14 work orders, no cycles, active dependencies only, and required task sections present; strict ADR lint passed 9/9 with zero findings; ADR index check reported changed=False; git diff --check, trailing-whitespace scan, unrelated-scope scan, and deferred-native-title scan passed. No implementation work was started.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Replaced the broad multi-agent adapter program with an approved, executable ADR Kit plan focused on Claude Code CLI, Codex CLI, and Copilot CLI. Added a defined generic portability bundle, OpenCode generic discovery, and honest untested Kilo/Kimi compatibility. Reworked the Backlog into detailed dependency-ordered work orders, added independent native certification tasks, established an early release-evidence contract, and archived four canceled adapter/prototype tasks. The adversarial review now records both the original findings and the post-rewrite defects/fixes. Repository validation passed: strict ADR lint 9/9, generated ADR indexes current, task graph acyclic, documentation whitespace/scope clean, and no deferred native adapter remains active. Implementation remains unstarted and TASK-40 stays To Do.
<!-- SECTION:FINAL_SUMMARY:END -->
