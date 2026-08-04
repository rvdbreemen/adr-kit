---
id: TASK-125
title: >-
  bin/adr-doctor assumes scripts/ and clients/, which the generated client trees
  do not have
status: To Do
assignee: []
created_date: '2026-08-04 05:25'
labels:
  - doctor
  - client-generation
  - mirrors
dependencies: []
priority: high
ordinal: 104500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`bin/adr-doctor` extends `sys.path` with `scripts/` and `clients/` relative to its own location. Neither directory is in `COPY_ROOTS`, so neither exists in `codex/` or `copilot/`. Running the doctor from a generated tree fails at import.

This is the same class of defect as the v0.44.1 hotfix, where `hooks/adr_pr_guard.py` was undeclared and every mirrored hook died at import. The fix there was an invariant test -- every module the generated entrypoint imports must resolve inside that client's tree -- rather than a longer file list. Extend that invariant to cover `bin/` entrypoints, so the next undeclared dependency is caught by the gate.

Then decide the actual fix: either declare the directories the doctor needs, or make the doctor degrade honestly when they are absent instead of raising.

Evidence: `sys.path` setup in `bin/adr-doctor`; `COPY_ROOTS` in `scripts/client_generation_model.py`; absence of `codex/scripts/` and `codex/clients/`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 bin/adr-doctor runs from codex/ and copilot/ without an import error
- [ ] #2 The generated-tree import invariant covers bin/ entrypoints, not only the hook entrypoint
- [ ] #3 A test drives the doctor from a generated tree as a subprocess rather than importing its internals
<!-- AC:END -->
