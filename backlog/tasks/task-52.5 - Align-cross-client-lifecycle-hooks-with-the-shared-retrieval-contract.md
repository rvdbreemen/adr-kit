---
id: TASK-52.5
title: Align cross-client lifecycle hooks with the shared retrieval contract
status: Done
assignee:
  - Codex
created_date: '2026-07-23 17:44'
updated_date: '2026-07-23 19:12'
labels:
  - adr
  - hooks
  - codex
  - claude
  - copilot
milestone: Index-first ADR retrieval
dependencies:
  - TASK-52.4
references:
  - TASK-52
  - hooks/adr_hook_core.py
  - hooks/native/adr-hook.rs
  - clients/capabilities.json
documentation:
  - docs/client-support.md
  - docs/adr/ADR-004-layered-adr-context-injection.md
  - >-
    docs/adr/ADR-010-certify-three-native-cli-clients-through-one-outcome-contract.md
modified_files:
  - hooks/adr_hook_core.py
  - hooks/native/adr-hook.rs
  - hooks/bin/windows-x64/adr-hook.exe
  - clients/capabilities.json
  - clients/exceptions.json
  - clients/fixtures/copilot-lifecycle-event-limit.json
  - tests/test_hook_protocol.py
  - tests/test_client_capabilities_schema.py
  - tests/certification/simulated-pass.json
  - codex/hooks/adr_hook_core.py
  - codex/hooks/bin/windows-x64/adr-hook.exe
  - copilot/hooks/adr_hook_core.py
  - copilot/hooks/bin/windows-x64/adr-hook.exe
parent_task_id: TASK-52
priority: high
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make session, prompt, pre-edit, post-edit, subagent, and compaction context use the same selective retrieval semantics across Python and native hooks while preserving each client's documented capability and fail-open behavior.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Session orientation includes only explicitly global Accepted ADRs and never arbitrary first records.
- [x] #2 Prompt and edit hooks select context through the shared outcome contract and keep Proposed findings separate from governing Accepted decisions.
- [x] #3 Python and native hook implementations pass the same retrieval fixtures and preserve bounded output, cooldowns, timeouts, and fail-open behavior.
- [x] #4 Claude and Codex retain native pre-edit context; Copilot retains its explicit supported degradation and deterministic backstops.
- [x] #5 Subagent and compaction paths preserve already-selected ADR context without broadening it to unrelated decisions.
- [x] #6 Generated client payloads and capability documentation remain synchronized.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Inventory Python/native hook event paths and the Claude, Codex, and Copilot capability declarations. 2. Introduce one bounded hook retrieval request/outcome adapter over the shared index-first engine: global Accepted-only session orientation; prompt/edit selective governing and advisory groups; preserved selected context for subagents/compaction. 3. Keep all hook paths fail-open with existing cooldown, timeout, size, and client-capability behavior, including Copilot's documented no-pre-edit degradation and deterministic judge/backstop. 4. Align native and Python fixtures/output semantics and regenerate client payloads/capability documentation. 5. Run hook protocol, native parity, adapter-generation, client-capability, and timeout regression tests before finalization.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan pre-recorded under the approved epic drain. Implementation starts only after TASK-52.4 is finalized.

TASK-52.4 is Done with a stable shared CLI/MCP request and result contract. Hook alignment now starts against that verified surface.

Python hooks now call the shared strict index-first query outcome and fail open without broad Markdown expansion. SessionStart selects only Accepted records explicitly marked `context_scope: global`; prompt and edit results render governing Accepted and advisory Proposed records under separate headings.

SubagentStart and PreCompact now preserve only the supplied parent ADR bundle and return a no-op when none is supplied, preventing context broadening. Edit paths remain workspace-contained; output stays bounded. The native Rust host implements the same metadata-aware positive ranking and lifecycle grouping over the generated index.

Claude and Codex capability mappings now document native prompt, pre-edit, subagent, and compaction events. Copilot retains PostToolUse edit backstop and documents unavailable SubagentStart/PreCompact events through a registered, fixture-backed non-blocking degradation. The native binary was rebuilt from the dependency-free Rust source and synchronized to generated packages.

Verification: 69 hook/guardian/grill/capability/adapter/native-package/certification tests passed in the broad slice; the final focused hook/capability/adapter slice passed 48 tests. Python/native fixture assertions compare exact selected ADR-ID sets, hook hard-timeout checks pass, and generated adapters report zero drift.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Aligned lifecycle hooks with ADR-014's index-first retrieval and authority contract. Session orientation is global Accepted-only, prompt/edit context separates governing Accepted from advisory Proposed decisions, and subagent/compaction events preserve rather than broaden selected context. The dependency-free native host mirrors the Python oracle's selected ADR sets and remains bounded/fail-open. Claude, Codex, and Copilot capability mappings and registered degradations now describe actual event support, with synchronized binaries and client payloads. Hook, parity, timeout, capability, packaging, and certification tests pass.
<!-- SECTION:FINAL_SUMMARY:END -->
