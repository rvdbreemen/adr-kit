---
id: TASK-119
title: '--no-pre-commit removes the hook rather than skipping it'
status: To Do
assignee: []
created_date: '2026-08-03 22:10'
labels:
  - setup
  - cli
  - ux
dependencies: []
priority: low
ordinal: 4200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found by reaching for the flag on the assumption its name was accurate.

`python scripts/setup-project.py --client claude-code-cli --project-root . --no-pre-commit` prints `disable-pre-commit: .githooks/pre-commit` and **deletes the hook**. The flag reads as "do not install one" and means "remove the one that is there".

That is a destructive act behind a name that promises a non-act. The intended use — set up the instruction layout on a project that manages its git hooks another way, without touching them — is not expressible: every invocation either installs the kit's hook or removes whatever is at that path.

Concretely: a project using husky, lefthook, or a hand-written `pre-commit` gets it deleted by a flag whose name says it will leave things alone. A backup is written, which limits the damage without making the name honest.

Options, roughly in order of preference:

1. Make `--no-pre-commit` mean *skip*, and add `--uninstall-pre-commit` for the removal. Clearest, and a behaviour change for anyone relying on today's meaning.
2. Keep the meaning and rename it `--remove-pre-commit`, with `--no-pre-commit` kept as a deprecated alias that warns.
3. Refuse to remove a hook the kit did not write — the installed wrapper carries `ADR_KIT_WRAPPER_VERSION`, so it is identifiable. Worth doing under either of the above.

Option 3 is the one that closes the actual hole, since the surprising case is not the naming but deleting someone else's file.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `setup-project.py` can write the instruction layout without touching `.githooks/pre-commit` at all
- [ ] #2 Removing a pre-commit hook is expressed by a flag whose name says removal
- [ ] #3 A hook the kit did not write — no `ADR_KIT_WRAPPER_VERSION` stamp — is not removed without an explicit confirmation
- [ ] #4 A test asserts that the skip flag leaves an existing foreign hook byte-identical
<!-- AC:END -->
