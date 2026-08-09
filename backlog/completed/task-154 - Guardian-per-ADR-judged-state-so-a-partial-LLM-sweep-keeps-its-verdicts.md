---
id: TASK-154
title: 'Guardian: per-ADR judged-state so a partial LLM sweep keeps its verdicts'
status: Done
assignee:
  - '@claude'
created_date: '2026-08-09 08:11'
updated_date: '2026-08-09 14:04'
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
- [x] #1 Design decision recorded (ADR) on where per-ADR judge state lives: advisory per-machine, tracked, or both
- [x] #2 An interrupted LLM sweep keeps the verdicts it reached and re-judges only ADRs without a fresh verdict
- [x] #3 A recorded VIOLATION keeps the sweep outcome non-clean until a re-judge clears it
- [x] #4 Per-ADR progress is visible while the sweep runs
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Per-ADR judged-state shipped per ADR-037 (Accepted). llm_tier.adrs in the advisory per-machine .adr-kit-state.json records {last_run, verdict} per ADR; adr-guardian stamp llm --adr ADR-NNN --verdict ok|violation stamps one verdict without touching the tier timestamp or trend, prunes entries for deleted ADR files, and refuses invalid combinations (no verdict, wrong tier) with exit 2 and no state side effect. A recorded violation keeps the llm tier DUE regardless of tier freshness and the nudge names the ids; a re-judge stamping ok clears it (proven end-to-end on a bench repro: fresh tier stamp + violation -> DUE with '1 violation(s) outstanding: ADR-001', re-judge ok -> quiet). Guardian skill step 3b rewritten to a per-ADR loop with resume-awareness (skip fresh ok entries, always re-judge recorded violations, print one line per ADR as its verdict lands); 3c stamps the tier only after a complete sweep. The tracked-state alternative was explicitly rejected in ADR-037 (ADR-025 boundary, spec task-9) and stays a downstream pattern. 6 new tests, guardian suites 45/45, full suite 1754 passed / 12 skipped in 12:52, adapters regenerated --check clean.
<!-- SECTION:FINAL_SUMMARY:END -->
