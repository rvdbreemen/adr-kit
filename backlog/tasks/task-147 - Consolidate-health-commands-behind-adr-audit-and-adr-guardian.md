---
id: TASK-147
title: Consolidate health commands behind adr-audit and adr-guardian
status: Done
assignee: []
created_date: '2026-08-09 10:34'
updated_date: '2026-08-09 12:46'
labels: []
dependencies: []
references:
  - docs/plans/kiss-simplification-plan.md
priority: medium
ordinal: 118500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Step 4 of docs/plans/kiss-simplification-plan.md. Independent of the removal tasks. R15 asks for one demandable command that lints and judges; R20 for the unprompted track. Keep bin/adr-audit and bin/adr-guardian as the two user-facing entry points; fold adr-status, adr-quality, adr-readiness and adr-doctor into library modules or subcommands behind them. Capability is preserved; only user surface shrinks. Mind ADR-010 line limits (entrypoints 300, support modules 400 - split along docstring seams and update tests/test_release_allowlist.py) and the exit-code contract of R15 (record-quality failure vs code-violation failure stay distinguishable).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The documented user surface names adr-audit and adr-guardian; status/quality/readiness/doctor reachable as subcommands or removed from docs, with skills updated across all three clients
- [ ] #2 R15 exit behaviour still distinguishes bad records from violating code
- [ ] #3 python -m pytest -q passes; build-client-adapters.py --check reports changed=0
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
adr-audit gained health subcommands (status, quality, readiness, doctor) dispatching to the sibling implementations via subprocess so each keeps its own argument surface and exit-code contract; R15's own exit codes (0/1/3/4/2) untouched. README's user surface now names adr-audit <sub> for the four; adr-audit and adr-guardian are the two entry points a person needs. The siblings stay on disk as support modules because the guardian, the lifecycle gates and the skills spawn them directly - capability preserved, surface shrunk. Dispatch test added. Full suite: 1744 passed, 14 skipped; adapters changed=0.
<!-- SECTION:FINAL_SUMMARY:END -->
