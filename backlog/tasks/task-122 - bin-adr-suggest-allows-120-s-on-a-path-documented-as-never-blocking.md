---
id: TASK-122
title: bin/adr-suggest allows 120 s on a path documented as never blocking
status: To Do
assignee: []
created_date: '2026-08-04 05:25'
updated_date: '2026-08-04 23:02'
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
INVESTIGATION 2026-08-05 — TWO PREMISES IN THIS RECORD ARE WRONG.

THE NUMBER IS REAL: bin/adr-suggest:99 sets DEFAULT_LLM_TIMEOUT_S = 120; resolve_llm_timeout (:558-567) falls through --llm-timeout -> suggest.llm_timeout_seconds -> judge.llm_timeout_seconds -> 120; main hands it to run_llm_suggest (:733-735) which passes it to subprocess.run(timeout=...) in HostBackend.judge (bin/adr_llm.py:350-359). No caller supplies --llm-timeout today, so every path gets 120 s.

WRONG PREMISE 1 — 'derive the timeout from the caller's budget' presupposes a caller budget. There is none, in three independent places. adr-suggest is not one of the eight events in hooks/manifest.json, so it is not a client hook and adr_pr_guard.guard_budget_s() has no analogue to read. .githooks/pre-commit puts no timeout on the suggest pass at all (:268-273); its only budget is the 5000 ms advisory WARN measuring adr-judge between _T0 and _T1 (:214-216), and the suggest pass runs AFTER _T1, outside the measured window entirely. And ADR-015 excludes this path by name.

WRONG PREMISE 2 — the model CLI is a DIRECT CHILD of adr-suggest, not a grandchild. The pull-request guard's --llm-timeout fix addressed a different topology; citing it here misdirects the fix.

AC#3 IS NOT CLOSABLE ON WINDOWS by this change. A hard guarantee that killing the parent kills the model CLI needs a Job Object with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE. The repo has zero precedent for job objects, process groups or psutil (verified by grep). Introducing a new OS primitive on the hardest platform for a low-priority task is a maintainer call, not an implementation detail.

OPEN DECISION: the proposed ~20 s fallback needs a fresh measurement on a named machine class, recorded as evidence. ADR-001's 2026-07 '5-10 seconds' figure is too old to reuse, and a number in a comment with no measurement behind it is exactly what this sweep exists to stop.

ORDERING: land together with TASK-121 in ONE commit. Both edit templates/githooks/pre-commit at :212-216 and their drafts contradict each other — TASK-121 replaces the literal 5000 with a config-read value, TASK-122 hoists the same literal into a constant. TASK-121's wired key is the source of truth.
<!-- SECTION:NOTES:END -->
