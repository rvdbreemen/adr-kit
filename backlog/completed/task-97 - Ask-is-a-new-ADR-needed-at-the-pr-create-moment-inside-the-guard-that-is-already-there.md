---
id: TASK-97
title: >-
  Ask 'is a new ADR needed?' at the pr-create moment, inside the guard that is
  already there
status: Done
assignee: []
created_date: '2026-08-03 19:32'
updated_date: '2026-08-05 07:20'
labels:
  - hooks
  - adr
  - decision
dependencies:
  - TASK-90
priority: high
ordinal: 1500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
R2 asks two questions at the moment a branch becomes a pull request: does this change violate an accepted decision, and does it contain a decision nobody recorded. Only the first is answered today. The second happens if someone types `/adr-kit:review` or has individually opted into `ADR_KIT_SUGGEST`, which means in practice it does not happen.

**Decided (maintainer, 2026-08-03).** Extend `hooks/adr_pr_guard.py`. It already intercepts `gh pr create` and runs the judge; the suggest nudge joins it, so the moment answers both halves of R2 instead of one.

Why not a CI workflow: ADR-019 rests on "No hook may spend money on an event the user cannot see fire and cannot refuse." A `pull_request` job spends on every push with nobody present to refuse, and the bill lands on the repository owner rather than the author. In-session, the user watches it run and can decline. The cost of the choice, stated: a PR opened by hand — from the web UI, from a teammate not using an agent — gets nothing. That gap is real and belongs in the ADR rather than in a footnote.

Depends on TASK-90: the guard only runs on Claude Code today, because `adr_pr_guard.py` never reached the Codex and Copilot mirrors.

Spec: R2, R14 track 2.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An ADR records the decision and states plainly that a hand-opened PR is not covered
- [x] #2 The `gh pr create` interception emits the missing-ADR nudge alongside the judge verdict
- [x] #3 A violation still denies; a suggestion never denies — the nudge is advisory and cannot block the tool call on its own
- [x] #4 The combined path stays inside the 5 s budget the manifest already declares for `pr-create`
- [x] #5 The nudge is skipped when the branch carries no candidate decisions, so a clean branch sees nothing
- [x] #6 A test drives the guard with a branch that adds a dependency and asserts both the verdict and the nudge appear
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude
created: 2026-08-03 20:53
---
Decision recorded: ADR-024, Proposed, passes all gates.

The hand-opened pull request is in the Consequences as an accepted gap, not a footnote: a PR from the web interface, from a teammate not using an agent, or from a script gets nothing, and a CI workflow is the only thing that closes it. The ADR refuses to ship that workflow **on by default** rather than refusing the workflow — a project may add one, and the Exceptions section says so.

ADR-024 rests on ADR-023's principle rather than restating ADR-019's: the dividing line is whether the user can see a hook fire and refuse it, which is what makes the in-session moment acceptable and the CI moment not.

Remaining: AC#2 through AC#6 are implementation, blocked on TASK-90 landing on this branch (the guard reaches only Claude Code until the mirrors ship, and that fix is on release/v0.44.1).
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The pull-request moment now answers both halves of R2. ADR-024 flipped to binding:true with gate adr-pr-suggest-v1, which the declared-gate check required as soon as the anchor landed.

AC#2 -- the nudge hangs off judge_branch rather than sitting beside it, and that is the design decision worth recording. A second entry point would need its own base_ref probe and its own git diff, spending the 5 s budget twice on the same bytes -- and the branches with the largest diffs are the ones most worth asking about, so the waste would scale with how much it matters. Attaching it means one Deadline, one diff, one extra subprocess.

AC#3 -- advisory by construction. A violation still denies and the nudge rides along, because the branch that broke a rule is also the one most likely to be making a decision. On a clean branch the nudge speaks alone. The test that matters most reads the deny branch off the source and asserts the nudge never contributes to it: that failure would be invisible in a passing suite until the day someone's clean branch was blocked for containing a decision.

AC#4 -- the nudge spends from the guard's existing Deadline and passes what is left down as --llm-timeout, so killing the child also bounds the model call it makes. Asserted directly.

AC#5 -- adr-suggest's "(skipped: ...)" and "LLM unavailable" notes are filtered out, so a branch with no candidate decision prints nothing. Without that the guard would be noisy on exactly the branches it has nothing to say about.

AC#6 -- eight tests, including both mirrors carrying the nudge. That last one exists because the v0.44.1 outage was a guard that existed in one tree and not the others.

One asymmetry is deliberate and documented: a failing suggest is silent while a failing judge reports. An unchecked branch looks exactly like a clean one; a missing suggestion carries no such ambiguity.

The gap ADR-024 names remains: a pull request opened by hand, from the web UI or by a teammate not using an agent, gets nothing.
<!-- SECTION:FINAL_SUMMARY:END -->
