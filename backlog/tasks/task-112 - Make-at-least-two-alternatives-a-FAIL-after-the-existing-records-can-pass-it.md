---
id: TASK-112
title: >-
  Make 'at least two alternatives' a FAIL, after the existing records can pass
  it
status: Done
assignee: []
created_date: '2026-08-03 19:35'
updated_date: '2026-08-03 23:19'
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
- [x] #1 The shipped ADRs are audited for the alternatives count and the result is recorded in the task
- [x] #2 Records falling short are repaired before any promotion
- [x] #3 `QUALITY_FEW_ALTERNATIVES` becomes a FAIL under `completeness`, or R0 is amended to say one alternative suffices — with the reason
- [x] #4 A fixture with one alternative fails, and a fixture with two passes
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Promoted to a `completeness` FAIL, in the default gate set.

**The audit came first, as the task required, and it cleared the way.** All 28 records already weigh at least three options, so the set passes on promotion with no repair round. Promoting a gate while the project's own records would fail it is how a gate gets reverted.

**One measurement I got wrong and corrected.** My first probe used a raw regex on literal headings and concluded the check reached only 5 of 28 ADRs. That was wrong: `_section_text` maps the heading to the semantic role, so it was already format-aware. Re-measured through the linter's own code path: 28 of 28 reached, 0 short. The real defect was only the severity and the gate it sat under.

**Two placeholder spellings are exempt, and finding the second is why this was not a one-line change.** Migration deliberately never fabricates alternatives, and says so two ways:

- `/adr-kit:migrate`'s skill writes `<!-- TODO: document at least 2 alternatives ... -->`
- `bin/adr-migrate` writes `- TODO: record the considered options.`

I caught the first and shipped it; the full suite then failed on `test_reported_nygard_path_becomes_strict_clean_after_approved_steps`, which is how the second surfaced. Counting either as a real option fails every honest import the moment it lands — how a migrating team learns to disable the gate, which is the R15 outcome. A real option beside a placeholder still counts as one, so a half-filled section does not pass by accident.

Two fixtures gained a second option because they legitimately should have had one: `bad-filename` exists to trip the filename check, and `with-policy`'s ADR-100 is the post-`strict_from` PASS control, which has to pass every default gate to be a control.

The old `QUALITY_FEW_ALTERNATIVES` advisory is retired rather than kept alongside — two findings for one cause tell an author to fix the same thing twice.

Full suite: 1533 passed, 13 skipped.
<!-- SECTION:FINAL_SUMMARY:END -->
