---
id: TASK-134
title: Restore fail-open Codex hook emitter
status: Done
assignee: []
created_date: '2026-08-04 20:11'
updated_date: '2026-08-04 20:18'
labels:
  - codex
  - hooks
  - bug
dependencies: []
references:
  - 'https://github.com/rvdbreemen/adr-kit/pull/61'
documentation:
  - 'https://learn.chatgpt.com/docs/hooks'
modified_files:
  - hooks/adr-hook.py
  - codex/hooks/adr-hook.py
  - copilot/hooks/adr-hook.py
priority: high
ordinal: 108500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The canonical ADR hook currently defines the _emit() body at module scope, so Codex hook processes fail during import with NameError instead of returning a fail-open response. Restore the function indentation and regenerate client hook mirrors.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 hooks/adr-hook.py defines the complete _emit() implementation inside the function
- [x] #2 Generated Codex and Copilot hook mirrors are regenerated from the canonical runtime
- [x] #3 Hook protocol regression tests pass and cover the import/runtime path
- [x] #4 Client generation check and whole-codebase ADR audit pass
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed the canonical _emit() indentation regression that caused Codex hook imports to fail with NameError, regenerated the Codex and Copilot mirrors, and merged the fix through PR #61. Focused hook/client tests passed (40 passed), client generation check passed, and whole-codebase ADR audit passed.
<!-- SECTION:FINAL_SUMMARY:END -->
