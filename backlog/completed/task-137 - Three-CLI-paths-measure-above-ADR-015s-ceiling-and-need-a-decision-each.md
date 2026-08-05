---
id: TASK-137
title: Three CLI paths measure above ADR-015's ceiling and need a decision each
status: Done
assignee: []
created_date: '2026-08-05 06:54'
updated_date: '2026-08-05 08:48'
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
TASK-126 completed the latency corpus and recorded three measured paths that exceed ADR-015's 2000 ms Must Not while doing real work. They were deliberately not budgeted there: absorbing them would have turned corpus completion into an ADR-015 amendment, and each needs its own decision. Measured 2026-08-05 on Windows 11 / CPython 3.12.9, this repository, 327 commits and 29 ADRs: adr-audit --whole-codebase ~10 s; adr-doctor --check ~6.8 s; adr-discover default with the git-history scan on ~2.8 s. The third is the most interesting: git rev-list --count HEAD is 327 against DEFAULT_MAX_COMMITS = 2000 in bin/adr_history_scan.py:35, so the cap never binds and 2820 ms is the honest cost of 327 commits, growing with the repository. The corpus budgets --no-history at the startup floor and says so, which means the path a user actually runs is still unbudgeted. Each path needs one of three outcomes, decided per path: brought under the ceiling (adr-discover could cap or sample the history scan); named by an amending ADR as a deliberately slower path the way ADR-031 named the pull-request moment, noting ADR-031's distinction rests on the event being user-initiated and all three of these are; or declared outside the contract with the reason recorded, if the cost is genuinely unbounded by anything the kit controls. The hook side of the ceiling is already enforced by TASK-129 in tests/test_hook_performance.py and the CLI side has a coverage gate from TASK-126 in tests/test_cli_corpus_coverage.py, so whatever is decided, the gate is there to hold it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Each of the three paths is under the ceiling, named by an Accepted amending ADR, or recorded as outside the contract with its reason
- [x] #2 adr-discover's default path carries a budget describing the path a user actually runs, not only --no-history
- [x] #3 The corpus known_over_ceiling block lists only paths a decision has been taken about
- [x] #4 A test fails when a measured path exceeds the ceiling with no ADR and no recorded decision
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Two of the three paths are a category; the third turned out to be a defect, and telling them apart is the outcome.

AC#2 -- adr-discover is FIXED rather than excepted. scan_first_appearance ran one `git log --follow` per candidate path: 21 paths, 21 git startups, rename detection re-run over the whole history each time. Measured 2762 ms per-path against 123 ms batched into a single `git log --name-only`. The default command drops from 3622 ms to 938 ms, back under the ceiling, and stops growing with the number of candidates. Same 21 arrivals, same ordering. It now carries a real workload budget (1350/1450/2000) describing the path a user actually runs.

The trade is --follow: a file that arrived under a different name reports the rename rather than the original creation. Real and small -- the signal is about the ORDER subsystems appeared, and a rename does not reorder anything.

AC#1 and AC#3 -- ADR-033 (Proposed) names what remains: adr-audit --whole-codebase at ~10 s and adr-doctor --check at ~6.8 s, both whole-repository commands a user invokes directly and waits on. That is the CLI counterpart of the distinction ADR-031 made for the pull-request hook. known_over_ceiling now lists only those two, each referencing the record.

The process point worth keeping: requiring an ADR before an exception is exactly what surfaced the third path as a defect. It had to be argued for, and the argument did not hold. An exception is for a cost that cannot be removed, not for one nobody has looked at yet.

AC#4 -- tests/test_cli_corpus_coverage.py fails on an over-ceiling entry naming no record, or naming one that does not exist. It requires the record to EXIST, not to be Accepted: these are recorded findings rather than declared budgets, the ceiling binds the `budgets` block which a separate test holds at 2000 ms, and demanding a signature before a measurement may be written down would make the honest move the one the gate blocks. A second check reports which exceptions are still Proposed so the state stays visible.

ADR-033 is Proposed and needs maintainer acceptance to become binding. The gate reports that rather than hiding it.

Verified: 27 tests across corpus coverage, discover and CLI performance; 45 across policy, audit and the declared-gate check; adr-lint --gates all exits 0.
<!-- SECTION:FINAL_SUMMARY:END -->
