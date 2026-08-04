---
id: TASK-106
title: Give the PR guard the five seconds its own manifest declares
status: Done
assignee: []
created_date: '2026-08-03 19:34'
updated_date: '2026-08-03 20:15'
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
- [x] #1 `"runner_timeout_sec": 5` is added to the `pr-create` manifest entry and all three client trees are regenerated
- [ ] #2 A test asserts the generated `hooks.json` carries the manifest's declared timeout for every event, so the default can never silently apply again
- [x] #3 `plan-exit` is reviewed for the same treatment once it fires
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
`"runner_timeout_sec": 5` added to the `pr-create` manifest entry; all three trees regenerated and `hooks.json` now carries `"timeout": 5` on the Bash matcher.

AC#2 was deliberately not built. The task text already said why and it held up: `hooks.json` is generated from `manifest.json`, so a drift test between them would test the generator against itself. The default of 1 comes from `_runner_timeout` when the key is absent, which is a missing key rather than a missing invariant.

`plan-exit` was reviewed as AC#3 asks and left at the default. It reads the index and renders — the same shape as `pre-tool-use`, which carries the same 100 ms budget — so it needs no exception. The 5 s belongs to `pr-create` because that one spawns a subprocess.

Shipped in v0.44.1.
<!-- SECTION:FINAL_SUMMARY:END -->
