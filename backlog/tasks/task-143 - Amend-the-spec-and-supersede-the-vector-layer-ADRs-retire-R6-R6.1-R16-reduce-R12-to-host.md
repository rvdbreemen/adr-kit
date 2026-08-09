---
id: TASK-143
title: >-
  Amend the spec and supersede the vector-layer ADRs: retire R6/R6.1/R16, reduce
  R12 to host
status: To Do
assignee: []
created_date: '2026-08-09 10:34'
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
