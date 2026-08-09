---
id: TASK-153
title: >-
  Make the upgrade skill finish the judge setup: backend, cost picture, and a
  cadence choice
status: Done
assignee:
  - '@claude'
created_date: '2026-08-09 08:11'
updated_date: '2026-08-09 08:28'
labels:
  - enhancement
  - upgrade
  - skill
dependencies: []
priority: high
ordinal: 116500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The v0.47.0 upgrade path enables llm_judge en masse (step 4b) but leaves the judge unable to actually run it as intended. Observed 2026-08-09 upgrading OTGW-firmware otgw-1.x.x from footprint v0.13.0: (1) the retired judge.llm_model stayed in .adr-kit.json and the LLM pass degraded silently until --set-backend was run by hand; (2) the migration reported 0 unbounded among the 6 newly enabled ADRs while the set ended at 68 judged / 64 unscoped, which at a measured 20-28s per isolated call (TASK-63 one-call-per-ADR) is ~25 minutes of blocking per commit; (3) nothing offered the alternative that fits that cost shape, the guardian llm tier with llm_stale_days. The upgrade must end with a judge that works as configured: run the backend step (or confirm one is set), show the set-wide per-commit cost derived from the unscoped count, and when that cost is prohibitive offer judge.llm_enabled=false plus guardian llm_stale_days as the documented cadence, so the next release works as intended out of the box.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Upgrade flow checks judge config for a usable backend and retired keys, and walks --set-backend when needed
- [x] #2 After step 4b the skill prints the set-wide totals (judged, unscoped) and the derived per-commit cost estimate
- [x] #3 When the unscoped count makes commit-time judging prohibitive the skill offers llm_enabled=false with guardian llm_stale_days, and records the choice
- [x] #4 Adapters regenerated with build-client-adapters.py --check clean
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The upgrade skill now finishes the judge setup instead of stopping at enabling flags. Step 4b leads with the new summary totals (judged_after/unbounded_after) and corrects the cost-shape sentence: one call per touched scope PLUS one per unscoped ADR on every commit; 'outside every scope makes none' only holds at unbounded_after=0. New step 4b-squared makes the pass runnable and places the cost: read effective config via adr-judge --show-config, walk --set-backend when the backend is missing or retired keys linger (set-backend removes them), then put unbounded_after x ~20s in front of the user and offer either per-commit judging (small unscoped count) or judge.llm_enabled=false with the guardian llm tier (guardian.llm_stale_days, cost-gated by llm_autorun=false). Wrap-up template gains a judge line recording backend, totals and cadence so .adr-kit.json reads as a decision. Grounded in the OTGW-firmware 0.13->0.47 upgrade where the delta-only report hid 58 already-enabled unscoped ADRs. Adapters regenerated, --check clean; full suite 1875 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
