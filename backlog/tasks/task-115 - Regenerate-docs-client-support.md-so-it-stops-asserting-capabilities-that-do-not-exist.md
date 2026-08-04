---
id: TASK-115
title: >-
  Regenerate docs/client-support.md so it stops asserting capabilities that do
  not exist
status: To Do
assignee: []
created_date: '2026-08-03 19:36'
updated_date: '2026-08-04 01:29'
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

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude
created: 2026-08-04 01:29
---
**Verified as genuinely blocked, not deferred.** Checked on `feat/spec-gap-decisions` today:

- `hooks/manifest.json` still has `plan-exit` with `command: plan-exit`, the value that makes it fall through to noop. The fix is on `release/v0.44.1`.
- `codex/hooks/adr_pr_guard.py` does not exist here. The mirror fix is on `release/v0.44.1`.

So both claims this task exists to correct — `Plan exit | supported (ExitPlanMode)` and Codex `Edit query | supported` — are false **on this branch** and true after #58 merges. Regenerating now can only produce one of two wrong artefacts: the current state, which becomes wrong on merge, or the post-merge state, which is a lie today.

AC#2 and AC#4 partly escape that — a shell-tool row and a live Claude probe are about client capability rather than about our wiring — but the PR-moment row is state-dependent, so splitting the task would leave the matrix half-regenerated and needing a second pass anyway.

Merging the release branch into this one would unblock it and was considered. Rejected: it puts #58's commits inside #59, which restructures a two-PR release flow the maintainer set up, to close one task. That is optimising for a checklist over someone else's process.

**Unblocks the moment #58 lands on `main` and reaches `dev`.**
---
<!-- COMMENTS:END -->
