---
id: TASK-220
title: Guardian hook entry still uses GNU sort -V to pick the plugin version
status: To Do
assignee: []
created_date: '2026-10-06 11:12'
labels:
  - bug
  - hooks
  - portability
dependencies: []
priority: medium
ordinal: 64000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
templates/cc-settings/guardian-hook-entry.json (line 7) selects the newest cached adr-kit with 'ls -d .../adr-kit/*/ | sort -V | tail -1'. This is the same portability defect issue #155 reported for the pre-commit hook: sort -V is a GNU extension the reporter says macOS lacks. 0.59.1 (TASK-216) fixed only templates/githooks/pre-commit. Found during the C4 refresh (TASK-219). Verify first which shells and platforms run this entry and whether set -e or && chaining turns a failing sort into a skipped guardian run, then pick the fix (version compare on the found Python, as the pre-commit hook now does).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The guardian hook entry no longer depends on sort -V
- [ ] #2 A test runs the real template command (or its version-selection part) against stub version directories, as tests/test_pre_commit_portability.py does
- [ ] #3 Behaviour on macOS confirmed by CI (macos-latest matrix job)
<!-- AC:END -->
