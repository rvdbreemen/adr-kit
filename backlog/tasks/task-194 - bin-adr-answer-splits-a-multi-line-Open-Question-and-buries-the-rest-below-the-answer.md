---
id: TASK-194
title: >-
  bin/adr answer splits a multi-line Open Question and buries the rest below the
  answer
status: To Do
assignee: []
created_date: '2026-08-26 20:25'
labels: []
dependencies: []
references:
  - docs/adr/ADR-022-make-open-questions-append-only-for-a-proposed-adr.md
  - >-
    docs/adr/ADR-042-drive-the-release-from-the-maintainer-s-machine-and-create-the-tag-from-the-merge.md
priority: low
type: bug
ordinal: 38000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`bin/adr answer` appends the answer after the FIRST line of the question, so the remaining lines of a multi-line Open Question end up printed below the answer as orphaned prose. The record stays readable but the reading order is wrong: a reader meets the answer before they have finished the question.

OBSERVED 2026-08-26 on ADR-042, which had one Open Question spanning ten lines. After `python bin/adr answer ADR-042 --question 1 --answer "..."` the section renders as:

```
- [x] Does npm's Trusted Publisher relationship survive the publish job being — **Answered 2026-08-26 by User: Robert van den Breemen:** No. npm validates the CALLING workflow's filename ... no reusable-workflow refactor is needed.
  invoked through `workflow_call`? npm matches the trust relationship against
  the workflow filename that *initiates* the run, and it is configured for
  `release-publish.yml` (`docs/RELEASING.md:256-266`). If `release-tag.yml`
  ...
```

The truncation is also visible in the command's own confirmation line, which echoed `Does npm's Trusted Publisher relationship survive the publish job bein` - cut mid-word at what looks like a fixed width.

WHY THIS IS WORTH FIXING RATHER THAN LIVING WITH. ADR-022 makes Open Questions append-only precisely so the reasoning survives for a future reader deciding whether to re-open a decision. That reader is the one this defect hurts: they see a checked item, an answer, and then several lines of unattributed text that read like a continuation of the answer while they are actually the second half of the question. The append-only rule also means it cannot be repaired by hand afterwards without violating the rule the tool exists to protect.

A single-line question is unaffected, which is probably why it has not surfaced: most Open Questions are one line.

NOT INVESTIGATED: whether the same truncation affects `bin/adr reject` or any other lifecycle command that echoes question text, and whether the answer is stored correctly in the generated indexes even though the Markdown renders oddly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Answering a multi-line Open Question keeps the whole question together and places the answer after all of it
- [ ] #2 The command's confirmation output does not truncate the question mid-word
- [ ] #3 A regression test covers a question of at least three lines and asserts the answer follows the complete question text
- [ ] #4 ADR-042's answered question is reflowed as part of the fix, since the append-only rule forbids repairing it by hand
- [ ] #5 python -m pytest -q passes
<!-- AC:END -->
