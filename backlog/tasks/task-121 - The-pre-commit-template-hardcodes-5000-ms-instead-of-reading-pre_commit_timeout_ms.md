---
id: TASK-121
title: >-
  The pre-commit template hardcodes 5000 ms instead of reading
  pre_commit_timeout_ms
status: To Do
assignee: []
created_date: '2026-08-04 05:25'
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
- [ ] #1 The template resolves pre_commit_timeout_ms and only falls back to a constant when the key is absent
- [ ] #2 A value outside a sane range is refused rather than adopted
- [ ] #3 A test drives the template with a configured value and observes the timeout it actually applies
<!-- AC:END -->
