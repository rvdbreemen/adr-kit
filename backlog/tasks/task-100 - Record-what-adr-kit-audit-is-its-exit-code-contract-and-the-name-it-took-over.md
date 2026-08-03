---
id: TASK-100
title: >-
  Record what /adr-kit:audit is, its exit-code contract, and the name it took
  over
status: To Do
assignee: []
created_date: '2026-08-03 19:32'
labels:
  - adr
  - cli
  - retrospective
dependencies: []
priority: medium
ordinal: 2200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`bin/adr-audit` means something different than it did a week ago: the init-time discovery scanner moved to `bin/adr-discover`, and the name now belongs to the combined lint-and-judge command of R15. Nothing records that.

The exit codes are a contract CI will lean on, and they exist only as constants in the file: `EXIT_OK=0`, `EXIT_CODE_VIOLATION=1`, `EXIT_TOOLING=2`, `EXIT_ADR_QUALITY=3`, `EXIT_BOTH=4`. The whole point of the split is that "your ADRs are not good enough" and "your code violates an ADR" are different problems with different owners — a single non-zero exit tells the caller nothing about what to fix. A contract that lives only in constants gets collapsed back to 0/1 by the next person who finds it convenient.

Also record the refusal: a bare invocation with no `--whole-codebase` and no `--diff` exits 2 pointing at `bin/adr-discover`, because it used to read closed stdin and report "on course" — a green answer to a question nobody asked.

Spec: R15.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 An ADR states what `/adr-kit:audit` runs, why lint and judge belong in one pass, and why the exit codes are five rather than two
- [ ] #2 The whole-codebase mode is recorded as a diff against the empty tree, with the diff budget that bounds it
- [ ] #3 The rename of the old `adr-audit` to `adr-discover` is recorded, with the ambiguity it removes
- [ ] #4 The refusal of a bare invocation is recorded, including the failure it replaced
- [ ] #5 A test asserts each of the five exit codes on a fixture, so the contract is enforced and not merely described
<!-- AC:END -->
