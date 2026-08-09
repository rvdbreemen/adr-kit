---
id: TASK-52.4
title: Integrate index-first retrieval with adr-context and MCP
status: Done
assignee:
  - Codex
created_date: '2026-07-23 17:44'
updated_date: '2026-07-23 19:02'
labels:
  - adr
  - cli
  - mcp
  - compatibility
milestone: Index-first ADR retrieval
dependencies:
  - TASK-52.3
references:
  - TASK-52
  - bin/adr-context
  - bin/adr-mcp
documentation:
  - README.md
  - skills/context/SKILL.md
modified_files:
  - bin/adr_query.py
  - bin/adr-context
  - bin/adr-mcp
  - schemas/adr-kit-config.schema.json
  - tests/test_adr_query.py
  - tests/test_adr_mcp.py
  - codex/bin/adr_query.py
  - codex/bin/adr-context
  - codex/bin/adr-mcp
  - codex/schemas/adr-kit-config.schema.json
  - copilot/bin/adr_query.py
  - copilot/bin/adr-context
  - copilot/bin/adr-mcp
  - copilot/schemas/adr-kit-config.schema.json
parent_task_id: TASK-52
priority: high
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Expose the shared query outcome consistently through the adr-context command and the key-free MCP server while retaining a compatible result surface and adding explicit path, component, symbol, authority, engine, and historical-context controls.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 CLI and MCP queries return the same ranked ADR ids, authority labels, match explanations, source paths, and compatibility fields for equivalent inputs.
- [x] #2 Callers can provide task text plus optional paths, components, symbols, lifecycle filters, result limit, and historical-context intent.
- [x] #3 Existing consumers retain their documented fields during the compatibility window and can identify whether results came from the index engine or Markdown fallback.
- [x] #4 No-result, invalid-input, missing-index, stale-index, future-schema, Windows-path, and timeout behavior is explicit and tested.
- [x] #5 The MCP surface remains local, stdlib-only, key-free, read-only, bounded, and safe across configured project roots.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Inspect the existing shared query module, adr-context compatibility surface, MCP tool schema, root validation, and timeout/error handling. 2. Route both CLI and MCP through one query request/outcome contract, exposing task text, paths, components, symbols, topics, authority/lifecycle filters, limit, strict-index, and historical intent while preserving legacy result fields. 3. Make source engine/fallback state and invalid/no-result/index errors explicit and bounded, with safe absolute project-root handling on Windows and POSIX. 4. Add parity and edge-case tests for CLI/MCP ranking, compatibility, fallback, future schemas, stale indexes, Windows paths, and timeouts. 5. Synchronize generated clients and finalize only after focused MCP/context tests and adapter checks pass.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan approved by the user's instruction to drain every TASK-52 subtask; TASK-52.4 starts first because TASK-52.3 is Done and TASK-52.5 depends on this integration.

Implemented shared CLI/MCP query controls for repeated paths, components, symbols, topics, lifecycle statuses, authorities, history intent, strict-index, limit, and min-score. Result compatibility fields are preserved while `source`, `engine`, `authority`, `role`, and explained matches make retrieval behavior explicit.

Hardened per-call MCP workspace resolution: caller-supplied project roots must be absolute, ADR directories must remain inside the selected project root, arrays and numeric inputs are bounded, and the existing 60-second subprocess timeout returns a stable tool error. Historical retrieval remains explicit opt-in.

Verification: 75 query/context/MCP tests passed with 2 opt-in performance tests skipped; 31 client-adapter/native-package/capability/config tests passed; generated adapters report zero drift. The first verification command referenced a nonexistent test filename and was immediately corrected to the repository's actual config/runtime test modules; this was a command-selection error, not a product failure.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Integrated the index-first retrieval contract across `adr-context` and the key-free MCP server. Equivalent CLI and MCP requests now accept the same bounded field, lifecycle, authority, strictness, and history controls and return identical compatible results with explicit engine/fallback provenance and positive match evidence. Added input/root containment and timeout safeguards, schema-v1/future-schema and Windows-path coverage, no-result behavior, and synchronized Codex/Copilot payloads. Focused retrieval/MCP and client/config suites pass with generated artifacts clean.
<!-- SECTION:FINAL_SUMMARY:END -->
