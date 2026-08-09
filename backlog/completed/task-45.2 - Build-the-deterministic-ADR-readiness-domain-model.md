---
id: TASK-45.2
title: Build the deterministic ADR readiness domain model
status: Done
assignee:
  - Codex
created_date: '2026-07-20 19:51'
updated_date: '2026-07-20 20:40'
labels:
  - feature
  - adr-grilling
  - readiness
  - performance
milestone: ADR Grilling
dependencies:
  - TASK-45.1
documentation:
  - docs/feature-adr-grilling/03-solution-design.md
  - docs/feature-adr-grilling/04-implementation-plan.md
  - docs/feature-adr-grilling/05-validation-plan.md
modified_files:
  - bin/adr_readiness.py
  - bin/adr-readiness
  - bin/adr_catalog.py
  - schemas/adr-readiness.schema.json
  - scripts/benchmark-adr-grilling.py
  - tests/test_adr_readiness.py
  - docs/feature-adr-grilling/03-solution-design.md
  - docs/feature-adr-grilling/06-benchmark-report.md
parent_task_id: TASK-45
priority: high
ordinal: 45200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement a shared, stdlib-only, read-only readiness core for CLI, MCP, guardian, and CI. The versioned report covers lifecycle, evidence, quality, open questions, implementation linkage, relationships, mechanical actions, human decisions, readiness classification, and the recommended next command.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The public classifications are not-an-adr, needs-human-input, needs-mechanical-fix, ready-for-confirmation, accepted, rejected, and supersession-required.
- [x] #2 The report schema version and stable finding codes are documented and covered by contract tests.
- [x] #3 The evaluation date is injectable and deterministic tests do not depend on the system clock.
- [x] #4 ADRs, findings, links, and evidence are stably ordered and paths are normalized across supported platforms.
- [x] #5 Missing, malformed, or unknown metadata produces controlled findings instead of an unhandled crash where safe analysis can continue.
- [x] #6 The readiness core does not modify ADRs, indexes, caches, git state, or other repository files.
- [x] #7 The same repository, arguments, and injected date produce byte-identical structured report data.
- [x] #8 Thirty warm samples on the standard 50-ADR fixture produce p95 no greater than 100 ms with at most 20 percent CI variance.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Define the versioned stdlib-only readiness classifications, findings and deterministic report shape. 2. Add tolerant metadata analysis, stable ordering, normalized paths and explicit evaluation-date injection. 3. Cover classifications, corruption, permutation and no-mutation behavior with contract tests. 4. Certify the 50-ADR and 500-path performance fixtures with thirty warm samples and record results.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented schema v1 with all seven public classifications, stable finding codes, tolerant metadata findings, normalized/sorted paths and injected dates. Read-only/permutation/corruption/classification tests pass. Certification on Windows 11 / CPython 3.12.9, 30 warm samples, 50 ADRs: core p50 54.753 ms, p95 67.949 ms, max 75.414 ms (100 ms budget). Full focused regression slice: 140 passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented the shared stdlib-only ADR readiness domain model and public schema v1. Reports now carry deterministic classifications, quality/evidence state, mechanical and human actions, implementation linkage, relationships, advisories, normalized paths, stable finding codes, and an injected evaluation date. Malformed and unknown metadata degrades to controlled findings. Added classification, corruption, permutation, path, clock and no-mutation coverage plus a reusable benchmark harness. Validation: 140 focused tests passed; 30-sample 50-ADR core p95 67.949 ms against the 100 ms budget.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Classification, permutation, corruption, path, and clock tests pass.
- [x] #2 Benchmark environment, fixture size, p50, p95, maximum, and comparison to baseline are recorded.
- [x] #3 Public schema, finding codes, modified files, and validation commands are documented.
<!-- DOD:END -->
