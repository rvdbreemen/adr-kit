---
id: TASK-246
title: 'Release driver: three defects seen during v0.61.1'
status: To Do
assignee: []
created_date: '2026-11-19T20:43:00Z'
labels: []
dependencies: []
priority: medium
type: bug
ordinal: 88000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Observed while releasing v0.61.1 (TASK-245); causes not yet reproduced in isolation.
1. verify hides the failing test: release_phases.py runs pytest with -p no:cacheprovider and reports only the summary tail, so '1 failed' gives no node id. Here it was a wall-clock flake (test_lint_and_retire_meet_hard_ceiling_on_this_repo) under machine load; finding it cost a second 21-minute run.
2. tag phase gave up after 45 min with 'gave up waiting for release-publish.yml to create v0.61.1', while git ls-remote showed refs/tags/v0.61.1 at 0ab9cb7 from 19:48 UTC, minutes after the merge. The detection does not see a tag that exists on origin.
3. Resume after that stop is blocked by preflight 'dev does not carry every published release' - the very syncback phase the driver would run next. Had to do the sync-back by hand (PR #213).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 verify names failing test ids in its stop message
- [ ] #2 tag phase detects a workflow-created tag on origin; regression test reproduces the 45-minute miss
- [ ] #3 preflight does not refuse a resume whose only gap is this release's own pending syncback
<!-- AC:END -->
