---
id: TASK-97
title: >-
  Ask 'is a new ADR needed?' at the pr-create moment, inside the guard that is
  already there
status: In Progress
assignee: []
created_date: '2026-08-03 19:32'
updated_date: '2026-08-03 20:53'
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
- [ ] #2 The `gh pr create` interception emits the missing-ADR nudge alongside the judge verdict
- [ ] #3 A violation still denies; a suggestion never denies — the nudge is advisory and cannot block the tool call on its own
- [ ] #4 The combined path stays inside the 5 s budget the manifest already declares for `pr-create`
- [ ] #5 The nudge is skipped when the branch carries no candidate decisions, so a clean branch sees nothing
- [ ] #6 A test drives the guard with a branch that adds a dependency and asserts both the verdict and the nudge appear
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
