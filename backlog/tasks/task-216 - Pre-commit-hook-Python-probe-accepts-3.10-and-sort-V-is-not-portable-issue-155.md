---
id: TASK-216
title: >-
  Pre-commit hook: Python probe accepts <3.10 and sort -V is not portable (issue
  #155)
status: Done
assignee: []
created_date: '2026-10-05 20:37'
updated_date: '2026-10-06 05:05'
labels:
  - bug
  - hooks
  - portability
dependencies: []
priority: high
ordinal: 60000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Reported in GitHub issue #155 by an external user. templates/githooks/pre-commit (copied to .githooks/pre-commit and the codex/copilot adapters): (1) the interpreter probe accepts the first command reporting any Python 3, though adr-judge needs 3.10+, so python3=3.9 next to python=3.12 picks 3.9 and fails; (2) the plugin-version comparison shells out to sort -V under set -e, a GNU extension the reporter says breaks on macOS. Fix both by asking the interpreter itself: probe sys.version_info >= (3, 10), and compare versions with the already-required Python.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The probe skips a Python below 3.10 and keeps searching the remaining candidates
- [x] #2 The plugin-version comparison uses the selected Python, not sort -V
- [x] #3 Tests run the real template block with stub interpreters on PATH, not a copy of it
- [x] #4 Generated adapter copies regenerated; build-client-adapters --check reports changed=0
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Probe now asks each candidate for sys.version_info (one-liner, CR stripped for Windows) and skips anything below 3.10. _version_ge() compares dotted versions numerically with the selected Python; the sort -V line is gone. New tests/test_pre_commit_portability.py cuts the probe block and _version_ge() out of the real template and runs them with stub interpreters on PATH: red on dev (3.9 and 3.8 accepted, sort -V present), green after. The error message keeps its 'Python 3 not found' prefix because test_init_python_check anchors on it. Adapters regenerated, --check changed=0. Targeted run over the 24 test files touching templates or adapters: 671 passed, 8 skipped; adr-lint --strict clean. Full local suite not run (commit charge 94%); CI matrix is the full check. Note: test_python_check.py still carries an inline copy of the old probe (says 3.9+); it tests the copy, not the template.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed in PR #179 (merged into dev, 12/12 CI jobs green including macOS) and shipped in v0.59.1. The probe skips any Python below 3.10 and keeps searching; _version_ge() replaces sort -V. Tests cut both blocks from the real template and run them with stub interpreters. Issue #155 closed by the merge; the reporter was answered and thanked.
<!-- SECTION:FINAL_SUMMARY:END -->
