---
id: TASK-212
title: adr-retire walks the tree with the same unbounded shape adr-lint had
status: To Do
assignee: []
created_date: '2026-10-03 15:52'
labels:
  - retire
  - performance
  - windows
dependencies: []
priority: medium
type: bug
ordinal: 56000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found during TASK-209. bin/adr-retire walks repo_root with os.walk(followlinks=False) (around line 195), which descends into Windows junctions, the same shape TASK-209 bounded in adr-lint. Separately, test_lint_and_retire_meet_hard_ceiling_on_this_repo fails locally on adr-retire: p50 2054-2940 ms against the 2000 ms ceiling, on unmodified dev, while the machine's commit charge was 70-94%. It passes in CI. Not verified whether the local failure is load or code.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 adr-retire's walk skips junctions and directory symlinks and has an entry/time budget like adr-lint's
- [ ] #2 The local ceiling failure is attributed to load or to code, with a measurement on an idle machine
<!-- AC:END -->
