---
id: TASK-184
title: Fix OpenCode reference registration for v1.18.18
status: Done
assignee: []
created_date: '2026-08-19 22:13'
updated_date: '2026-08-19 22:34'
labels:
  - opencode
  - bug
  - compatibility
dependencies: []
references:
  - 'https://opencode.ai/docs/references/'
  - 'https://opencode.ai/config.json'
modified_files:
  - opencode/plugin.ts
  - tests/test_opencode_plugin.py
priority: high
type: bug
ordinal: 28000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Prevent the native OpenCode plugin from making OpenCode fail startup when it registers the local docs/adr reference on Windows. OpenCode's config-hook mutations cannot safely create its internal reference schema classes, so the plugin uses the official local string shortcut; agent-facing ADR guidance remains supplied through ADR-guide.md.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 OpenCode 1.18.18 reaches the TUI prompt in this project without the ConfigV2.Reference validation error.
- [x] #2 The adr-decisions reference remains registered as the local docs/adr directory through the supported string shortcut.
- [x] #3 Focused OpenCode tests pass.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Confirm the installed OpenCode reference contract, update the plugin registration, add a focused regression assertion, and validate OpenCode startup plus the relevant test suite.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented the reference registration fix in opencode/plugin.ts and updated tests/test_opencode_plugin.py. Verification: python -m pytest -q tests/test_opencode_plugin.py tests/test_opencode_package.py -> 10 passed; opencode --print-logs reached the TUI prompt on Windows before the deliberate 20-second non-interactive timeout.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
OpenCode startup no longer receives a plain object reference from the plugin config hook. The supported local string reference keeps adr-decisions available while avoiding the runtime schema-class mismatch.
<!-- SECTION:FINAL_SUMMARY:END -->
