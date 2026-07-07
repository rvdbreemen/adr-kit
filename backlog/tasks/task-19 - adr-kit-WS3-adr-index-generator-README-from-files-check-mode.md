---
id: TASK-19
title: 'adr-kit WS3: ''adr index'' generator (README from files, --check mode)'
status: Done
assignee:
  - Codex
created_date: '2026-07-06 19:54'
updated_date: '2026-07-06 20:16'
labels:
  - adr-kit
  - governance
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The hand-maintained index rotted (19 missing, 12 stale labels, a dup, wrong counts). Generate entries/status markers/supersession notes/per-topic counts from the ADR files. 'adr index --check' exits non-zero on drift (CI/pre-commit assertion). Human prose preserved via sentinels; tool owns only generated tables. Full plan: docs/plan/adr-kit-governance-plan.md. Repo: adr-kit.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 adr index reproduces a correct README: zero missing ADRs, no duplicate, correct counts
- [x] #2 adr index --check green immediately after generation; idempotent
- [x] #3 Human narrative sections preserved via sentinels
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Implementation plan for TASK-19:
1. Add a stdlib-only bin/adr-index CLI that reads ADR files and canonical frontmatter, builds deterministic index rows, status counts, and supersession notes.
2. Use sentinel markers in docs/adr/README.md so generated content can be replaced idempotently while preserving human prose before/after the generated block.
3. Support --check for CI: exit 1 if README is missing or stale, exit 0 immediately after generation, and emit JSON/text summaries.
4. Detect duplicate ADR ids while indexing and report them in JSON/text; generated output must include every ADR exactly once.
5. Generate this repo's docs/adr/README.md from the current ADR set and verify --check is green.
6. Add focused tests for initial generation, idempotent --check, stale README detection, duplicate reporting, and human prose preservation.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Moved from OTGW-firmware TASK-1007 because this is adr-kit repo work.

Implemented bin/adr-index. The CLI reads local ADR files/frontmatter, generates deterministic status counts and decision rows, reports duplicate ADR ids, and owns only the sentinel-delimited block in docs/adr/README.md. Existing human prose outside <!-- adr-kit-index:begin --> / <!-- adr-kit-index:end --> is preserved. Added --check and JSON/text output for CI.

Generated this repo's docs/adr/README.md. Verification:
- python -m pytest tests/test_adr_index.py -q -> 4 passed
- python -m pytest tests/test_adr_index.py tests/test_adr_migrate.py tests/test_adr_lint_governance.py -q -> 15 passed
- python bin/adr-index --check docs/adr -> changed=False, duplicates=0
- python bin/adr-index --check --format json docs/adr -> total=3, duplicates=0, changed=false
- python -m pytest tests/test_adr_index.py tests/test_adr_migrate.py tests/test_adr_lint.py tests/test_adr_lint_supersession.py tests/test_adr_lint_governance.py tests/test_adr_policy.py tests/test_adr_context.py -q -> 66 passed
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added a local ADR README index generator. bin/adr-index builds a deterministic generated block from ADR metadata, detects duplicate ids, preserves human prose outside sentinels, and supports --check for CI/pre-commit drift detection. Generated docs/adr/README.md for this repo and documented the command in README.

Tests: index tests and the focused migration/lint/governance/policy/context regression slice pass; adr-index --check docs/adr is clean.
<!-- SECTION:FINAL_SUMMARY:END -->
