---
id: TASK-114
title: Bring spec.md Appendices A and B up to what ships
status: Done
assignee: []
created_date: '2026-08-03 19:35'
updated_date: '2026-08-03 22:28'
labels:
  - docs
  - spec
dependencies:
  - TASK-103
  - TASK-98
priority: low
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Partly done in 65c8d8a: A.1 now lists eight events, names `plan-exit` and `pr-create`, scopes the "does not block" sentence to the six injection hooks, and mentions the guardian's own SessionStart entry. What remains:

**A.2.** The pre-commit hook runs three further passes after the blocking judge — the advisory `adr-index --check` staleness warning, the `adr-grill-signal` nudge, and the opt-in `adr-suggest` nudge. Say which of them blocks (only `adr-judge`). The `adr-suggest` line matters: the inventory does not currently show that a commit-time half of the missing-ADR question exists at all.

**A.3.** Add `branch-sync-check.yml` (daily cron `0 7 * * *`) or state why a non-ADR workflow is out of scope. Refresh the downstream list to four templates and three composite actions. Note that `adr-index-check.yml` is scoped `branches: [main]` and that dev freshness comes from `validate.yml`. Correct that `adr-lint-self.yml` also carries a `pytest tests/ -v` job.

**A.4.** The conclusion is stale as a claim about the kit, though literally defensible as scoped. `/adr-kit:review` is a shipped path — mirrored into `codex/skills/review/` and `copilot/skills/review/`, registered as workflow id `review` in `clients/workflows.json` — and its Step 4 runs `adr-suggest` over `merge-base(BASE,HEAD)..HEAD`, then requires the model's own vigilance pass. That is the question asked with the whole change in view. What remains true: nothing fires unless someone asks, and plan-exit was built to close that and does not fire.

Re-check after TASK-103 and TASK-98 land, since both change what the inventory should say.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A.2 lists all four pre-commit passes and states that only `adr-judge` blocks
- [x] #2 A.3 is accurate on workflow count, cron, branch scoping and the pytest job
- [x] #3 A.4 credits `/adr-kit:review` as a shipped path and narrows the claim to what is still true
- [x] #4 The appendices carry a date stamp so a later reader knows what they were true of
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A.2, A.3 and A.4 corrected; A.1 was already done in 65c8d8a.

**A.2** now shows the pre-commit hook as four passes with a blocks column, and only `adr-judge` blocks. The `adr-index --check` row carries the reason it is advisory rather than blocking: it reads the worktree while the commit is the staged snapshot, so a block there would refuse correct work on a partial commit. The `adr-suggest` row is the one that matters for R2 — a commit-time missing-ADR pass exists, off by default, asking about one commit rather than the whole branch, which is precisely why the pull-request moment is a separate question rather than a duplicate.

**A.3** was wrong in four places, all verified against the files: `adr-index-check.yml` is scoped `branches: [main]`; `adr-lint-self.yml` also runs `pytest tests/ -v`; `validate.yml` now runs `adr-lint docs/adr` and markdownlint; the downstream list is four templates and three composite actions, not two and two. `branch-sync-check.yml` (daily 07:00) is added and explicitly labelled as not an ADR gate — worth listing because it catches a release nobody merged back, which has silently reverted a release twice.

**A.4 was the substantive correction.** It claimed only the PreToolUse nudge ever asks whether a new ADR should exist. Three moments do: that nudge, the opt-in commit-time `adr-suggest` pass, and `/adr-kit:review`, whose step 4 runs `adr-suggest` over `merge-base(BASE,HEAD)..HEAD` and then requires the model's own vigilance pass — that third one *is* the question asked with the whole change in view, and it ships on all three clients.

What survives is narrower and sharper than the original claim: none of them fires unless someone asks. So an unrecorded decision survives by default while a violated one meets four gates. That asymmetry is the actual finding, and it is what ADR-024 addresses.

AC#4: the appendix is date-stamped 2026-08-04, with the reason stated — an inventory without a date reads as timeless and is the first thing to rot.
<!-- SECTION:FINAL_SUMMARY:END -->
