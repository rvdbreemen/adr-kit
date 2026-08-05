---
id: TASK-121
title: >-
  The pre-commit template hardcodes 5000 ms instead of reading
  pre_commit_timeout_ms
status: Done
assignee: []
created_date: '2026-08-04 05:25'
updated_date: '2026-08-05 06:10'
labels:
  - hooks
  - config
  - consistency
dependencies: []
priority: medium
ordinal: 100500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`templates/githooks/pre-commit` line 214 uses a literal `5000` for its timeout while `pre_commit_timeout_ms` exists as a configurable key. Setting the key changes nothing.

Same shape as the `JUDGE_TIMEOUT_S = 120` defect fixed in v0.44.1: a bound declared in config and contradicted by a constant in code, with nothing forcing agreement. This one is in the file every installed project copies, so the divergence ships to every user.

Read the key, fall back to 5000 when it is absent, and bound it the way the guard bounds `runner_timeout_sec` -- a hand-edited value from a repo-tracked file gets validated, not trusted.

Evidence: `templates/githooks/pre-commit:214`; `pre_commit_timeout_ms` in `schemas/adr-kit-config.schema.json`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The template resolves pre_commit_timeout_ms and only falls back to a constant when the key is absent
- [x] #2 A value outside a sane range is refused rather than adopted
- [x] #3 A test drives the template with a configured value and observes the timeout it actually applies
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The template resolves judge.pre_commit_timeout_ms, validates it, and applies it. Previously the threshold was a literal 5000 and the key changed nothing.

AC#1 -- absent falls back to 5000, the schema default. 0 means off, matching how bin/adr-judge:2876 already reads it, so the shell does not invent a second meaning.

AC#2 -- anything outside 0..3600000 is refused with a named message on stderr and the default applied. The ceiling is an hour rather than something tighter because judge.llm_timeout_seconds bounds ONE call and one call runs per llm_judge ADR: a ten-ADR project has a legitimate twenty-minute commit, and a lower ceiling would refuse a correct config.

Also honours judge.warn_on_exceed, which was not in the criteria but shipping without it would have reproduced the identical defect one key over -- a user setting warn_on_exceed:false would still have got the WARN.

AC#3 -- tests/test_pre_commit_budget.py drives the actual shell block and observes the threshold it resolves, rather than asserting on the template source. Twelve tests including the state machine, warn_on_exceed, and a malformed config (set -e is live at that point, so an unguarded read would abort the commit).

Three Windows platform details were needed and are commented in the test: bash gets the script by relative path with cwd set (a native path arrives mangled, and /c/... assumes a drive mount the Git usr/bin/bash does not have), the script is written as bytes with explicit LF, and the interpreter resolves from PATH inside the shell.

`True` is in the invalid-value parametrisation deliberately: bool subclasses int in Python, so a naive isinstance check would accept `true` as 1 ms.
<!-- SECTION:FINAL_SUMMARY:END -->
