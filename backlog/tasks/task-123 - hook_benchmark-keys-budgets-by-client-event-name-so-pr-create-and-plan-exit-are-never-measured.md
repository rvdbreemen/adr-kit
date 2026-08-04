---
id: TASK-123
title: >-
  hook_benchmark keys budgets by client event name, so pr-create and plan-exit
  are never measured
status: To Do
assignee: []
created_date: '2026-08-04 05:25'
labels:
  - hooks
  - benchmark
  - coverage
dependencies: []
priority: high
ordinal: 102500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`hooks/hook_benchmark.py` looks up each event's latency budget by the client-facing event name. `pr-create` and `plan-exit` are registered under `pre-tool-use` with a matcher (that is how the v0.44.1 plan-exit fix works), so the lookup finds no budget for them and the benchmark skips both.

The result reads as a pass. Two of the eight declared moments are unmeasured and the report does not say so, which is the failure mode this whole benchmark exists to prevent.

Key the budget by the manifest entry rather than by the dispatched event name, and make an event with no budget a loud failure instead of a silent skip.

Evidence: `hooks/hook_benchmark.py` budget lookup; `hooks/manifest.json` entries for `pr-create` and `plan-exit`, both `pre-tool-use` with a matcher.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every entry in hooks/manifest.json is measured, including the matcher-dispatched ones
- [ ] #2 An event without a resolvable budget fails the benchmark rather than being skipped
- [ ] #3 A test asserts the measured set equals the declared set
<!-- AC:END -->
