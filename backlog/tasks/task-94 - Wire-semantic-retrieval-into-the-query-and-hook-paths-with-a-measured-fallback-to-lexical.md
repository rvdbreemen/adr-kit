---
id: TASK-94
title: >-
  Wire semantic retrieval into the query and hook paths, with a measured
  fallback to lexical
status: To Do
assignee: []
created_date: '2026-08-03 19:31'
labels:
  - retrieval
  - hooks
dependencies:
  - TASK-92
  - TASK-93
priority: high
ordinal: 1200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implementation half of the A1 decision. The vector layer exists and nothing shipped reaches it: `query_adr_context` and `hooks/adr_hook_core.py` rank lexically, so the store is a diagnostic rather than a feature. Under the spec's own reading (R6.1, "How to read this document"), a mechanism no shipped path reaches does not count as implemented.

Route chosen by the maintainer: embed the query at the moment it is asked, in a query step and in a hook. The corpus stays a build step — re-embedding 18 ADRs on every prompt would be model work on text that has not changed.

Three properties keep it inside the contract, and each needs a test rather than a promise:

1. **Budget.** R21's ceiling, with the backend's own timeout well under it. Measured, not asserted. The manifest budgets are 500 ms for `session-start` and `user-prompt-submit` and 100 ms for the pre/post-tool events — an embedding round trip does not fit the 100 ms events, so those keep reading the index only.
2. **Fail-soft.** An unreachable, slow or erroring backend falls back to lexical ranking and the output names which route answered. It never fails the hook and never blocks the prompt.
3. **Default backend.** The local runtime of R16, so the common case stays offline and key-free. A remote endpoint is the user's choice, made in the settings surface after being told the latency and privacy consequence.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `query_adr_context` embeds the query and ranks by vector similarity when the store is present and the backend answers
- [ ] #2 The hook path reaches the same engine on the 500 ms events; the 100 ms pre/post-tool events keep the index-only route
- [ ] #3 An unreachable backend, a timeout and a malformed response each fall back to lexical ranking, exit 0, and label the route in the output — one test per failure mode
- [ ] #4 A latency test measures the query-embedding path against R21 and fails when it exceeds the budget, using the fixture contract of ADR-015 rather than wall-clock on a live model
- [ ] #5 The retrieval route (`vector` or `lexical`) is visible to the user in the injected block, so a silent degradation is impossible
<!-- AC:END -->
