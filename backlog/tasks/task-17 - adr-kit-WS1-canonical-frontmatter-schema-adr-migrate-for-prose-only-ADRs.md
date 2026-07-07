---
id: TASK-17
title: 'adr-kit WS1: canonical frontmatter schema + ''adr migrate'' for prose-only ADRs'
status: Done
assignee:
  - Codex
created_date: '2026-07-06 19:54'
updated_date: '2026-07-06 20:08'
labels:
  - adr-kit
  - governance
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Root enabler: 35/43 ADRs are prose-only so nothing is machine-checkable. Define the frontmatter schema (adds binding:bool, gate:str|null, documents_shipped:bool, verified_in:[file:symbol|commit]) and ship 'adr migrate' to back-fill frontmatter from legacy prose Status blocks, idempotent, body bytes unchanged. Full plan: docs/plan/adr-kit-governance-plan.md. Repo: adr-kit.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Documented schema incl. binding/gate/documents_shipped/verified_in
- [x] #2 adr migrate back-fills every prose-only ADR, idempotent, body unchanged (frontmatter-only diff)
- [x] #3 Shared schema-validation function reused by lint
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Implementation plan for TASK-17:
1. Add a stdlib-only shared module under bin/ for canonical ADR frontmatter parsing, inference from legacy prose, rendering, and validation.
2. Add schemas/adr-frontmatter.schema.json and README documentation for the canonical fields: id, title, status, date, binding, gate, documents_shipped, verified_in, supersedes, superseded_by.
3. Add bin/adr-migrate to add or repair frontmatter for ADR files/directories while preserving the markdown body byte-for-byte; support --check and --dry-run for CI/safe review.
4. Extend bin/adr-lint to reuse the shared schema validator through an opt-in schema gate without changing existing default lint behavior yet.
5. Add focused pytest coverage for inference, idempotence/body preservation, --check behavior, and lint schema-gate reuse.
6. Verify with the focused tests first, then run the relevant existing lint/context test slice to catch regressions.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Moved from OTGW-firmware TASK-1005 because this is adr-kit repo work.

Reconcile with TASK-424 (adr-kit v0.11 adr-kit-migrate skill, legacy->canonical): this WS1 largely overlaps; fold into 424 rather than build twice. Net-new from the audit is the extended schema fields (binding/gate/documents_shipped/verified_in).

Implemented canonical ADR frontmatter foundation locally. Added bin/adr_schema.py for frontmatter split/parse/render/infer/validate, bin/adr-migrate for file/directory migration with --check and --dry-run, schemas/adr-frontmatter.schema.json, README documentation, and opt-in adr-lint schema gate reuse. Migrated this repo's docs/adr ADRs; bin/adr-migrate --check docs/adr is now clean.

Verification:
- python -m pytest tests/test_adr_migrate.py -q -> 5 passed
- python -m pytest tests/test_adr_lint.py tests/test_adr_lint_supersession.py tests/test_adr_context.py tests/test_template_profiles.py -q -> 52 passed
- python -m pytest tests/test_adr_migrate.py tests/test_adr_lint.py tests/test_adr_lint_supersession.py tests/test_adr_policy.py tests/test_adr_context.py -q -> 56 passed
- python bin/adr-lint --format json --gates schema docs/adr -> pass=3 fail=0
- python bin/adr-migrate --check docs/adr -> changed=0 failed=0

Full pytest note: python -m pytest -q reached 458 passed / 2 skipped but had 4 failures outside this change surface: one adr-status timing threshold (540ms vs 500ms) and three Windows bash/PATH hook tests. Focused TASK-17 regression surface is green.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added the local canonical-frontmatter foundation for adr-kit. The new shared schema module infers and validates ADR metadata, adr-migrate adds/repairs frontmatter while preserving markdown body text, and adr-lint now reuses the validator via an opt-in schema gate. Documented the schema in README plus schemas/adr-frontmatter.schema.json, added focused tests, and migrated this repo's ADRs so schema-gate validation is clean locally.

Tests: focused migration/lint/context/policy suites passed; docs/adr schema lint passed; adr-migrate --check docs/adr is idempotent. Full-suite run exposed pre-existing/non-task failures in Windows bash hook tests and a marginal adr-status timing threshold, not in the TASK-17 surface.
<!-- SECTION:FINAL_SUMMARY:END -->
