---
id: TASK-45.3
title: Add semantic Open Questions support to ADR profiles
status: Done
assignee:
  - Codex
created_date: '2026-07-20 19:51'
updated_date: '2026-07-20 20:40'
labels:
  - feature
  - adr-grilling
  - adr-profiles
  - lint
milestone: ADR Grilling
dependencies:
  - TASK-45.1
documentation:
  - docs/feature-adr-grilling/02-lifecycle-analysis.md
  - docs/feature-adr-grilling/03-solution-design.md
  - docs/feature-adr-grilling/04-implementation-plan.md
  - docs/feature-adr-grilling/05-validation-plan.md
modified_files:
  - bin/adr_format.py
  - bin/adr_catalog.py
  - bin/adr-lint
  - bin/adr
  - templates/adr-template.madr.md
  - templates/adr-template.nygard.md
  - templates/adr-template.canonical.md
  - templates/adr-template.md
  - tests/test_adr_open_questions.py
  - docs/feature-adr-grilling/03-solution-design.md
parent_task_id: TASK-45
priority: high
ordinal: 45300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add Open Questions as an optional semantic ADR section for Proposed decision work. Keep existing records backwards-compatible, make unresolved Proposed questions visible to readiness, and prevent acceptance while a required human question remains unresolved.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 MADR, Nygard, and legacy profiles recognize the Open Questions semantic role through their supported headings or aliases.
- [x] #2 Existing ADRs without an Open Questions section remain valid and are not rewritten automatically.
- [x] #3 A Proposed ADR with unresolved questions remains valid but is not classified as ready for acceptance.
- [x] #4 Strict lint and adr accept reject a candidate that still has unresolved Open Questions with an actionable message.
- [x] #5 Empty, checked, or explicitly answered questions do not block acceptance.
- [x] #6 Migration remains read-only unless an explicit write operation is requested and does not add the section merely for normalization.
- [x] #7 Templates and authoring documentation explain the section and its lifecycle semantics.
- [x] #8 Profile, lifecycle, migration, and existing lint regression suites pass.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add an optional Open Questions semantic role to MADR, Nygard and canonical profiles. 2. Parse unresolved, checked, answered, empty and absent states without rewriting existing ADRs. 3. Make Proposed questions advisory/readiness-blocking and Accepted questions strict/acceptance-blocking. 4. Update templates, generated clients and profile/lifecycle/migration regression coverage.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added optional Open Questions semantics to every supported profile. Proposed unresolved questions remain lint advisories and readiness-blocking; strict lint and adr accept reject unresolved questions for Accepted transitions. Absent, empty, None, checked, Answered and Resolved states are non-blocking. Existing migration behavior remains explicit-write-only and the corpus is not rewritten. Profile/lifecycle/migration regression slice is included in the 140 passing tests.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added backwards-compatible Open Questions support across MADR, Nygard and canonical ADRs. The parser distinguishes unresolved checklist/bullet questions from empty, checked and explicitly answered states. Proposed ADRs remain valid but cannot become ready while human decisions are open; strict lint and the lifecycle command prevent acceptance without mutating the record. Templates and design documentation describe the lifecycle semantics, and generated client copies are reproducible. Validation: the full profile matrix plus lifecycle, template, migration, index and lint regressions passed in a 140-test slice.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 The profile matrix covers absent, empty, unresolved, checked, and answered questions.
- [x] #2 Backwards compatibility is demonstrated against the existing ADR corpus.
- [x] #3 Modified templates, documentation, validation commands, and results are recorded.
<!-- DOD:END -->
