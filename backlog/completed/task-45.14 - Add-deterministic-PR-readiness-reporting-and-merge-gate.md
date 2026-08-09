---
id: TASK-45.14
title: Add deterministic PR readiness reporting and merge gate
status: Done
assignee:
  - Codex
created_date: '2026-07-20 19:53'
updated_date: '2026-07-20 21:57'
labels:
  - feature
  - adr-grilling
  - ci
  - github-actions
  - performance
milestone: ADR Grilling
dependencies:
  - TASK-45.4
  - TASK-45.5
  - TASK-45.8
documentation:
  - docs/feature-adr-grilling/02-lifecycle-analysis.md
  - docs/feature-adr-grilling/03-solution-design.md
  - docs/feature-adr-grilling/04-implementation-plan.md
  - docs/feature-adr-grilling/05-validation-plan.md
modified_files:
  - bin/adr-readiness-ci
  - bin/adr_readiness_ci.py
  - .github/actions/adr-readiness/action.yml
  - .github/workflows/adr-readiness.yml
  - templates/github-workflows/adr-readiness.yml
  - tests/test_adr_readiness_ci.py
  - scripts/benchmark-adr-grilling.py
  - docs/feature-adr-grilling/06-benchmark-report.md
  - README.md
parent_task_id: TASK-45
priority: high
ordinal: 46400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add a model-free pull request readiness action that analyzes the diff, publishes a GitHub Step Summary and safe annotations, and exposes machine-readable outputs. Keep suspected undocumented decisions advisory and fail only when explicit evidence proves the pull request implements a linked Proposed ADR.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The pull request integration publishes GitHub Step Summary, escaped notice or warning annotations, and documented machine-readable outputs.
- [x] #2 The integration posts no automatic PR comment and requires no model, API key, secret, or hosted analysis service.
- [x] #3 A suspected undocumented architecture decision produces a successful advisory check.
- [x] #4 The check fails only when deterministic evidence proves that the pull request implements an explicitly linked Proposed ADR.
- [x] #5 Accepted, Rejected, Superseded, and non-implemented Proposed ADRs do not produce an incorrect block.
- [x] #6 Every advisory or blocking result includes its evidence, readiness classification, and an exact /adr-kit:grill command.
- [x] #7 Analysis and infrastructure failures are reported separately from architecture findings.
- [x] #8 Fork pull requests, shallow clones, detached HEAD, missing base refs, multiple linked ADRs, and untrusted output content have fixtures.
- [x] #9 Action overhead excluding checkout and runtime installation has p95 no greater than five seconds on the standard 500-path and 50-ADR fixture.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add a model-free composite PR action over one base/head readiness report. 2. Render safe Step Summary/annotations and stable single-line machine outputs without PR comments or secrets. 3. Exit 1 only for deterministic linked-and-implemented Proposed ADRs; keep suspected decisions advisory and infrastructure failures distinct at exit 2. 4. Cover statuses, fork/shallow/missing-ref/multiple-link/injection fixtures and certify 500-path/50-ADR overhead.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Validation: `python -m pytest tests/test_adr_readiness.py tests/test_adr_readiness_ci.py -q` -> 29 passed, including exact-SHA fork-style detached HEAD, two-commit shallow clone, missing ref, multiple Proposed links, status matrix, output injection and escaping. Thirty-sample 500-distinct-path/50-ADR action benchmark: p50 911.954 ms, p95 1,150.890 ms, max 1,619.274 ms against p95 5,000 ms. Action is key/model/secret/comment free; exit 1 is limited to explicitly linked implemented Proposed ADRs and exit 2 is infrastructure.

Self-dogfood workflow added for pull requests targeting the new default `dev` branch or protected `main`; the downstream template remains branch-neutral. The static action test verifies the local composite action wiring.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Delivered a model-free composite PR readiness action with safe summaries, annotations, and machine outputs. It uses exact base/head commits, keeps suspected decisions advisory, blocks only explicit implementation links to Proposed ADRs, and remains well below its five-second budget.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Composite action and workflow fixtures cover every status and linkage combination.
- [x] #2 GitHub escaping, fork safety, output contracts, and performance evidence are recorded.
- [x] #3 Downstream configuration documentation, modified files, exact validation commands, and results are recorded.
<!-- DOD:END -->
