---
id: TASK-45.9
title: Add adaptive reconstruction grilling to adr-kit init
status: Done
assignee:
  - Codex
created_date: '2026-07-20 19:52'
updated_date: '2026-07-20 21:33'
labels:
  - feature
  - adr-grilling
  - init
  - reconstruction
milestone: ADR Grilling
dependencies:
  - TASK-45.8
documentation:
  - docs/feature-adr-grilling/01-research.md
  - docs/feature-adr-grilling/02-lifecycle-analysis.md
  - docs/feature-adr-grilling/03-solution-design.md
  - docs/feature-adr-grilling/04-implementation-plan.md
  - docs/feature-adr-grilling/05-validation-plan.md
modified_files:
  - skills/init/SKILL.md
  - tests/fixtures/grill/lifecycle-routing.json
  - tests/test_adr_grill_integrations.py
parent_task_id: TASK-45
priority: high
ordinal: 45900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Change adr-kit init so reconstructed architecture candidates begin as Proposed and receive either a compact confirmation grill or a deep grill based on the completeness of directly cited evidence. Keep mixed batches resumable and preserve an explicit work queue for unfinished decisions.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Reconstructed candidates are created as Proposed and cannot be silently accepted by init.
- [x] #2 Compact confirmation is used only when the chosen decision, rationale, alternatives, and consequences have direct cited evidence.
- [x] #3 Missing rationale, alternatives, consequences, ownership, or conflicting evidence selects a deep one-question-at-a-time grill.
- [x] #4 The selected grill depth and supporting evidence are explained to the engineer.
- [x] #5 Each ADR receives its own decision confirmation; one batch confirmation cannot accept multiple candidates.
- [x] #6 Duplicate and conflicting candidates are merged, linked, rejected, or escalated before acceptance.
- [x] #7 An interrupted mixed batch leaves valid Proposed ADRs, a consistent index, explicit Open Questions, and resume commands.
- [x] #8 Full, partial, conflicting, duplicate, mixed-batch, interruption, and resume fixtures pass.
- [x] #9 Deterministic candidate preparation does not regress by more than 20 percent; model interaction latency is excluded from the measurement.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Change reconstruction guidance so every selected candidate is Proposed and independently confirmed. 2. Select compact versus deep grilling only from directly cited decision/rationale/alternatives/consequences evidence. 3. Preserve deduplication, conflict handling, mixed-batch Open Questions and resume commands. 4. Add static/fixture regression coverage and measure deterministic preparation separately from interaction.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Validation: the 285-test lifecycle/integration regression slice passed. `tests/fixtures/grill/lifecycle-routing.json` covers full-evidence compact, partial/conflicting deep, duplicate merge/link, mixed-batch interruption and resume. Init's executable candidate-preparation path was not changed; only workflow guidance and deterministic fixtures changed, so model/human latency is excluded and deterministic preparation has 0% code-path regression.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Init reconstruction now always creates Proposed ADRs, chooses compact versus deep grilling only from directly cited evidence, confirms candidates individually, and leaves mixed or interrupted batches as valid resumable Proposed work.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Init fixtures demonstrate both compact and deep paths plus safe interruption.
- [x] #2 Performance evidence isolates deterministic preparation from human or model wait time.
- [x] #3 User guidance, modified files, exact validation commands, and results are recorded.
<!-- DOD:END -->
