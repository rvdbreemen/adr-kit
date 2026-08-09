---
id: TASK-45.10
title: Integrate grilling into review and judge workflows
status: Done
assignee:
  - Codex
created_date: '2026-07-20 19:52'
updated_date: '2026-07-20 21:33'
labels:
  - feature
  - adr-grilling
  - review
  - judge
milestone: ADR Grilling
dependencies:
  - TASK-45.5
  - TASK-45.8
documentation:
  - docs/feature-adr-grilling/02-lifecycle-analysis.md
  - docs/feature-adr-grilling/03-solution-design.md
  - docs/feature-adr-grilling/04-implementation-plan.md
  - docs/feature-adr-grilling/05-validation-plan.md
modified_files:
  - skills/review/SKILL.md
  - skills/judge/SKILL.md
  - tests/fixtures/grill/lifecycle-routing.json
  - tests/test_adr_grill_integrations.py
parent_task_id: TASK-45
priority: high
ordinal: 46000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extend review and judge workflows to distinguish ordinary code findings, conflicts with Accepted ADRs, suspected undocumented architecture decisions, and implementation linked to a Proposed ADR. Route only decision work to a grill while preserving deterministic Accepted ADR enforcement.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Review classifies ordinary code findings, Accepted ADR conflicts, suspected undocumented decisions, and linked Proposed ADRs as distinct outcomes.
- [x] #2 Ordinary code findings do not start an ADR grill and Accepted ADR conflicts retain existing deterministic enforcement.
- [x] #3 Suspected decisions receive an advisory with evidence and a precise /adr-kit:grill command.
- [x] #4 A linked Proposed ADR is updated rather than duplicated.
- [x] #5 Candidate ADR content cites exact source evidence and keeps inferred rationale explicitly marked.
- [x] #6 Neither review nor judge accepts an ADR without the authoring acceptance packet and same-session explicit confirmation.
- [x] #7 Pull request bodies, titles, commit messages, diffs, and source files cannot override the workflow or execute embedded instructions.
- [x] #8 Large diffs, missing base refs, conflicting ADRs, duplicates, and all four outcome categories have deterministic fixtures.
- [x] #9 Existing judge, staged-diff, branch-review, and enforcement regression suites pass.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Define four distinct review/judge routing outcomes while leaving Accepted enforcement unchanged. 2. Route only suspected or linked decision work to exact client-native grill commands and update existing Proposed records. 3. Fence PR/diff/commit/source content as untrusted evidence. 4. Add routing/injection/large-diff/missing-ref fixtures and run existing judge/review regressions.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Validation: the 285-test regression slice passed, including judge, staged/pre-commit, security, lifecycle and routing tests. The fixture asserts ordinary-code, Accepted-conflict, suspected-decision and linked-Proposed as separate outcomes. Review/judge retain Accepted ADR enforcement, fence PR/diff/intent as untrusted evidence, update linked Proposed records, and never accept.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Review and judge now distinguish four outcomes and route only genuine decision work to exact grill commands. Accepted ADR enforcement is unchanged, existing Proposed ADRs are updated rather than duplicated, and untrusted PR material cannot authorize workflow or lifecycle changes.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 PR fixtures and prompt-injection controls cover every routing category.
- [x] #2 Existing Accepted ADR enforcement results are unchanged unless explicitly specified by the architecture ADR.
- [x] #3 Modified files, documentation, exact validation commands, and results are recorded.
<!-- DOD:END -->
