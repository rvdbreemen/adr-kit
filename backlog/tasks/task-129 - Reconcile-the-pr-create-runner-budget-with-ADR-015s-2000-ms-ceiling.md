---
id: TASK-129
title: pr-create carries a 5000 ms latency budget against ADR-015's 2000 ms Must Not
status: To Do
assignee: []
created_date: '2026-08-04 05:24'
updated_date: '2026-08-04 05:30'
labels:
  - adr
  - hooks
  - consistency
dependencies: []
priority: high
ordinal: 97500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ADR-015's Decision Contract says, under **Must Not**: "No deterministic user-facing path may carry a hard budget above 2000 ms." Its **Must** requires every CLI *or hook* path to keep a budget entry in a committed latency fixture, and its References name `hooks/manifest.json` as the per-event hook budget file. So the hook manifest is inside ADR-015's scope, in the ADR's own words.

`hooks/manifest.json` gives `pr-create` a `latency_budget_ms` of 5000. That is the divergence. It is **pre-existing**: introduced by commit 323a38a, shipped in v0.44.0, already on `main`. The v0.44.1 hotfix added `runner_timeout_sec: 5` to the same entry, which is a different quantity -- a kill timeout, not a latency budget. `session-start` carries `runner_timeout_sec: 5` against a 500 ms budget, so the two numbers were never meant to match.

The reason it went unnoticed is the interesting part, and the real work here: **nothing enforces the hook side of ADR-015.** The ADR's Enforcement block only requires `"hard_timeout_ms": 2000` in `tests/fixtures/cli/latency-corpus.json`. `tests/test_hook_performance.py` contains no reference to the ceiling at all. A 5000 ms hook budget could land, ship to users, and pass every gate -- which is exactly what happened.

Two decisions, in order:

1. **Enforce the hook side.** Assert the ceiling against `hooks/manifest.json` the way it is asserted against the CLI corpus, so the next entry above 2000 ms fails rather than ships.
2. **Then settle pr-create.** Either bring the budget under 2000 ms and accept that the branch judge cannot run an LLM pass there, or amend ADR-015 with a new ADR that names the pull-request moment as a deliberately slower, user-initiated event. ADR-015 already excepts opt-in LLM passes; the branch guard runs the declarative pass by default, so it does not fall under that exception as written.

Evidence: `docs/adr/ADR-015-*.md` (Decision Contract, References, Enforcement); `hooks/manifest.json` `pr-create` entry; commit 323a38a; `tests/test_hook_performance.py` (no ceiling assertion).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A test asserts ADR-015's 2000 ms ceiling against every latency_budget_ms in hooks/manifest.json, and fails on the current pr-create entry
- [ ] #2 pr-create is either under the ceiling or covered by an accepted amending ADR that names it
- [ ] #3 The changelog states which of the two happened, because the 5000 ms budget shipped to users in v0.44.0
<!-- AC:END -->
