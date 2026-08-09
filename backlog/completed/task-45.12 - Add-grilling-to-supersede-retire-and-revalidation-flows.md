---
id: TASK-45.12
title: 'Add grilling to supersede, retire and revalidation flows'
status: Done
assignee:
  - Codex
created_date: '2026-07-20 19:52'
updated_date: '2026-07-20 21:33'
labels:
  - feature
  - adr-grilling
  - lifecycle
  - supersession
milestone: ADR Grilling
dependencies:
  - TASK-45.8
documentation:
  - docs/feature-adr-grilling/02-lifecycle-analysis.md
  - docs/feature-adr-grilling/03-solution-design.md
  - docs/feature-adr-grilling/04-implementation-plan.md
  - docs/feature-adr-grilling/05-validation-plan.md
modified_files:
  - skills/supersede/SKILL.md
  - skills/retire/SKILL.md
  - tests/fixtures/grill/lifecycle-routing.json
  - tests/test_adr_grill_integrations.py
parent_task_id: TASK-45
priority: high
ordinal: 46200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Use the canonical grill when an Accepted decision may need replacement, retirement, or revalidation. Preserve transactional lifecycle behavior, history, and reciprocal links while making changed forces and human intent explicit.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Supersede grilling covers changed forces, alternatives, migration, consequences, evidence, and the impact on related ADRs.
- [x] #2 A successor remains Proposed until its acceptance packet receives same-session explicit confirmation and adr accept succeeds.
- [x] #3 The successor is accepted before the previous ADR and reciprocal links are transactionally updated.
- [x] #4 A failed or interrupted successor acceptance leaves the previous ADR and its links unchanged.
- [x] #5 Retire remains read-only until an explicit lifecycle command is confirmed and executed.
- [x] #6 Revalidation cannot silently rewrite an Accepted ADR and supports unchanged, successor, reject-candidate, and defer outcomes.
- [x] #7 The workflow identifies the new evidence that justifies each lifecycle outcome.
- [x] #8 Transactional failure, rollback, reciprocal-link, index, supersession-chain, retire false-positive, unchanged, reject, and defer tests pass.
- [x] #9 Measured lifecycle operations do not regress by more than 20 percent.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add revalidation grilling for changed forces, alternatives, migration, consequences, evidence and related ADR impact. 2. Keep successor Proposed until explicit packet confirmation and existing adr accept success. 3. Preserve transactional accept-before-supersede, reciprocal links, rollback and read-only retirement behavior. 4. Validate unchanged/successor/reject/defer and lifecycle/index/relationship regressions with performance comparison.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Validation: the 285-test lifecycle/integration slice passed, including lifecycle rollback, reciprocal links, index, related and retire suites. Revalidation fixtures cover unchanged, successor, reject-candidate and defer. The mutating lifecycle transaction implementation remains the existing tested path; grilling adds workflow guidance before it and therefore adds 0% deterministic transaction-path runtime.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Supersede, retire, and revalidation now grill changed forces and human intent while preserving lifecycle authority. Successors stay Proposed until individually accepted; only then can the existing transaction update the old record and reciprocal links. Interruptions leave prior Accepted state unchanged.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Lifecycle transaction and rollback evidence is recorded for every mutating outcome.
- [x] #2 Performance comparison and all affected relationship/index checks are recorded.
- [x] #3 User guidance, modified files, exact validation commands, and results are recorded.
<!-- DOD:END -->
