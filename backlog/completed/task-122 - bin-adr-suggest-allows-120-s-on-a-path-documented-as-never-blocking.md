---
id: TASK-122
title: bin/adr-suggest allows 120 s on a path documented as never blocking
status: Done
assignee: []
created_date: '2026-08-04 05:25'
updated_date: '2026-08-05 06:11'
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
- [x] #1 The suggest timeout is derived from the caller's budget, not a local constant
- [x] #2 Either the wait is short enough to sit through or progress is visible while it runs
- [x] #3 Killing the parent does not leave a model CLI running
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

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Both premises in this record were wrong; the investigation notes above record why. What remained was real and is fixed.

AC#1 -- "derived from the caller's budget" presupposed a caller budget that did not exist anywhere: adr-suggest is not a manifest event, the pre-commit template put no timeout on the suggest pass at all, and ADR-015 excludes the path by name. So the caller budget was created rather than located: the template now passes --llm-timeout derived from the same judge.pre_commit_timeout_ms its own warning uses, with a 10 s floor because a budget of 0 disables the WARN and does not mean "no time at all". The flag already existed and no caller had ever used it.

AC#2 -- the default drops from 120 s to 30 s, with the basis stated in the source rather than left as a bare number: ADR-001 measured a local suggest call at 5-10 s in 2026-07, so 30 s leaves generous headroom while staying inside what a person will sit through. Two minutes of silence is indistinguishable from a hang, which is what made the old value harmful rather than merely generous.

AC#3 -- the record described a grandchild problem that does not exist here. The model CLI is a DIRECT child of adr-suggest (bin/adr_llm.py:350-359), so subprocess.run(timeout=) kills it when the bound expires. What is genuinely not covered is a grandchild the model CLI spawns for itself; a hard guarantee there needs a Windows Job Object with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE, and this repository has no precedent for job objects, process groups or psutil. That limit is named in the source rather than papered over, and introducing a new OS primitive on the hardest platform for a low-priority path was not worth it against a 30 s bound.

Landed in one commit with TASK-121, as the investigation required: both edit the same template lines and their drafts contradicted each other.
<!-- SECTION:FINAL_SUMMARY:END -->
