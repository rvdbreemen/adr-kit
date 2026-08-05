---
id: TASK-126
title: The latency corpus has no entry for bin/adr-discover
status: To Do
assignee: []
created_date: '2026-08-04 05:25'
updated_date: '2026-08-04 23:02'
labels:
  - performance
  - coverage
  - adr-015
dependencies: []
priority: medium
ordinal: 105500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`tests/fixtures/cli/latency-corpus.json` is the ADR-015 fixture that pins CLI latency. `bin/adr-discover` is not in it, so its cost is unmeasured and unbounded.

ADR-015 chose a fixture contract precisely so the measurement survives slow CI runners and future tools. A tool that is absent from the corpus is outside that contract without anyone deciding it should be.

Add the entry, and add a test that fails when a `bin/` entrypoint exists with no corpus row -- otherwise the next tool lands outside the contract the same silent way.

Evidence: `tests/fixtures/cli/latency-corpus.json`; `bin/adr-discover`; ADR-015.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 bin/adr-discover has a corpus entry with a measured budget
- [ ] #2 A test fails when any bin/ entrypoint has no corpus row
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
INVESTIGATION 2026-08-05 — far larger than 'add one row', and the measurement is already done.

SCOPE: the corpus holds three budget keys (adr-lint, adr-retire, adr-context-vector). bin/ holds 26 non-.py entrypoints. tests/test_cli_performance.py:32 asserts presence for only adr-lint and adr-retire, so a tool ships without a row and nothing fails. Note adr-context-vector is a PATH LABEL, not an entrypoint — the gate must handle labels that are not files.

ALL 26 MEASURED (Windows 11, Python 3.12.9, 5 samples + warmup, cwd = repo root). `git status --porcelain` was empty before and after every probe batch, so the invocation table is read-only and re-runnable. --help never does real work: all 25 argparse entrypoints print usage and exit 0, slowest adr-doctor 479 ms and adr-judge 478 ms. Two non-argparse exceptions: bin/bump-version has no --help (no-args form is benign, 130 ms, exit 1) and bin/adr-judge-precommit ignores argv.

FOUR PATHS EXCEED ADR-015's 2000 ms CEILING and are NOT this task's to solve: adr-audit --whole-codebase ~10 s, adr-doctor --check ~6.8 s, adr-discover default ~2.8 s. Absorbing them here would quietly turn a corpus-completion task into an ADR-015 amendment. File them separately.

BLOCKING DECISION FOR AC#1 — which adr-discover path is budgeted? Default (git-history scan on) measures p50 2820 ms, over the ceiling; `--no-history` measures 276 ms. `git rev-list --count HEAD` is 327 against DEFAULT_MAX_COMMITS = 2000 (bin/adr_history_scan.py:35), so the cap never binds and 2820 ms is the honest cost of 327 commits — it grows with the repository. (a) Budget --no-history at 450/600/2000 and note that the history scan is deliberately outside the contract: AC#1 closes today, but the path a user actually runs stays unbudgeted. (b) Budget the default path, which needs an amending ADR raising adr-discover's ceiling.

ORDERING: measure LAST. TASK-127 (+220 ms) and TASK-96 (+113 ms) both move adr-lint's number, and the hook recalibration moves the hook side. Rows measured before those land are stale on arrival.
<!-- SECTION:NOTES:END -->
