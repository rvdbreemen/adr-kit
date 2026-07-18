---
id: TASK-32.5
title: Make release and shared-state updates transaction-safe
status: Done
assignee:
  - Codex
created_date: '2026-07-18 19:52'
updated_date: '2026-07-18 20:28'
labels:
  - release
  - concurrency
  - atomicity
  - F-15
  - F-16
dependencies: []
references:
  - docs/reviews/2026-07-18-source-audit/FINDINGS.md
modified_files:
  - bin/bump-version
  - bin/adr_state.py
  - bin/adr-guardian
  - bin/adr-watch
  - tests/test_bump_version.py
  - tests/test_adr_state_concurrency.py
parent_task_id: TASK-32
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Resolve source-audit F-15 and F-16 by fully preflighting release bumps, applying multi-file changes with rollback safety, and locking complete guardian/watcher state read-modify-write cycles.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Version bump validates every target and computes all edits before the first write.
- [x] #2 Injected write failures cannot leave a partially bumped release tree.
- [x] #3 Guardian and watcher lock the complete state read-modify-write transaction and use unique same-directory temporary files plus atomic replacement.
- [x] #4 Concurrent state and release failure regression tests pass.
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Closed F-15 and F-16. bump-version now requires and validates all ten release targets, computes all edits before the first write, uses unique same-directory atomic replacements, rolls back every target on any failure, and prints a complete staging hint. Guardian and watcher now use one shared stdlib state transaction: blocking fcntl/msvcrt locking covers the full read-modify-write cycle, unique temporary files are fsynced and atomically replaced, and lock/write failure remains fail-open. Concurrent integration tests prove eight guardian trends and eight unique watcher cooldowns are all preserved. Verification: 82 focused release, guardian, watcher, and concurrency tests passed.
<!-- SECTION:FINAL_SUMMARY:END -->
