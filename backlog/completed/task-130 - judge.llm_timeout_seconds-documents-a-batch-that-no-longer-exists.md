---
id: TASK-130
title: judge.llm_timeout_seconds documents a batch that no longer exists
status: Done
assignee: []
created_date: '2026-08-04 05:24'
updated_date: '2026-08-05 05:58'
labels:
  - judge
  - config
  - docs
dependencies: []
priority: high
ordinal: 98500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The config schema describes `judge.llm_timeout_seconds` as the timeout for "one batch call". Per-ADR isolation replaced batching (see `.claude/adr-kit-guide.md`, "Each `llm_judge` ADR gets its own isolated call"), so the field now bounds each call in a loop.

Consequence with the shipped default of 120 s: a project with 20 `llm_judge: true` ADRs has a worst case of 20 x 120 s = 40 minutes on a single `git commit`, and the description tells the reader it is two minutes total. That is not a wording nit; it is the number someone uses to decide whether the pass is affordable.

Fix the schema description, and decide whether the field should stay per-call or become a whole-pass budget spent down across the loop (the `Deadline` pattern now in `hooks/adr_pr_guard.py` is the working example).

Evidence: `schemas/adr-kit-config.schema.json`, the per-ADR loop in `bin/adr-judge`, `.claude/adr-kit-guide.md` cost-shape section.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The schema description matches the per-ADR loop that actually runs
- [x] #2 The worst-case wall clock for a realistic ADR count is stated where a user chooses the value
- [ ] #3 If the field becomes a whole-pass budget, a test proves the loop stops when it is spent
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The schema description now matches the per-ADR loop that actually runs, and states the worst case where someone chooses the value.

AC#1 -- judge.llm_timeout_seconds is described as the hard timeout for each individual LLM judge call, with per-ADR isolation meaning one call runs per ADR marked llm_judge.

AC#2 -- the description states the worst case for realistic ADR counts: at the shipped 120 s default, 10 ADRs is a 20-minute worst case and 20 ADRs is 40 minutes on a single commit. The old text said "one batch call", which read as two minutes total.

AC#3 -- NOT done, and deliberately so. Converting the field into a whole-pass budget spent down across the loop (the Deadline pattern in hooks/adr_pr_guard.py is the working example) changes commit-time behaviour for every user with more than one llm_judge ADR: a pass that completes today would start being cut short. That is a behavioural change rather than a documentation fix, and it belongs in its own task with its own decision. The description is now honest about what the field does, which is what made the number dangerous.
<!-- SECTION:FINAL_SUMMARY:END -->
