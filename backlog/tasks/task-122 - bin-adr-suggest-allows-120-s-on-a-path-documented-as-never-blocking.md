---
id: TASK-122
title: bin/adr-suggest allows 120 s on a path documented as never blocking
status: To Do
assignee: []
created_date: '2026-08-04 05:25'
labels:
  - guardian
  - llm
  - ux
dependencies: []
priority: low
ordinal: 101500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`bin/adr-suggest` runs its model call with a 120 s timeout. It is reached from the guardian sweep, which is documented as advisory and free to interrupt.

Two minutes of no output is indistinguishable from a hang. A user who reads "this never blocks" and then waits two minutes will kill the process, and killing it does not stop the model CLI it spawned -- the same grandchild problem the pull-request guard just fixed with `--llm-timeout`.

Bring the timeout down to something a person will wait through, or emit progress so the wait is legible. Whichever is chosen, the number should come from the same place the caller's budget does rather than from a constant in this file.

Evidence: the timeout constant in `bin/adr-suggest`; the guardian tier description in `.claude/adr-kit-guide.md`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The suggest timeout is derived from the caller's budget, not a local constant
- [ ] #2 Either the wait is short enough to sit through or progress is visible while it runs
- [ ] #3 Killing the parent does not leave a model CLI running
<!-- AC:END -->
