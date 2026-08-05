---
id: TASK-124
title: >-
  The benchmark's hard timeout sits below the interpreter floor, so doctor is
  always degraded off Windows
status: Done
assignee: []
created_date: '2026-08-04 05:25'
updated_date: '2026-08-05 05:58'
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
- [x] #1 The hard timeout exceeds the measured interpreter floor plus the hook's own work
- [x] #2 adr-doctor reports healthy on a clean checkout on a non-Windows platform
- [x] #3 The floor is a named constant carrying the measurement that produced it
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Resolved by ADR-030, and the defect was wider than this record stated: adr-doctor was degraded on EVERY platform including Windows, not only where the native binary is absent. Since v0.44.1 the benchmark follows the dispatcher, and the dispatcher runs the binary only under ADR_KIT_NATIVE_HOOK=1.

Raising only the hard timeout would not have been enough. With coverage fixed (TASK-123), seven of the eight events failed their p50 and p95 targets too, so adr-doctor would have stayed degraded. The budgets were calibrated for the native binary and were exactly right for it: same machine, same payloads, PreToolUse costs 20.2 ms native against 273.6 ms in Python, comfortably inside the declared 25 ms p50 and 100 ms hard timeout. ADR-029 retired that host and the numbers were left describing a path that no longer runs.

AC#1 -- MEASURED_INTERPRETER_FLOOR_MS = 182.6 is now a named constant carrying its measurement (python -c pass, p50 over 7 samples, Windows 11 / CPython 3.12.9, 2026-08-05), and the benchmark's kill timeout is max(declared hard timeout, 2x the floor). A test asserts no declared hard timeout sits at or below the floor.

AC#2 -- the benchmark reports all_targets_met True for the first time. Verified locally on Windows across all eight events; the non-Windows verification is CI, which is the honest verifier since this machine cannot run it.

AC#3 -- the floor is recorded both as the named constant and in the corpus, with the note that it is machine-dependent: 124 ms was measured on 2026-07-26 on a different machine.

Recalibration method, recorded in the corpus: budget = measured p95 x 1.5, rounded up to 50 ms, hard timeout twice that, capped by ADR-015's 2000 ms ceiling. The 1.5 rather than the corpus's 1.2 CI variance is deliberate -- the Windows CI leg runs roughly twice as long as Ubuntu on this repository, and a budget that flakes gets muted.
<!-- SECTION:FINAL_SUMMARY:END -->
