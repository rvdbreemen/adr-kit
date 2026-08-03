---
id: TASK-115
title: >-
  Regenerate docs/client-support.md so it stops asserting capabilities that do
  not exist
status: To Do
assignee: []
created_date: '2026-08-03 19:36'
labels:
  - docs
  - clients
dependencies:
  - TASK-90
  - TASK-103
priority: medium
ordinal: 5100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The capability document asserts rather than evidences. Line 14 claims `Plan exit | supported (ExitPlanMode)` for Claude Code — measurably false. Line 15 claims `Edit query | supported` for Codex CLI, also false while the mirror cannot import `adr_pr_guard`. The file is 36 lines, Evidence reads "simulated only" for all three clients, macOS and Linux are "not-run", and there is no row for the shell tool or the PR moment despite TASK-76 AC#6 being ticked for exactly that.

R17 (now in the spec) requires a generated support matrix stating per client and per operating system where an outcome is reached by a weaker route. A matrix that claims capabilities the code does not have is worse than none: it is what someone reads before deciding the kit covers their client.

Regenerate after TASK-90 and TASK-103 land, since both change what is true.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The matrix is regenerated from evidence after the two hook fixes land
- [ ] #2 Rows exist for the shell tool and the PR moment, naming which clients expose a hookable shell tool and what happens where none is exposed
- [ ] #3 Every claim carries its evidence class; 'simulated only' is labelled as such rather than reading as a test result
- [ ] #4 At least the Claude Code surface is probed live rather than simulated, since a claim of maximal hook use rests on knowing what the client offers
<!-- AC:END -->
