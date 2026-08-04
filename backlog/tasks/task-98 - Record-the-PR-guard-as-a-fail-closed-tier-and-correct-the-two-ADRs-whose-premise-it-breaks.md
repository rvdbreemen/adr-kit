---
id: TASK-98
title: >-
  Record the PR guard as a fail-closed tier, and correct the two ADRs whose
  premise it breaks
status: Done
assignee: []
created_date: '2026-08-03 19:32'
updated_date: '2026-08-03 20:53'
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
- [x] #1 An ADR records the PR guard as a fail-closed tier and states what makes it different from the three fail-open injection tiers
- [x] #2 ADR-004's rejected alternative is addressed explicitly: what changed, and why the rejection no longer holds at this moment
- [x] #3 ADR-019's premise is corrected through supersession or a successor, not by editing its Accepted text
- [x] #4 The new record states which hooks are model-free and which are not, so the next reader does not have to re-derive it
- [x] #5 `bin/adr supersede` writes both sides of every link
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
ADR-023 written and Proposed, passing all gates. Reciprocal `related` links written to ADR-004 and ADR-019 with `bin/adr relate`.

**The contradiction was sharper than this task stated, and in a different place.** I had framed it as the guard contradicting ADR-004's *rejected alternative*. Reading ADR-004 line by line, that rejection is about denying **edits** to governed paths, and its reasoning — "legitimate compliant edits touch governed paths constantly" — turns on frequency and on a later backstop existing. Neither applies to a pull request, which happens once per branch and after the commit gate is behind the user. That rejection stands untouched, including "blocking belongs at commit, not keystroke".

What the guard actually contradicts is ADR-004 **Decision point 2**: "`bin/adr-judge` at pre-commit (and the CI action) remains the only mechanism that blocks." That is a claim about what exists, and it is false.

**ADR-019's conclusion survives its premise, and the ADR says why.** ADR-019 offers two supports for end-of-session silence: that all hooks are model-free (false, as the guard shows), and that a session does not end while the user is watching. The second is load-bearing and untouched — and it is the same property that makes the pull-request moment acceptable. So the dividing line for a fail-closed or spending hook is not "model or no model" but "can the user see it fire and refuse it". ADR-019 comes out of this with a better argument than it shipped with.

**Neither ADR is superseded, deliberately.** This toolkit has no `amends` relationship. Superseding ADR-004 would retire an injection architecture still in force; superseding ADR-019 would retire a conclusion still correct. Both destroy more than they correct. The ADR records that the alternative was unavailable, because the next person to find a stale sentence in an Accepted ADR faces the same choice.

Acceptance is the maintainer's action.
<!-- SECTION:FINAL_SUMMARY:END -->
