---
id: TASK-98
title: >-
  Record the PR guard as a fail-closed tier, and correct the two ADRs whose
  premise it breaks
status: To Do
assignee: []
created_date: '2026-08-03 19:32'
labels:
  - adr
  - hooks
  - retrospective
dependencies: []
priority: high
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Two Accepted ADRs assert something the shipped code contradicts. Both were found by reading the ADRs against `hooks/`, and both are load-bearing for other decisions.

**ADR-004.** Its Alternatives Considered rejects a fail-closed PreToolUse gate with "Blocking belongs at commit, not keystroke", and its Decision builds three fail-open injection tiers on top of that rejection. `hooks/adr_pr_guard.py` returns `permissionDecision: deny` from a PreToolUse hook. The rejected alternative shipped.

**ADR-019.** Its Context states "Every hook in this kit today is deterministic, model-free, offline, and finishes inside a fixed budget" and reasons from there to a silent session end. The hook next to it spawns `adr-judge` with `JUDGE_TIMEOUT_S = 120`, which is neither model-free nor inside the budget the sentence claims.

Neither is a small error. ADR-019's conclusion may still be right, but it currently rests on a false premise, and TASK-97 is about to build on that same hook. A decision whose stated reason is untrue cannot be re-evaluated honestly later — which is R0's whole argument for writing them down.

Write the record: `gh pr create` is a fail-closed tier, distinct from the three injection tiers, justified by the fact that a pull request is outward-facing and the commit gate has by then been passed or bypassed. Correct both premises through the supersession machinery, never by editing an Accepted Decision.

Spec: R2, Appendix A.1 (corrected in 65c8d8a).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 An ADR records the PR guard as a fail-closed tier and states what makes it different from the three fail-open injection tiers
- [ ] #2 ADR-004's rejected alternative is addressed explicitly: what changed, and why the rejection no longer holds at this moment
- [ ] #3 ADR-019's premise is corrected through supersession or a successor, not by editing its Accepted text
- [ ] #4 The new record states which hooks are model-free and which are not, so the next reader does not have to re-derive it
- [ ] #5 `bin/adr supersede` writes both sides of every link
<!-- AC:END -->
