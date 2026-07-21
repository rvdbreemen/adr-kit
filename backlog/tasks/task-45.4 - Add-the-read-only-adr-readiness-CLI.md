---
id: TASK-45.4
title: Add the read-only adr-readiness CLI
status: Done
assignee:
  - Codex
created_date: '2026-07-20 19:51'
updated_date: '2026-07-20 20:47'
labels:
  - feature
  - adr-grilling
  - readiness
  - cli
  - performance
milestone: ADR Grilling
dependencies:
  - TASK-45.2
  - TASK-45.3
documentation:
  - docs/feature-adr-grilling/03-solution-design.md
  - docs/feature-adr-grilling/04-implementation-plan.md
  - docs/feature-adr-grilling/05-validation-plan.md
modified_files:
  - bin/adr-readiness
  - bin/adr_readiness.py
  - schemas/adr-readiness.schema.json
  - packaging/executables.json
  - tests/test_adr_readiness.py
  - scripts/benchmark-adr-grilling.py
  - docs/feature-adr-grilling/03-solution-design.md
  - docs/feature-adr-grilling/06-benchmark-report.md
parent_task_id: TASK-45
priority: high
ordinal: 45400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Expose readiness locally for one ADR, all Proposed ADRs, or a git diff. Reuse the shared readiness core in-process and provide stable human, JSON, and GitHub renderers without lifecycle or repository mutation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The CLI supports ADR-NNN, --all-proposed, --diff, and --base/--head input modes plus human, json, and github output formats.
- [x] #2 All modes use the same readiness model and load reusable repository state once per invocation.
- [x] #3 Exit code 0 means analysis completed regardless of readiness findings; exit code 2 identifies invalid input or runtime failure.
- [x] #4 Portable JSON excludes uncontrolled timestamps and machine-specific absolute paths and remains stably ordered.
- [x] #5 GitHub output is safe for Step Summary and workflow annotations.
- [x] #6 Unknown ADRs, empty repositories, detached HEAD, and invalid refs produce controlled, documented outcomes.
- [x] #7 The CLI is fully read-only and leaves repository and git state unchanged.
- [x] #8 Single-ADR warm p95 is no greater than 500 ms; the 50-ADR all-proposed fixture has warm p95 no greater than 1000 ms and hard duration no greater than 2 seconds.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Expose the shared readiness core through mutually validated ADR, all-Proposed, staged-diff and base/head modes. 2. Provide stable human, JSON and GitHub renderers with safe output and exit codes 0/2. 3. Test empty/unknown/invalid-ref/detached/no-mutation behavior. 4. Package for all clients and certify single/all-Proposed latency over thirty warm samples.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
CLI covers single ADR, all Proposed, staged diff, and merge-base range with human/JSON/GitHub formats. Invalid input/runtime exit 2; completed analysis exits 0 even with findings. Tests cover unknown/empty/invalid refs, detached HEAD, safe Markdown and no mutation. Thirty warm samples: single p95 296.880 ms; all-Proposed p95 348.958 ms/max 433.150 ms. Packaging inventory includes bin/adr-readiness.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added the read-only adr-readiness CLI over the shared in-process domain model. It supports all required target modes, stable portable JSON, concise human output and GitHub-safe Markdown, with controlled 0/2 exit behavior. The command is copied into every generated client and declared in executable packaging. Validation includes empty/unknown/invalid-ref/detached/no-mutation paths and performance comparison to adr-status/adr-context; all budgets passed.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Golden output, CLI contract, error, cross-platform path, and no-mutation tests pass.
- [x] #2 Thirty-sample benchmark evidence and comparison to adr-status and adr-context are recorded.
- [x] #3 Command documentation, packaging impact, modified files, and exact validation results are recorded.
<!-- DOD:END -->
