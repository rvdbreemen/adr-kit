---
id: TASK-220
title: Guardian hook entry still uses GNU sort -V to pick the plugin version
status: Done
assignee: []
created_date: '2026-10-06 11:12'
updated_date: '2026-10-06 16:21'
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
- [x] #1 The guardian hook entry no longer depends on sort -V
- [x] #2 A test runs the real template command (or its version-selection part) against stub version directories, as tests/test_pre_commit_portability.py does
- [x] #3 Behaviour on macOS confirmed by CI (macos-latest matrix job)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Premise confirmed, with a sharper consequence than the task said: the entry has no set -e, so a sort without version mode does not abort anything; the pipeline yields nothing, ADR_KIT stays empty, and [ -n ] / || true skip the guardian silently on every session start. Reproduced with a stub sort that rejects -V (test red), fixed by piping ls into the Python the entry already resolves (numeric max, sys.stdout.write so no CR on Windows). Whether macOS sort lacks -V was not verified here (I believe FreeBSD-derived sort has it); the fix removes the dependency either way.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed in PR #186 (merged be2458d, 14/14 CI checks green including both macOS matrix legs). The guardian SessionStart entry no longer pipes through sort -V: where sort lacks version mode the guardian was skipped silently on every session start. It now picks the numerically newest cached plugin with the Python it already resolves. tests/test_guardian_entry_portability.py runs the real template command with a stub sort that rejects -V (red before, green after) and checks 0.10.0 over 0.9.0. Existing projects get the new entry through /adr-kit:upgrade once the next release bumps its stamp.
<!-- SECTION:FINAL_SUMMARY:END -->
