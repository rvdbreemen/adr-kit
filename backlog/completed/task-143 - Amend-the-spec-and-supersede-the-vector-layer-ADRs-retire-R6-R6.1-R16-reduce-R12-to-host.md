---
id: TASK-143
title: >-
  Amend the spec and supersede the vector-layer ADRs: retire R6/R6.1/R16, reduce
  R12 to host
status: Done
assignee: []
created_date: '2026-08-09 10:34'
updated_date: '2026-08-09 11:21'
labels: []
dependencies: []
references:
  - docs/plans/kiss-simplification-plan.md
priority: high
ordinal: 114500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Step 1+2 of docs/plans/kiss-simplification-plan.md. Amend spec.md: retire R6 and R6.1 (vector database, query embedding), retire R16 (runtime detection exists only to serve R6), drop the embeddings clause from R11 (graph stays), reduce R12 to the host backend plus the operator escape hatch (ADR_KIT_LLM_CMD / --llm-cmd). State the named loss: without an agent CLI the LLM pass degrades to declarative-only, the floor ADR-001 defines. Supersede ADR-018 and ADR-020 with one ADR recording the retirement and the evidence (no store in this repo; the shipped rerank receives the already-truncated lexical top-5 so the recall gap R6 names is not closed; 36-record corpus). Amend or supersede ADR-017 to host + escape hatch; ADR-025 stands. Acknowledge reversed work by task id: TASK-79, TASK-85, TASK-87, TASK-94, TASK-107, TASK-109, TASK-135. No code is removed in this task.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 spec.md no longer contains R6, R6.1 or R16; R11 keeps only the graph half; R12 names host + operator escape hatch only, with the declarative-only degradation stated
- [ ] #2 One new ADR supersedes ADR-018 and ADR-020 via python bin/adr relate / supersede tooling, with reciprocal links intact (ADR-028 gate passes)
- [ ] #3 ADR-017 amended or superseded to host + escape hatch; ADR-025 untouched
- [ ] #4 python -m pytest -q passes; adapters regenerated with build-client-adapters.py --check reporting changed=0
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
ADR-036 written (Proposed) and wired: relates to ADR-001/014/025/034; spec.md amended (R6/R6.1/R16 tombstoned, R11 graph-only, R12 host + operator escape hatch, cross-refs in R0/R5/R10/R13/R18/R21 and appendix B5 updated). Correction on the task premise: ADR-018 is already Superseded by ADR-020, so ADR-036 supersedes ADR-017 and ADR-020; the chain stays traceable. Two enabling changes shipped with tests: bin/adr supersede now allows one successor for multiple predecessors (each predecessor still gets exactly one successor), and the index emits an empty Decision Contract for Superseded nodes to stay inside ADR-014's graph budget (margin was 307 bytes, now ~3 KiB). Full suite green: 1872 passed, 15 skipped. Awaiting maintainer acceptance of ADR-036 and the two supersessions.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shipped: ADR-036 written, Accepted (signed by the maintainer in session) and superseding ADR-017 and ADR-020 with reciprocal links; ADR-018 was already superseded by ADR-020 so the chain stays traceable. spec.md amended: R6/R6.1/R16 tombstoned, R11 graph-only, R12 host + operator escape hatch, cross-references updated in R0/R5/R10/R12.1/R13/R18/R21 and appendix B5. Gate adr-host-only-judge-v1 registered as strict-xfail placeholder pending TASK-145. Enabling changes with tests: multi-predecessor supersession in bin/adr; empty Decision Contract for Superseded nodes in the index (budget margin 307 bytes -> ~5.5 KiB). Probe and test fixtures repointed from ADR-020 to ADR-036. Full suite: 1872 passed, 15 skipped, 1 xfailed.
<!-- SECTION:FINAL_SUMMARY:END -->
