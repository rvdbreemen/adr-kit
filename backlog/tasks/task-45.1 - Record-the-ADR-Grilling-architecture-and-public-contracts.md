---
id: TASK-45.1
title: Record the ADR Grilling architecture and public contracts
status: Done
assignee: []
created_date: '2026-07-20 19:50'
updated_date: '2026-07-20 20:11'
labels:
  - feature
  - adr-grilling
  - architecture
milestone: ADR Grilling
dependencies: []
references:
  - >-
    backlog/tasks/task-20 -
    adr-kit-WS4-lifecycle-commands-propose-accept-supersede-reject-mutatereciprocatereindex.md
documentation:
  - docs/feature-adr-grilling/01-research.md
  - docs/feature-adr-grilling/02-lifecycle-analysis.md
  - docs/feature-adr-grilling/03-solution-design.md
  - docs/feature-adr-grilling/04-implementation-plan.md
modified_files:
  - >-
    docs/adr/ADR-011-adopt-deterministic-readiness-and-human-gated-grilling-across-the-adr-lifecycle.md
  - docs/adr/README.md
  - docs/adr/ADR-INDEX.md
  - docs/adr/ADR-INDEX.json
  - docs/feature-adr-grilling/01-research.md
  - docs/feature-adr-grilling/02-lifecycle-analysis.md
  - docs/feature-adr-grilling/03-solution-design.md
  - docs/feature-adr-grilling/04-implementation-plan.md
parent_task_id: TASK-45
priority: high
ordinal: 45100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create and human-accept an ADR that defines the boundaries between deterministic readiness analysis, interactive grilling, lifecycle mutations, hooks, MCP, and CI. Record the evidence classes, public commands, readiness classifications, explicit confirmation rule, failure behavior, compatibility policy, and performance limits before implementation begins.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The ADR records context, decision, alternatives, consequences, failure modes, and the rejected option of agent-driven automatic acceptance.
- [x] #2 Observed, human-stated, inferred, and unknown are defined as separate evidence classes.
- [x] #3 Only existing lifecycle commands are authorized to mutate ADR lifecycle state.
- [x] #4 CI blocking is restricted to an explicitly linked and implemented Proposed ADR, while suspected undocumented decisions remain advisory.
- [x] #5 Hooks and deterministic CI are prohibited from requiring a model or secret.
- [x] #6 The public authoring, grill, readiness CLI, and MCP interfaces plus performance budgets are recorded.
- [x] #7 The accepted ADR has no unresolved open questions and does not conflict with the lifecycle foundation delivered by TASK-20.
- [x] #8 Strict ADR lint, quality, related-link, and index checks pass.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Architecture and public-contract work started on branch dev. The current relevant ADR set, available profiles, source design dossier, and existing lifecycle/client/performance contracts will be checked before the new ADR is accepted.

Validation: `python bin/adr-lint --strict docs/adr/ADR-011-adopt-deterministic-readiness-and-human-gated-grilling-across-the-adr-lifecycle.md` passed with zero advisories; `python bin/adr-quality ... --format json` returned grade A and all four gate scores 1.0; `python bin/adr-index --check docs/adr` reported 11 ADRs, zero duplicates, no drift; `python bin/adr-related ADR-011 --adr-dir docs/adr` resolved ADR-001/004/005/009/010; focused lifecycle/index/lint/quality/related regression slice passed 78 tests in 17.21s.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Accepted ADR-011 as the human-approved architectural contract for deterministic readiness plus human-gated ADR grilling. The record defines evidence classes, lifecycle authority, public surfaces, automation boundaries, compatibility policy, performance budgets, alternatives, consequences, and verification, with no unresolved questions or conflicts.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 The exact review and validation commands and results are recorded in task notes.
- [x] #2 The ADR and affected architecture documentation are included in modified files and the final summary.
- [x] #3 No feature implementation beyond the accepted architectural contract is included.
<!-- DOD:END -->
