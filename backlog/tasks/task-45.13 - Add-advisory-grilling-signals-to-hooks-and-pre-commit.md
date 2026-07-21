---
id: TASK-45.13
title: Add advisory grilling signals to hooks and pre-commit
status: Done
assignee:
  - Codex
created_date: '2026-07-20 19:53'
updated_date: '2026-07-20 21:33'
labels:
  - feature
  - adr-grilling
  - hooks
  - performance
milestone: ADR Grilling
dependencies:
  - TASK-45.5
  - TASK-45.7
documentation:
  - docs/feature-adr-grilling/02-lifecycle-analysis.md
  - docs/feature-adr-grilling/03-solution-design.md
  - docs/feature-adr-grilling/04-implementation-plan.md
  - docs/feature-adr-grilling/05-validation-plan.md
  - docs/hook-performance.md
modified_files:
  - bin/adr-grill-signal
  - bin/adr_grill_signal.py
  - templates/githooks/pre-commit
  - hooks/adr_hook_core.py
  - hooks/native/adr-hook.rs
  - hooks/bin/windows-x64/adr-hook.exe
  - tests/test_adr_grill_signal.py
  - docs/feature-adr-grilling/06-benchmark-report.md
parent_task_id: TASK-45
priority: high
ordinal: 46300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add concise, non-interactive grill advisories to existing hook and pre-commit output. Suggest exact commands for suspected architecture decisions and explicit Proposed links without adding a model call, network dependency, full readiness sweep, or new local blocking behavior.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Hooks and pre-commit never start an interactive grill or invoke a model, network service, or provider credential.
- [x] #2 A suspected undocumented decision produces a short advisory with an exact grill command.
- [x] #3 An explicit Proposed implementation link produces a stronger advisory while existing Accepted ADR judge enforcement remains the only local blocking behavior.
- [x] #4 No full readiness scan or per-ADR subprocess loop is added to a hot hook or pre-commit path.
- [x] #5 Output is deduplicated, bounded, shell-safe, and provides executable PowerShell, Bash, or POSIX syntax as appropriate.
- [x] #6 Failures in the new advisory logic fail open and do not hide existing enforcement output.
- [x] #7 No-signal, suspected-decision, linked-Proposed, Accepted-conflict, quoting, and output-injection fixtures pass.
- [x] #8 Pre-commit remains below its existing five-second warning threshold and every hook retains its current manifest p50, p95, and hard budget over thirty warm samples.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add a bounded index-based signal core for suspected decisions and explicit Proposed links without readiness sweeps, models or network. 2. Surface deduplicated client-native advisories in edit hooks and a single fail-open pre-commit subprocess after Accepted enforcement. 3. Keep all new signals non-blocking, shell/output safe and preserve judge as the only local block. 4. Add no-signal/suspected/linked/Accepted/injection/failure fixtures and rerun 30-sample hook/pre-commit performance checks.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Validation: signal/hook/generation slice 60 passed, 3 skipped; combined integration slice 285 passed. Thirty warm native samples retained all p95/hard budgets: SessionStart 31.412/37.563/37.956 ms, UserPrompt 29.874/35.224/35.269, Subagent 28.948/34.059/42.055, PreTool 29.135/35.690/35.763, PostTool 29.336/35.993/39.393, PreCompact 32.021/42.142/43.432, Stop 22.561/26.624/42.921. The single pre-commit advisory subprocess measured p50 444.398 ms, p95 616.388 ms, max 721.188 ms, below 5 s. Signals use only the generated index, are capped at three, shell/output safe, and fail open.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added bounded, index-only grill advisories to edit hooks and pre-commit. Explicit Proposed links receive a stronger signal; suspected decisions receive an advisory. No model, network, readiness sweep, or new blocking behavior was introduced, and the Accepted judge remains the sole local block.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 All hook benchmark reports include sample count, p50, p95, maximum, and baseline comparison.
- [x] #2 Cross-shell command rendering and fail-open behavior are documented and tested.
- [x] #3 Modified files, exact validation commands, and results are recorded.
<!-- DOD:END -->
