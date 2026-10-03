---
id: TASK-194
title: >-
  bin/adr answer splits a multi-line Open Question and buries the rest below the
  answer
status: In Progress
assignee: []
created_date: '2026-08-26 20:25'
updated_date: '2026-10-03 14:17'
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
- [x] #1 Answering a multi-line Open Question keeps the whole question together and places the answer after all of it
- [x] #2 The command's confirmation output does not truncate the question mid-word
- [x] #3 A regression test covers a question of at least three lines and asserts the answer follows the complete question text
- [x] #4 ADR-042's answered question is reflowed as part of the fix, since the append-only rule forbids repairing it by hand
- [ ] #5 python -m pytest -q passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reproduced 2026-10-03 with a three-question fixture (wrapped, wrapped with a '?' continuation, nested bullets). The recorded cause is correct but incomplete, and the severity is understated. (1) Deadlock: a continuation line ending in '?' counted as an open question (adr_format.unresolved_open_questions) that answer could not target, so accept stayed blocked after every question was answered. (2) Nested bullets counted as separate questions. (3) --question <text> searched the first line only. (4) The truncated echo is a separate cause: fixed [:70]/[:60] slices. The two parsers also disagreed on the count (5 vs 6).

Fix: one helper, adr_format.open_question_items, groups the section into items (a top-level bullet plus indented lines, nested bullets and lazy continuations; a paragraph counts only if a line ends in '?'). It is used by command_answer, unresolved_open_questions and all_open_questions. Single-line answers keep the one-line form; a multi-line question gets '  — **Answered …**' on a new line after its last line. Identity (ADR-022 append-only) stays _normalise_question over the joined text, so answered and unanswered forms match. The echo cuts at a word boundary. Own ADRs: readiness output byte-identical before and after, and lint is clean. Tests: tests/test_adr_answer_multiline.py (7) plus the related suites, 122 passed.

Not changed: answer rewrites CRLF files to LF, like the other lifecycle writers (seen in the reproduction).

AC#4: ADR-042's answered question was reflowed by script. The answer moved from the end of line 1 to a new line after the question's last line, and the word multiset was asserted unchanged. The question identity changes from the truncated 'Does ... being' (an artefact of the old layout) to the whole question. The ADR-022 append-only guard does not apply because ADR-042 is Accepted. adr-lint over docs/adr is clean; single-file strict lint gives the same 5 findings before and after (directory-context artefacts); judge OK; the index check finds no artefact change.
<!-- SECTION:NOTES:END -->
