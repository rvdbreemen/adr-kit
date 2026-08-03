---
id: TASK-112
title: >-
  Make 'at least two alternatives' a FAIL, after the existing records can pass
  it
status: To Do
assignee: []
created_date: '2026-08-03 19:35'
labels:
  - lint
  - adr
dependencies:
  - TASK-111
priority: low
ordinal: 3900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
R0 states that an ADR carries the alternatives that were weighed and why they lost, because a record that states only the outcome cannot be re-evaluated later — and a decision that cannot be re-evaluated cannot be superseded honestly.

The lint does not guarantee that. `## Alternatives Considered` is a required section (`bin/adr-lint:147-154`), but the count check `QUALITY_FEW_ALTERNATIVES` is `"severity": "ADVISORY"` under gate `quality` (`bin/adr-lint:1287-1300`). A record naming one option and no rejected alternative passes every FAIL gate.

Order matters: audit the shipped ADRs for the count first and repair what falls short, then promote. Promoting while this repository's own set would fail is how a gate gets reverted. Shares its repair step with TASK-111.

If one alternative turns out to be genuinely acceptable for some class of decision, say so in `spec.md` R0 and close this without code — that is a legitimate outcome, not a failure to deliver.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The shipped ADRs are audited for the alternatives count and the result is recorded in the task
- [ ] #2 Records falling short are repaired before any promotion
- [ ] #3 `QUALITY_FEW_ALTERNATIVES` becomes a FAIL under `completeness`, or R0 is amended to say one alternative suffices — with the reason
- [ ] #4 A fixture with one alternative fails, and a fixture with two passes
<!-- AC:END -->
