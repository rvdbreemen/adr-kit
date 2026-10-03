---
id: TASK-212
title: adr-retire walks the tree with the same unbounded shape adr-lint had
status: Done
assignee: []
created_date: '2026-10-03 15:52'
updated_date: '2026-10-03 20:10'
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
- [x] #1 adr-retire's walk skips junctions and directory symlinks and has an entry/time budget like adr-lint's
- [x] #2 The local ceiling failure is attributed to load or to code, with a measurement on an idle machine
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
AC#2, attributed to code, not load. cProfile: resolve_present_terms took 3.4 s, of which 1.6 s was matching terms in file text and 1.5 s reading 1607 files. Of those files, 1174 (67.4 MB) sat in graphify-out/, which .gitignore:72 ignores, so CI never has it. That is why the ceiling test failed locally and passed in CI.

Fix: _walk_repo_files asks git first (`ls-files -z --cached --others --exclude-standard`), keeping the IGNORED_DIRS and suffix filters. Outside a git repository the os.walk fallback skips junctions and directory symlinks (reparse tag check, as adr-lint does) and stops after WALK_MAX_ENTRIES=100,000 or WALK_MAX_SECONDS=10 (AC#1). adr-retire on this repository went from 3.5 s to 0.97 s, and test_lint_and_retire_meet_hard_ceiling_on_this_repo passes locally again. New tests: test_retire_skips_what_git_ignores and test_retire_walk_does_not_follow_directory_links, both red before the fix. Perf, retire and corpus suites: 49 passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
adr-retire scans git's view of the project: tracked files plus untracked files that are not ignored. Its fallback walk skips links and has an entry and time budget. The local ceiling failure was code, not load: the scan read 67 MB of git-ignored graphify-out/. Runtime on this repo went from 3.5 s to 0.97 s.
<!-- SECTION:FINAL_SUMMARY:END -->
