---
id: TASK-150
title: 'Plan-exit hook: name undecided decisions when a plan completes (B1, R3)'
status: To Do
assignee: []
created_date: '2026-08-09 10:35'
labels: []
dependencies: []
references:
  - docs/plans/kiss-simplification-plan.md
priority: high
ordinal: 121500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Step 5 of docs/plans/kiss-simplification-plan.md - the investment the freed budget pays for. Appendix A.4: an unrecorded decision survives by default; four gates catch a violated decision, none catches a missing one. Implement proposal B1: a PreToolUse hook matching ExitPlanMode that runs the deterministic candidate finder (bin/adr-discover machinery) against the plan text and injects what looks undecided. Budgeted like the other pre-hooks: 1s, injection only, no model call, fail-open. Declare the event in hooks/manifest.json with network_allowed: false; cover the clients that expose a plan-exit moment and record the degradation for those that do not (R17), with a track-3 backstop noted. TASK-116 (capability registry for plan-exit) is adjacent - check it before starting.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Leaving plan mode in Claude Code injects named undecided-decision candidates within the 1s budget, without any model call
- [ ] #2 hooks/manifest.json declares the event with network_allowed false and a measured latency entry
- [ ] #3 Clients without a plan-exit event have the degradation recorded per R17
- [ ] #4 python -m pytest -q passes; build-client-adapters.py --check reports changed=0
<!-- AC:END -->
