---
id: TASK-124
title: >-
  The benchmark's hard timeout sits below the interpreter floor, so doctor is
  always degraded off Windows
status: To Do
assignee: []
created_date: '2026-08-04 05:25'
labels:
  - hooks
  - benchmark
  - doctor
dependencies: []
priority: high
ordinal: 103500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`hooks/hook_benchmark.py` enforces a hard timeout roughly 100 ms below the measured CPython start floor of ~124 ms. On any platform without the native binary, the hook cannot finish inside a bound that a bare `python -c pass` already exceeds, so `bin/adr-doctor` reports degraded on every run.

A health check that is always red is a health check nobody reads. The signal is gone precisely when something real breaks.

Set the bound above the interpreter floor plus the work the hook actually does, and record the floor as a measured constant with the measurement next to it, so the next person adjusting it knows what it is made of.

Evidence: the timeout constant in `hooks/hook_benchmark.py`; measured `python -c pass` start cost ~124 ms; `bin/adr-doctor` degraded output on Linux and macOS.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The hard timeout exceeds the measured interpreter floor plus the hook's own work
- [ ] #2 adr-doctor reports healthy on a clean checkout on a non-Windows platform
- [ ] #3 The floor is a named constant carrying the measurement that produced it
<!-- AC:END -->
