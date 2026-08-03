---
id: TASK-114
title: Bring spec.md Appendices A and B up to what ships
status: To Do
assignee: []
created_date: '2026-08-03 19:35'
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
- [ ] #1 A.2 lists all four pre-commit passes and states that only `adr-judge` blocks
- [ ] #2 A.3 is accurate on workflow count, cron, branch scoping and the pytest job
- [ ] #3 A.4 credits `/adr-kit:review` as a shipped path and narrows the claim to what is still true
- [ ] #4 The appendices carry a date stamp so a later reader knows what they were true of
<!-- AC:END -->
