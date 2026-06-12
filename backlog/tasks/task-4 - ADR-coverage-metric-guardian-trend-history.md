---
id: TASK-4
title: ADR coverage metric + guardian trend history
status: Done
assignee: []
created_date: '2026-05-31 13:20'
updated_date: '2026-06-12 21:26'
labels: []
dependencies:
  - TASK-1
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Turn the guardian from a snapshot into a KPI with memory. Extend bin/adr-status with Enforcement-coverage percent (and optionally llm_judge percent). Extend the v0.18 guardian state file with an append-only trend log per sweep (date, total ADRs, drift, suggestions, retire candidates, coverage); guardian reports the delta vs previous run. HARD DEPENDENCY on v0.18 guardian.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 bin/adr-status reports % of Accepted ADRs carrying an Enforcement block
- [x] #2 Guardian state file gains an append-only trend log; running the guardian twice records a delta
- [x] #3 pytest green, adr-lint clean, docs updated, version bump, released (user sign-off)
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shipped in v0.29.0. adr-status summary gains coverage_pct + llm_judge_pct (additive, all three formats). adr-guardian stamp appends to append-only trend list (cap 52) with --coverage flag; SessionStart nudge shows delta line vs previous sweep when two or more entries exist. Merged cleanly with task-9 locks and task-15 artifact staleness. 22 new tests.
<!-- SECTION:FINAL_SUMMARY:END -->
