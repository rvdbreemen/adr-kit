---
id: TASK-125
title: >-
  bin/adr-doctor assumes scripts/ and clients/, which the generated client trees
  do not have
status: To Do
assignee: []
created_date: '2026-08-04 05:25'
updated_date: '2026-08-04 23:01'
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
INVESTIGATION 2026-08-05 — one detail in this record is wrong and the task is larger than stated.

WRONG: bin/adr-doctor does NOT extend sys.path with `scripts/` and `clients/`. It appends ROOT and ROOT/"scripts" only (bin/adr-doctor:49-51); `clients.installer.*` resolves as a package under ROOT. The consequence is the same, but a fix written against the stated cause would miss.

REPRODUCED: `python -P codex/bin/adr-doctor --help` raises ModuleNotFoundError: No module named 'adr_settings', from codex/bin/adr_doctor_checks.py:12. Same for copilot. All 25 other extensionless entrypoints were run in both generated trees: adr-doctor is the ONLY failure.

EXACT IMPORT SURFACE (AST sweep of all 26 bin/ files, no others found): bin/adr_doctor_checks.py:12-25 needs adr_settings, client_generation, project_setup, clients.installer.contracts, clients.installer.detection. bin/adr_doctor_probes.py:15-20 needs adr_settings, clients.installer.detection, hooks.hook_benchmark.

LARGER THAN STATED: the import error is only the first of two premise breaks — check_mcp_launcher also assumes the repo layout. And the fix adds 16 new committed files to each mirror, which makes this the only task in the sweep that changes WHICH files are mirrored. Ordering consequence: it must land before the other regeneration-heavy tasks, or every later `--check` diff mixes the real change with sixteen new files appearing.

OPEN DECISION: whether a short Proposed amending ADR is needed. The file-list addition sits inside ADR-010:243 ('generation uses declared bounded input roots'), but the NEW semantic — a generated client tree is a first-class doctor context that reports only its own client and marks the other two 'unsupported' — is not written down anywhere and would otherwise have to be inferred from code.
<!-- SECTION:NOTES:END -->
