---
id: TASK-45.8
title: Integrate grilling into ADR authoring and acceptance
status: Done
assignee:
  - Codex
created_date: '2026-07-20 19:52'
updated_date: '2026-07-20 21:33'
labels:
  - feature
  - adr-grilling
  - authoring
  - lifecycle
milestone: ADR Grilling
dependencies:
  - TASK-45.7
documentation:
  - docs/feature-adr-grilling/02-lifecycle-analysis.md
  - docs/feature-adr-grilling/03-solution-design.md
  - docs/feature-adr-grilling/04-implementation-plan.md
  - docs/feature-adr-grilling/05-validation-plan.md
modified_files:
  - skills/adr/SKILL.md
  - bin/adr
  - bin/adr_format.py
  - tests/test_adr_auto_accept.py
  - tests/test_adr_grill_integrations.py
  - README.md
  - CHANGELOG.md
parent_task_id: TASK-45
priority: high
ordinal: 45800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make /adr-kit:adr <subject> the primary guided authoring flow without adding a redundant create command. Qualify the subject, create a Proposed ADR with the existing lifecycle, grill context and trade-offs, show an acceptance packet, and then delegate the explicit transition to adr accept.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 /adr-kit:adr <subject> first determines whether the subject is a consequential and difficult-to-reverse architecture decision.
- [x] #2 A qualifying decision is created as Proposed through the existing bin/adr lifecycle rather than through direct file mutation.
- [x] #3 The grill covers context, decision, alternatives, consequences, evidence, scope, ownership, conflicts, and Open Questions.
- [x] #4 The final acceptance packet summarizes the chosen decision, rationale, alternatives, consequences, evidence, scope, conflicts, and lifecycle effect.
- [x] #5 Acceptance requires an explicit yes in the active session followed by adr accept and all existing gates remain able to refuse the transition.
- [x] #6 Unresolved questions, missing required evidence, lifecycle conflicts, and strict lint failures block acceptance with an actionable next question.
- [x] #7 No separate create new ADR command is added.
- [x] #8 The unspecified after-the-fact mode changes from auto to assist while explicitly configured legacy auto remains supported and documented.
- [x] #9 Configuration without an explicit mode is not rewritten merely because the default changes.
- [x] #10 Create, accept, reject, abort, resume, legacy-auto, atomic-write, reciprocal-link, and index tests pass without hook or context-command regression.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Make the existing adr workflow qualify subjects and create only Proposed records through bin/adr. 2. Integrate the canonical grill, Open Questions and complete acceptance packet before delegating to adr accept. 3. Change implicit after-the-fact mode to assist while preserving explicit legacy auto and non-rewriting configuration behavior. 4. Validate create/accept/reject/abort/resume/auto/transactions/index regressions.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Validation: `python -m pytest tests/test_adr_lifecycle.py tests/test_adr_auto_accept.py tests/test_adr_index.py tests/test_adr_related.py tests/test_adr_retire.py tests/test_adr_grill_workflow.py tests/test_adr_grill_integrations.py tests/test_adr_open_questions.py tests/test_adr_judge.py tests/test_adr_judge_security.py tests/test_adr_judge_precommit.py tests/test_adr_guardian.py tests/test_adr_guardian_state.py tests/test_adr_guardian_artifacts.py tests/test_adr_guardian_queue.py tests/test_adr_grill_signal.py tests/test_hook_protocol.py tests/test_hook_performance.py tests/test_adr_mcp.py tests/test_client_adapter_generation.py tests/test_native_client_packages.py -q` -> 285 passed. Implicit after-the-fact mode is tested as assist/no mutation; explicit legacy auto remains tested. Proposed -> `/adr-kit:grill ADR-NNN` -> acceptance packet -> same-session yes -> `bin/adr accept` is documented in README.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Integrated grilling into the existing ADR authoring lifecycle without adding a create command. Qualifying subjects become Proposed records, unresolved Open Questions block acceptance, and an explicit same-session confirmation plus the existing lifecycle command remains mandatory. Changed implicit shipped-ADR acceptance to assist while preserving explicit legacy auto.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 The default compatibility change and explicit legacy opt-in are covered by tests and upgrade documentation.
- [x] #2 End-to-end authoring evidence includes the exact commands and resulting lifecycle state.
- [x] #3 Modified files, validation results, and final behavior summary are recorded.
<!-- DOD:END -->
