---
id: TASK-202
title: A migration-created Related Decisions section is never reported as unwritten
status: To Do
assignee: []
created_date: '2026-09-06 15:11'
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
- [ ] #1 A decision is recorded on whether a machine-written '- None.' counts as the author's answer
- [ ] #2 If it does not, adr-migrate names it alongside the other sections it filled, and the placeholder detector still leaves a hand-written '- None.' alone
<!-- AC:END -->
