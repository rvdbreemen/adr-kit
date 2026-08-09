---
id: TASK-32.1
title: Fail closed on invalid judge config and oversized diffs
status: Done
assignee:
  - Codex
created_date: '2026-07-18 19:52'
updated_date: '2026-07-18 19:57'
labels:
  - security
  - adr-judge
  - F-02
  - F-03
dependencies: []
references:
  - docs/reviews/2026-07-18-source-audit/FINDINGS.md
modified_files:
  - bin/adr_config.py
  - bin/adr-judge
  - bin/adr-suggest
  - schemas/adr-kit-config.schema.json
  - tests/test_adr_runtime_config.py
parent_task_id: TASK-32
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Resolve source-audit F-02 and F-03 by validating runtime configuration types and bounds before use and making oversized diffs fail closed with an actionable result instead of skipping enforcement successfully.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Invalid booleans, nulls, negative sizes, wrong container types, and unknown config keys cannot weaken enforcement or enable LLM execution.
- [x] #2 Oversized non-empty diffs cannot exit successfully without deterministic enforcement.
- [x] #3 Valid configuration remains backward compatible and schema-driven.
- [x] #4 Focused config and large-diff regression tests pass.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented a shared stdlib-only JSON Schema subset validator driven by `schemas/adr-kit-config.schema.json`. Runtime judge/suggest configuration now rejects wrong booleans, nulls, negative limits, wrong containers, nested and top-level unknown keys (while retaining underscore-prefixed annotations), before enforcement or LLM resolution.

Oversized diffs now use exact UTF-8 byte size and exit 2 with an actionable fail-closed error instead of returning success without enforcement. Focused verification: 76 affected judge/suggest/performance tests passed; final warning-free runtime configuration slice: 11 passed; Python compilation passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Resolved F-02 and F-03. Runtime configuration is schema-validated without an optional dependency, string values can no longer become truthy enforcement or LLM switches, numeric bounds are enforced, and oversized diffs fail closed rather than bypassing ADR enforcement.
<!-- SECTION:FINAL_SUMMARY:END -->
