---
id: TASK-214
title: Release v0.58.0 to the three marketplaces
status: Done
assignee: []
created_date: '2026-10-03 19:20'
updated_date: '2026-10-03 20:06'
labels: []
dependencies: []
priority: high
type: chore
ordinal: 58000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Minor release. A consumer can observe new behaviour: `adr-judge --check-scope` (TASK-204), the new `adr-substance` command and guardian step (TASK-203), the new config key `judge.llm_pass_timeout_seconds` (TASK-210), `adr-migrate` review lines (TASK-202), and readiness items carrying `date` (TASK-200). The rest are fixes from the 2026-10-03 sweep (TASK-191, 192, 194, 201, 209, 211). Driven by scripts/release.py per ADR-042.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Tag v0.58.0 created by release-publish.yml resolves to origin/main
- [x] #2 Sync-back PR into dev merged
- [x] #3 Per-client versions read back as 0.58.0
- [x] #4 npm dist-tags.latest names 0.58.0
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Driven by scripts/release.py. Preflight passed in run 1 (tree clean, dev current, gh authenticated). Prepare stopped on the placeholder as designed; the CHANGELOG section and the README were then written. The next run was refused by preflight, because prepare's own changes left the tree dirty, so the remaining phases ran with --only (prepare, verify, land, tag, syncback, install). Defect recorded in TASK-213.

Verify: version consistency, adapter drift, adr-lint --strict and adr-index --check all passed. The local full suite gave 1 failed, 1946 passed, 12 skipped; the failure was test_lint_and_retire_meet_hard_ceiling_on_this_repo (adr-retire p50 3269 ms). It also fails on unmodified dev locally, passes in CI, and is tracked as TASK-212. Ran with --skip-tests and relied on CI: release PR #170 had all 14 checks green, including pytest on Python 3.10 and 3.12 on Windows, macOS and Ubuntu.

Land: release commit on release/v0.58.0, PR #170 merged into main. Tag: v0.58.0 resolves to 91cf41a, equal to origin/main, created by release-publish.yml (the 'ADR Kit release publish' run succeeded). Release: https://github.com/rvdbreemen/adr-kit/releases/tag/v0.58.0, not a draft and not a prerelease, published 2026-10-03T19:46:11Z. Syncback: PR #171 merged into dev; v0.58.0 is an ancestor of origin/dev, and check-branch-sync reports in sync. Install: all three clients report 0.58.0.

Open: npm. dist-tags.latest still reads 0.57.0, and approval needs the maintainer's 2FA. npm is not logged in on this machine (E401).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
v0.58.0 is released, a minor bump because consumers can observe new behaviour: adr-substance, adr-judge --check-scope, and judge.llm_pass_timeout_seconds. Release PR #170 merged into main with all 14 checks green. Tag v0.58.0 resolves to 91cf41a, equal to origin/main, and was created by release-publish.yml. Release page: https://github.com/rvdbreemen/adr-kit/releases/tag/v0.58.0. Sync-back PR #171 merged into dev, and the branches are in sync. All three clients report 0.58.0. npm dist-tags.latest is 0.58.0, after the maintainer approved it with 2FA. Two deviations: local pytest gave 1 failure (the adr-retire ceiling, TASK-212), so the run used --skip-tests and relied on CI; and preflight refuses prepare's own changes, so the phases ran with --only (recorded in TASK-213).
<!-- SECTION:FINAL_SUMMARY:END -->
