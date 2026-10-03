---
id: TASK-202
title: A migration-created Related Decisions section is never reported as unwritten
status: In Progress
assignee: []
created_date: '2026-09-06 15:11'
updated_date: '2026-10-03 15:40'
labels:
  - migrate
  - question
dependencies: []
priority: low
ordinal: 46000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
bin/adr_format.py::_append_missing_role writes the literal '- None.' for the 'related' role, unlike every other role which gets a '- TODO: ...' line. That is deliberate and correct as content ('nothing relates to this' is a statement, not a hole), and the placeholder detector correctly leaves it alone, verified by a test added in TASK-199.

The open question is whether it should be reported at migrate time. Measured during TASK-199: converting an ADR that lacked Alternatives, Related and References adds all three sections, and the operator is told about two. Nobody ever wrote the Related Decisions section, and nothing says so.

Both readings are defensible: '- None.' is a real answer that happens to have been written by a machine, or it is a machine guessing on the author's behalf about a section the author never saw. This needs a decision before it needs code, which is why it is filed rather than fixed.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A decision is recorded on whether a machine-written '- None.' counts as the author's answer
- [x] #2 If it does not, adr-migrate names it alongside the other sections it filled, and the placeholder detector still leaves a hand-written '- None.' alone
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Decision (maintainer, 2026-10-03): a '- None.' written by the migration does NOT count as the author's answer. Reason: the author never saw the section, so the line is a machine's guess on their behalf. It is reported for review, not as a hole: the line is true in most records, and the placeholder detector must keep treating a hand-written '- None.' as content (test_the_related_decisions_none_line_stays_real_content is unchanged).

Reproduced 2026-10-03: canonical record without Related Decisions, migrate --to-profile canonical, output silent about the added section. Fix: adr-migrate records machine_written_sections when the source lacked the related role and the result has it, and prints 'review: ## Related Decisions (written as '- None.' by the migration; confirm it, or name the related ADRs)'. Tests: test_a_machine_written_related_section_is_named_for_review (fails before, passes after) and test_a_hand_written_related_none_is_not_named; tests/test_selectable_formats.py 37 passed.
<!-- SECTION:NOTES:END -->
