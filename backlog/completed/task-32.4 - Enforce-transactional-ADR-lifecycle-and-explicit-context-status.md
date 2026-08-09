---
id: TASK-32.4
title: Enforce transactional ADR lifecycle and explicit context status
status: Done
assignee:
  - Codex
created_date: '2026-07-18 19:52'
updated_date: '2026-07-18 20:21'
labels:
  - lifecycle
  - context
  - atomicity
  - F-08
  - F-09
dependencies: []
references:
  - docs/reviews/2026-07-18-source-audit/FINDINGS.md
modified_files:
  - bin/adr
  - bin/adr-context
  - tests/test_adr_lifecycle.py
  - tests/test_adr_context.py
parent_task_id: TASK-32
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Resolve source-audit F-08 and F-09 by enforcing legal lifecycle transitions, making reciprocal supersession rollback-safe, and making Proposed versus Accepted context semantics explicit to all consumers.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Illegal lifecycle transitions are rejected through one shared state-machine contract.
- [x] #2 Two-file supersession either completes consistently or restores both original records under injected write failure.
- [x] #3 Context output always exposes lifecycle status and its default binding behavior is documented and tested.
- [x] #4 MADR, Nygard, and canonical lifecycle/context regression tests pass.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Map every lifecycle command and existing profile-specific tests against one legal transition graph.
2. Centralize transition validation and acceptance-gate preflight.
3. Implement same-directory atomic writes and a two-record rollback transaction for supersession, including injected failure tests.
4. Decide and document context default behavior; preserve retrieval breadth while making binding status explicit in every output/client surface.
5. Verify lifecycle and context equivalence for MADR, Nygard, and canonical records.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Closed F-08 and F-09. Lifecycle commands now enforce an explicit transition graph and strict acceptance gates before mutation. All ADR and generated-index writes use same-directory atomic replacement inside a recoverable transaction; injected multi-file and index failures restore byte-identical originals. Supersession rejects self-links, conflicting successors, and incoherent reciprocal state. Context results now expose status plus is_accepted and label Accepted records as binding while all other statuses are explicitly non-binding. Verification: 62 focused lifecycle, auto-accept, context, and selectable-format tests passed.
<!-- SECTION:FINAL_SUMMARY:END -->
