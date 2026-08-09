---
id: TASK-154
title: 'Guardian: per-ADR judged-state so a partial LLM sweep keeps its verdicts'
status: To Do
assignee: []
created_date: '2026-08-09 08:11'
labels:
  - enhancement
  - guardian
  - design
dependencies: []
priority: medium
ordinal: 117500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The guardian llm tier records one last_run for the whole tier. A 68-ADR sweep at 20-28s per isolated call runs ~25 minutes; when it is interrupted or an ADR times out, the tier either stays due (all work lost) or is stamped complete (unjudged ADRs inherit a verdict they never got). Per-ADR last_run+verdict state would let an interrupted sweep keep what it established, re-judge only what is due or timed out, pick up newly added ADRs immediately, and let a recorded VIOLATION keep failing until a re-judge clears it. Design tension to resolve explicitly: .adr-kit-state.json is per-machine advisory by spec (task-9 multi-session safety), while cross-checkout cadence sharing needs a tracked file. Prototype exists downstream in OTGW-firmware otgw-1.x.x scripts/adr-judge-weekly.py (per-ADR stamps, verdict memory, progress-per-ADR reporting, empirical 180s timeout at 6.5x measured max).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Design decision recorded (ADR) on where per-ADR judge state lives: advisory per-machine, tracked, or both
- [ ] #2 An interrupted LLM sweep keeps the verdicts it reached and re-judges only ADRs without a fresh verdict
- [ ] #3 A recorded VIOLATION keeps the sweep outcome non-clean until a re-judge clears it
- [ ] #4 Per-ADR progress is visible while the sweep runs
<!-- AC:END -->
