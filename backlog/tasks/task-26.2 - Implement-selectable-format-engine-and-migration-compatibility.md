---
id: TASK-26.2
title: Implement selectable format engine and migration compatibility
status: Done
assignee:
  - Codex
created_date: '2026-07-18 15:34'
updated_date: '2026-07-18 16:13'
labels:
  - engine
  - templates
  - migration
dependencies:
  - TASK-26.1
documentation:
  - schemas/adr-kit-config.schema.json
  - templates/adr-template.md
modified_files:
  - bin/
  - schemas/
  - templates/
  - tests/test_selectable_formats.py
  - tests/test_python_compatibility.py
parent_task_id: TASK-26
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the approved ADR-format strategy in the canonical engines and schemas. Add deterministic format selection and rendering while preserving machine-readable metadata, status history, Enforcement blocks, migration safety, and backwards compatibility for existing canonical ADRs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Configuration schema validates every supported format and defines an explicit default and unsupported-format error path.
- [x] #2 ADR proposal, lifecycle, lint, index, context, judge, related, retire, doctor, and migration workflows use a shared format model rather than divergent heading assumptions.
- [x] #3 Every supported format has a deterministic template and fixtures covering create, parse, mutate, index, enforce, and migrate behavior.
- [x] #4 Existing adr-kit canonical ADRs remain valid or have a documented, tested migration path with dry-run and idempotency guarantees.
- [x] #5 Python/runtime compatibility and malformed/hybrid document behavior are covered by focused tests.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
After TASK-26.1: inspect all heading-dependent engines and current profile tests; implement a shared semantic profile registry and config validation; add deterministic templates/rendering and profile-aware parsing/mutation; preserve legacy records and invariant metadata; extend migration with dry-run/idempotency; add focused fixtures/tests for all supported, unsupported, and hybrid cases; run focused verification before advancing.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementation started after TASK-26.1 completion. Shared semantic registry, templates, config selection, `adr new`, migration, and profile-aware engine paths are implemented; initial cross-engine focused slice is 197 passed.

Completed shared profile engine and focused verification. MADR, Nygard, and canonical now share semantic roles across creation, lifecycle mutation, lint, quality, index, context, judge, related, retire, doctor, audit, migration, suggestion, and watch paths. Conversion rejects conflicting source declarations, preserves invariant content, supports all nine source/target pairs, and inserts explicit extension placeholders where a target requires missing structure. Focused engine/client slice: 220 passed; compatibility/profile/client slice: 36 passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented the selectable-format engine with MADR as the default and Nygard/canonical as supported profiles. Added shared semantic parsing, deterministic templates, profile-aware creation and lifecycle mutation, strict malformed/hybrid handling, dry-run/idempotent all-pairs migration, real Enforcement coverage, and Python 3.10 syntax/runtime-floor tests. Focused verification passed.
<!-- SECTION:FINAL_SUMMARY:END -->
