---
id: TASK-137
title: Three CLI paths measure above ADR-015's ceiling and need a decision each
status: To Do
assignee: []
created_date: '2026-08-05 06:54'
updated_date: '2026-08-05 06:55'
labels:
  - performance
  - adr-015
  - follow-up
dependencies: []
priority: medium
ordinal: 109500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-126 completed the latency corpus and recorded three measured paths that exceed ADR-015's 2000 ms Must Not while doing real work. They were deliberately not budgeted there: absorbing them would have turned corpus completion into an ADR-015 amendment, and each needs its own decision. Measured 2026-08-05 on Windows 11 / CPython 3.12.9, this repository, 327 commits and 29 ADRs: adr-audit --whole-codebase ~10 s; adr-doctor --check ~6.8 s; adr-discover default with the git-history scan on ~2.8 s. The third is the most interesting: git rev-list --count HEAD is 327 against DEFAULT_MAX_COMMITS = 2000 in bin/adr_history_scan.py:35, so the cap never binds and 2820 ms is the honest cost of 327 commits, growing with the repository. The corpus budgets --no-history at the startup floor and says so, which means the path a user actually runs is still unbudgeted. Each path needs one of three outcomes, decided per path: brought under the ceiling (adr-discover could cap or sample the history scan); named by an amending ADR as a deliberately slower path the way ADR-031 named the pull-request moment, noting ADR-031's distinction rests on the event being user-initiated and all three of these are; or declared outside the contract with the reason recorded, if the cost is genuinely unbounded by anything the kit controls. The hook side of the ceiling is already enforced by TASK-129 in tests/test_hook_performance.py and the CLI side has a coverage gate from TASK-126 in tests/test_cli_corpus_coverage.py, so whatever is decided, the gate is there to hold it.<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each of the three paths is under the ceiling, named by an Accepted amending ADR, or recorded as outside the contract with its reason
- [ ] #2 adr-discover's default path carries a budget describing the path a user actually runs, not only --no-history
- [ ] #3 The corpus known_over_ceiling block lists only paths a decision has been taken about
- [ ] #4 A test fails when a measured path exceeds the ceiling with no ADR and no recorded decision
<!-- AC:END -->
