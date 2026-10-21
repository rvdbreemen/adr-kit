---
id: TASK-241
title: Release adr-kit v0.61.0
status: Done
assignee: []
created_date: '2026-10-21T20:12:00Z'
updated_date: '2026-10-21T20:24:00Z'
labels:
  - release
dependencies: []
priority: high
ordinal: 83000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Minor release: native OMP support (ADR-050, TASK-239) and replies in the user's language (TASK-238) are consumer-visible behaviour changes, so this is a minor bump from 0.60.0.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 All version sites read 0.61.0 and CHANGELOG [0.61.0] reads as release notes
- [x] #2 Tag v0.61.0 resolves to origin/main and the GitHub Release exists
- [x] #3 Sync-back PR into dev is merged
- [ ] #4 npm staging handed to the maintainer for 2FA approval
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
v0.61.0 released: minor bump for native OMP support (ADR-050, TASK-239) and replies in the user's language (TASK-238). Release PR #203 merged into main; tag v0.61.0 = origin/main = 413b9d3; GitHub Release https://github.com/rvdbreemen/adr-kit/releases/tag/v0.61.0; release-publish run 39669438195 succeeded including npm staging; sync-back PR #204 merged, check-branch-sync in sync. Verify ran with --skip-tests (CI ran pytest on six runners); one local Windows run had failed test_pre_commit_portability's bash probe, which skips alone. Install phase stopped: claude/codex/copilot report 0.60.0 because running clients lock their plugin directories; rerun python scripts/release.py 0.61.0 after closing them. OMP reinstalled from the GitHub marketplace at 0.61.0 and smoke-tested: extension fires, omp-cli recorded. AC #4 open: npm staged package awaits maintainer 2FA approval.
<!-- SECTION:FINAL_SUMMARY:END -->
