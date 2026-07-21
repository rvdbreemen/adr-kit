---
id: TASK-45.11
title: Manage Proposed ADRs as an active guardian work queue
status: Done
assignee:
  - Codex
created_date: '2026-07-20 19:52'
updated_date: '2026-07-20 21:33'
labels:
  - feature
  - adr-grilling
  - guardian
  - performance
milestone: ADR Grilling
dependencies:
  - TASK-45.4
  - TASK-45.8
documentation:
  - docs/feature-adr-grilling/02-lifecycle-analysis.md
  - docs/feature-adr-grilling/03-solution-design.md
  - docs/feature-adr-grilling/04-implementation-plan.md
  - docs/feature-adr-grilling/05-validation-plan.md
  - docs/hook-performance.md
modified_files:
  - bin/adr_guardian_queue.py
  - bin/adr-guardian
  - hooks/adr_hook_core.py
  - hooks/native/adr-hook.rs
  - hooks/bin/windows-x64/adr-hook.exe
  - skills/guardian/SKILL.md
  - .gitignore
  - tests/test_adr_guardian_queue.py
  - docs/feature-adr-grilling/03-solution-design.md
  - docs/feature-adr-grilling/06-benchmark-report.md
parent_task_id: TASK-45
priority: high
ordinal: 46100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extend guardian so Proposed ADRs form a ranked decision work queue rather than a parking state. Compute readiness outside hot hooks, write an atomic derived cache, and surface at most three concrete grill actions at SessionStart.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Proposed ADRs are ranked by active diff or PR linkage, shipped-but-Proposed, ready-for-confirmation, open human questions, age, and lowest quality in that order.
- [x] #2 Ranking and tie-breaking are stable and every ranking decision is explainable from report data.
- [x] #3 Full readiness calculation runs outside SessionStart and writes only an atomic derived cache.
- [x] #4 SessionStart reads prepared data, displays at most three actions, and includes an exact /adr-kit:grill command for each.
- [x] #5 Missing, stale, partially written, or corrupt cache data is ignored and SessionStart fails open.
- [x] #6 The cache is safe to delete and is never authoritative for lifecycle or acceptance.
- [x] #7 Explicit deferral records a reason and re-evaluation date or condition without pretending the ADR is complete.
- [x] #8 Ranking, cache concurrency, corruption, deletion, staleness, deferral, doctor, and shipped-but-Proposed tests pass.
- [x] #9 SessionStart remains p50 no greater than 50 ms, p95 no greater than 150 ms, and hard no greater than 500 ms over thirty warm certification samples.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Rank Proposed ADRs deterministically from the shared readiness report using linkage, shipped state, confirmation readiness, open questions, age and quality. 2. Add an outside-hook refresh command that atomically writes a disposable, expiring cache. 3. Make SessionStart perform only a bounded cache read and surface at most three exact grill actions, failing open on missing/stale/corrupt data. 4. Test ranking, tie-breaking, cache concurrency/corruption/deletion/staleness/deferral and certify hook latency.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Validation: guardian/hook/doctor slice 76 passed; combined integration slice 285 passed. Cache is schema v1, atomic, disposable, ignored, expires after 24 hours, and ranks at most three actions by linkage, shipped, ready, open questions, age, then quality with stable ties. Thirty warm Windows native SessionStart samples after final signal work: p50 31.412 ms, p95 37.563 ms, max 37.956 ms (budgets 50/150/500 ms). Missing/stale/corrupt data fails open.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Guardian now manages Proposed ADRs as a deterministic, explainable work queue computed outside hooks. SessionStart performs only a bounded cache read, surfaces at most three exact grill commands, and remains well inside its native latency budgets.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 The cache format and invalidation policy are documented and tested.
- [x] #2 Hook benchmark evidence includes p50, p95, maximum, sample count, and baseline comparison.
- [x] #3 Modified files, exact validation commands, and results are recorded.
<!-- DOD:END -->
