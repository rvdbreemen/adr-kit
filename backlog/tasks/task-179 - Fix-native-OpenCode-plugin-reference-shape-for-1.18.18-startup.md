---
id: TASK-179
title: Fix native OpenCode plugin reference shape for 1.18.18 startup
status: Done
assignee: []
created_date: '2026-08-18 17:45'
updated_date: '2026-08-18 18:17'
labels:
  - opencode
  - plugin
  - compatibility
  - startup
dependencies: []
references:
  - 'https://opencode.ai/config.json'
  - 'https://opencode.ai/docs/plugins/'
modified_files:
  - opencode/plugin.ts
  - tests/test_opencode_plugin.py
priority: high
type: bug
ordinal: 23000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The native OpenCode plugin adds references.adr-decisions as an object with path and description, but OpenCode 1.18.18 rejects that object during startup with ConfigV2.Reference.Git/Local validation errors. Reproduce the failure, align the additive registration with the runtime contract, and preserve user-owned references.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 OpenCode starts from the repository checkout without a ConfigV2.Reference validation error when docs/adr exists.
- [x] #2 The plugin registers the ADR reference using a shape accepted by OpenCode 1.18.18 and preserves existing user-owned references.
- [x] #3 Focused OpenCode plugin and package tests pass.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Reproduce the OpenCode 1.18.18 startup failure and inspect the current reference contract. 2. Patch the plugin and focused regression test. 3. Run focused OpenCode checks and the smallest relevant repository gates.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reproduced the warning on OpenCode 1.18.18 with external plugins enabled. The runtime rejected the object reference shape even though the documented schema lists it, while a string path is accepted. Changed opencode/plugin.ts to register docs/adr as a string path and extended the Bun smoke test to verify the string shape and preservation of an existing user reference.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-08-18 18:17
---
Verification: python -m pytest -q tests/test_opencode_plugin.py tests/test_opencode_package.py (10 passed); python scripts/build-client-adapters.py --check (changed=0); OPENCODE_PURE=0 opencode run --print-logs hello reached session creation without a ConfigV2.Reference warning.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
OpenCode startup compatibility fixed by using the cross-version string reference form. Verified with the focused plugin/package suite, OpenCode 1.18.18 startup, and the three-client adapter drift check.
<!-- SECTION:FINAL_SUMMARY:END -->
