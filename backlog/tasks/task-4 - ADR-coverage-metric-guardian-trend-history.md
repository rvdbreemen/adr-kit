---
id: TASK-4
title: ADR coverage metric + guardian trend history
status: To Do
assignee: []
created_date: '2026-05-31 13:20'
updated_date: '2026-06-12 21:06'
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
- [ ] #1 bin/adr-status reports % of Accepted ADRs carrying an Enforcement block
- [ ] #2 Guardian state file gains an append-only trend log; running the guardian twice records a delta
- [ ] #3 pytest green, adr-lint clean, docs updated, version bump, released (user sign-off)
<!-- AC:END -->
