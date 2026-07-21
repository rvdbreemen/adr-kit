---
id: TASK-45.6
title: Expose readiness through the key-free MCP server
status: Done
assignee:
  - Codex
created_date: '2026-07-20 19:51'
updated_date: '2026-07-20 20:47'
labels:
  - feature
  - adr-grilling
  - mcp
  - readiness
milestone: ADR Grilling
dependencies:
  - TASK-45.4
  - TASK-45.5
documentation:
  - docs/feature-adr-grilling/03-solution-design.md
  - docs/feature-adr-grilling/04-implementation-plan.md
  - docs/feature-adr-grilling/05-validation-plan.md
modified_files:
  - bin/adr-mcp
  - tests/test_adr_mcp.py
  - clients/workflows.json
  - scripts/benchmark-adr-grilling.py
  - docs/feature-adr-grilling/03-solution-design.md
  - docs/feature-adr-grilling/06-benchmark-report.md
parent_task_id: TASK-45
priority: high
ordinal: 45600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add adr_readiness as the fifth read-only MCP tool, exposing the same single-ADR, all-Proposed, and diff readiness semantics as the CLI without adding lifecycle mutation or provider credentials.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 adr_readiness accepts one ADR, all Proposed ADRs, or a diff range plus workspace override and returns the shared readiness report.
- [x] #2 The tool cannot create, edit, accept, reject, supersede, or otherwise mutate an ADR or repository state.
- [x] #3 Workspace boundaries, path normalization, timeouts, and structured errors follow the existing MCP conventions.
- [x] #4 The existing adr_context, adr_judge, adr_status, and adr_quality contracts remain unchanged.
- [x] #5 Tool inventory, schemas, generated documentation, and tests identify exactly five MCP tools.
- [x] #6 CLI and MCP produce semantically identical reports for the same fixtures and injected date.
- [x] #7 Workspace isolation, malformed input, missing repository, timeout, and no-mutation tests pass.
- [x] #8 MCP adapter overhead is no greater than 100 ms above the equivalent readiness core operation.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add adr_readiness as exactly the fifth key-free read-only MCP tool. 2. Reuse the CLI/report contract for ADR, all-Proposed and base/head modes with existing workspace/error/timeout conventions. 3. Add inventory, schema, parity, isolation and no-mutation tests. 4. Measure persistent-server adapter overhead against the CLI operation.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added adr_readiness as exactly the fifth MCP tool without changing the four existing contracts. It validates workspace/ADR/mode/date inputs, delegates to the shared CLI with a bounded timeout and returns structured errors. CLI/MCP report parity and no-mutation are tested. Persistent-server 30-sample p95 was 310.024 ms versus CLI p95 348.958 ms, conservatively zero additional overhead and within the 100 ms budget. Generated client copies match.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Exposed readiness through the existing stdlib-only, key-free MCP server as its fifth read-only tool. Single-ADR, all-Proposed and range modes reuse the CLI contract, injected date and existing workspace/error/timeout conventions; no lifecycle mutation capability was added. Inventory, malformed-input, workspace, parity and no-mutation tests pass, existing tools retain their schemas, and persistent-server adapter overhead passed its budget.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 MCP schema, contract, parity, isolation, and error tests pass.
- [x] #2 Performance evidence separates core duration from adapter overhead.
- [x] #3 Tool documentation, inventory assertions, modified files, and exact validation results are recorded.
<!-- DOD:END -->
