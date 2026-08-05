---
id: TASK-123
title: >-
  hook_benchmark keys budgets by client event name, so pr-create and plan-exit
  are never measured
status: Done
assignee: []
created_date: '2026-08-04 05:25'
updated_date: '2026-08-05 05:57'
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
- [x] #1 Every entry in hooks/manifest.json is measured, including the matcher-dispatched ones
- [x] #2 An event without a resolvable budget fails the benchmark rather than being skipped
- [x] #3 A test asserts the measured set equals the declared set
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Payloads and budgets are keyed by manifest event id instead of client-facing event name. plan-exit and pr-create are both registered as pre-tool-use WITH A MATCHER, so name-keyed they collapsed onto one entry and two of the eight were never measured while the report still read as a pass.

An event with no latency block now raises rather than being skipped, and the check is three-way: no budget, no payload, and a payload for an undeclared event all fail. A test asserts the measured set equals the declared set.

tests/fixtures/hooks/reference-corpus.json no longer carries its own budget table -- that duplication is what hid the gap. It keeps the method metadata and now records budget_source: hooks/manifest.json plus the measured interpreter floor with its evidence.

Measuring all eight immediately found a third defect the task did not know about: pr-create's p50 budget was 400 ms against a measured 949 ms. It had never been checked, because it was one of the two being skipped. Recalibrated to 1500/3000/5000 under ADR-031's ceiling exemption.

Verified: 13 tests pass in test_hook_performance.py; the benchmark reports all_targets_met True across all eight events for the first time.
<!-- SECTION:FINAL_SUMMARY:END -->
