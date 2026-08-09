---
id: TASK-45.5
title: Detect deterministic implementation links to Proposed ADRs
status: Done
assignee:
  - Codex
created_date: '2026-07-20 19:51'
updated_date: '2026-07-20 20:47'
labels:
  - feature
  - adr-grilling
  - git
  - readiness
  - performance
milestone: ADR Grilling
dependencies:
  - TASK-45.2
documentation:
  - docs/feature-adr-grilling/02-lifecycle-analysis.md
  - docs/feature-adr-grilling/03-solution-design.md
  - docs/feature-adr-grilling/04-implementation-plan.md
  - docs/feature-adr-grilling/05-validation-plan.md
modified_files:
  - bin/adr_readiness.py
  - bin/adr-readiness
  - tests/test_adr_readiness.py
  - scripts/benchmark-adr-grilling.py
  - docs/feature-adr-grilling/03-solution-design.md
  - docs/feature-adr-grilling/06-benchmark-report.md
parent_task_id: TASK-45
priority: high
ordinal: 45500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement an explicit and explainable detector for whether changed code implements a Proposed ADR. Keep possible undocumented architecture decisions in a separate advisory category so heuristics cannot create a merge-blocking link.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Blocking linkage uses only an explicit ADR ID in controlled PR or commit context, an ADR plus its described implementation surface, a changed verified_in path, or explicit project metadata.
- [x] #2 Every positive link identifies the exact evidence and a stable finding code.
- [x] #3 File names, technology recognition, or architecture-sensitive paths alone can only produce advisory review recommendations.
- [x] #4 Missing or conflicting evidence results in advisory or unknown rather than a blocking link.
- [x] #5 Renames, deletes, monorepo paths, multiple ADRs, Accepted ADRs, and supersession relationships are handled correctly.
- [x] #6 Results are independent of changed-path order and git output order and the detector is fully read-only.
- [x] #7 Positive, negative, accidental-ID, path-fuzz, quoting, and annotation-injection fixtures pass.
- [x] #8 Five hundred changed paths against fifty ADRs have warm p95 no greater than 250 ms and hard duration no greater than one second.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Restrict blocking implementation links to explicit ADR IDs plus implementation surfaces, changed ADR/surface pairs, verified_in paths or explicit metadata. 2. Keep heuristic architecture-sensitive paths advisory only and attach stable evidence codes. 3. Normalize and stably order paths across rename/delete/monorepo/multi-ADR inputs. 4. Add false-positive, injection, permutation and 500-path performance coverage.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Blocking links require an implementation surface plus explicit ADR evidence, a changed ADR, or verified_in match. Evidence codes are stable and returned per link. Architecture-sensitive path heuristics remain ARCHITECTURE_REVIEW_RECOMMENDED advisories. Tests cover explicit/accidental IDs, scope/verified path matching, path fuzz, Proposed/Accepted/Superseded behavior, order normalization and output injection. Thirty warm samples on 500 paths/50 ADRs: p50 119.386 ms, p95 149.240 ms, max 166.125 ms.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented deterministic, explainable Proposed-ADR implementation linkage. Positive evidence is reported with stable codes; blocking is restricted to explicit implementation surfaces and lifecycle status. Heuristic architecture signals are structurally separate and advisory-only. Normalization and ordering are independent of git path order and platform separators, and all logic remains read-only. The 500-path/50-ADR benchmark passed both p95 and hard budgets with substantial headroom.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 All allowed evidence signals and explicit false-positive controls are tested.
- [x] #2 Thirty-sample benchmark evidence and input fixture characteristics are recorded.
- [x] #3 Finding codes, modified files, documentation, and exact validation results are recorded.
<!-- DOD:END -->
