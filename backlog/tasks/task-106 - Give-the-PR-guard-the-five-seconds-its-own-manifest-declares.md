---
id: TASK-106
title: Give the PR guard the five seconds its own manifest declares
status: To Do
assignee: []
created_date: '2026-08-03 19:34'
labels:
  - hooks
  - bug
dependencies: []
priority: medium
ordinal: 3300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`hooks/hooks.json` gives the Bash matcher `"timeout": 1` while `hooks/manifest.json` declares `latency_budget_ms: 5000` for `pr-create`, and the guard's own internals allow 60 s for `git diff` and `JUDGE_TIMEOUT_S = 120`. Measured warm end-to-end is ~0.8 s declarative-only — already inside the noise of a 1 s cap. One `llm_judge: true` ADR in scope is seconds, so the guard is killed before it answers.

Do **not** build a drift test between the two files: `hooks.json` is generated from `manifest.json` (`scripts/client_generation.py:150-156`), and `_runner_timeout` at `scripts/client_generation_artifacts.py:135-141` defaults to 1 when `runner_timeout_sec` is absent. The key exists and is already set to 5 on SessionStart and UserPromptSubmit. This is one missing key, not a missing invariant.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `"runner_timeout_sec": 5` is added to the `pr-create` manifest entry and all three client trees are regenerated
- [ ] #2 A test asserts the generated `hooks.json` carries the manifest's declared timeout for every event, so the default can never silently apply again
- [ ] #3 `plan-exit` is reviewed for the same treatment once it fires
<!-- AC:END -->
