---
id: TASK-125
title: >-
  bin/adr-doctor assumes scripts/ and clients/, which the generated client trees
  do not have
status: Done
assignee: []
created_date: '2026-08-04 05:25'
updated_date: '2026-08-05 05:43'
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
- [x] #1 bin/adr-doctor runs from codex/ and copilot/ without an import error
- [x] #2 The generated-tree import invariant covers bin/ entrypoints, not only the hook entrypoint
- [x] #3 A test drives the doctor from a generated tree as a subprocess rather than importing its internals
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

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
bin/adr-doctor now runs from codex/ and copilot/, reports only its own client, and never writes into the tree it inspects. ADR-032 records the reporting contract.

RUNTIME_SUPPORT_FILES declares the eight modules bin/ imports from outside bin/ and mirrors them at their own relative paths, because the doctor resolves them by appending ROOT and ROOT/"scripts" to sys.path -- the layout has to match, not just the files. They cannot go in COPY_ROOTS: declared_source_files() rglobs a whole root, which would drag build-client-adapters.py into the mirrors and copy clients/workflows.json there, destroying the marker generated_tree_owner() reads.

Fixing the imports alone would have satisfied AC#1 while leaving the doctor lying in six places: check_mcp_launcher and check_hook_package both computed plugin_root / client, but codex/ IS the plugin root for Codex. client_root() re-roots per client and returns None for the two that are not installed, which report unsupported rather than failed. _generated_check returns before importing the generator, because a mirror has no canonical inputs to diff and repair mode -- the DEFAULT mode -- would otherwise write into the tree under inspection.

Measured after, both mirrors: required_failures 0, generated-adapters unsupported, own client's mcp-launcher and hook-package healthy, other two unsupported. SHA-256 snapshot before and after a repair run plus --fix: zero files changed.

AC#2 is the part that needed the most care. The v0.44.1 invariant scanned one file one hop deep and would have PASSED on this defect. tests/generated_tree_imports.py walks the closure transitively over parsed ASTs, and is verified against BOTH historical outages. Its companion test is what keeps the exclusion honest: a deliberately-absent module is allowed only when every import of it is lazy, otherwise the allowlist would let an eager import reproduce the v0.44.1 outage with a green suite.

Verified: 357 tests pass across the doctor, generation, dispatch-matrix and package suites; build-client-adapters.py --check reports changed=0.
<!-- SECTION:FINAL_SUMMARY:END -->
