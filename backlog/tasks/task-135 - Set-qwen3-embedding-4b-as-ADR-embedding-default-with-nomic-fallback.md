---
id: TASK-135
title: 'Set qwen3-embedding:4b as ADR embedding default with nomic fallback'
status: Done
assignee: []
created_date: '2026-08-04 21:20'
updated_date: '2026-08-04 21:25'
labels:
  - embedding
  - settings
  - retrieval
dependencies: []
modified_files:
  - bin/adr-embed
  - codex/bin/adr-embed
  - bin/adr_embedding_runtime.py
  - codex/bin/adr_embedding_runtime.py
  - schemas/adr-kit-config.schema.json
  - codex/schemas/adr-kit-config.schema.json
  - spec.md
  - tests/test_adr_embedding_runtime.py
  - tests/test_adr_settings.py
priority: medium
ordinal: 107500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make qwen3-embedding:4b the default embedding model for adr-kit while retaining nomic-embed-text as an explicit fallback. Update both source and Codex distribution copies, runtime guidance, tests, and configuration documentation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 bin/adr-embed defaults to qwen3-embedding:4b when embedding.model is unset
- [x] #2 nomic-embed-text remains available only as an explicit fallback or user-selected model
- [x] #3 bin and codex distribution copies remain behaviorally aligned
- [x] #4 Focused embedding/settings tests pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Update defaults and fallback messaging; align tests and docs; run focused tests, ADR lint, and judge
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented qwen3-embedding:4b as the measured default in both native and Codex distribution copies. nomic-embed-text remains the explicit English-only fallback; automatic switching is intentionally avoided because vector identity changes require a rebuild. Focused tests: 63 passed; client/package tests: 20 passed, 1 skipped; strict ADR lint passed; staged ADR judge reported 0 violations and 0 advisories.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
qwen3-embedding:4b is now the adr-kit default. nomic-embed-text remains available as the explicit fallback through the runtime setup route and --model selection. Source/Codex mirrors, schema, spec, and regression tests are aligned.
<!-- SECTION:FINAL_SUMMARY:END -->
