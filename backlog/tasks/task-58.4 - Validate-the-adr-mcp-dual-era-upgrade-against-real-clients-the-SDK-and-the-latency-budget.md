---
id: TASK-58.4
title: >-
  Validate the adr-mcp dual-era upgrade against real clients, the SDK and the
  latency budget
status: To Do
assignee: []
created_date: '2026-07-29 22:48'
labels:
  - mcp
  - protocol
  - validation
dependencies:
  - TASK-58.2
  - TASK-58.3
references:
  - >-
    docs/adr/ADR-015-enforce-a-two-second-deterministic-latency-budget-as-a-test-fixture-contract.md
  - >-
    docs/adr/ADR-016-serve-both-mcp-protocol-eras-from-one-hand-rolled-stdio-server.md
  - 'https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.0.0'
modified_files:
  - tests/test_adr_mcp.py
  - tests/fixtures/cli/latency-corpus.json
parent_task_id: TASK-58
priority: high
ordinal: 62500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Unit tests prove the shapes we believe in. This task proves the upgrade against things we do not control: real MCP clients, the official SDK's own client, and the latency contract.

**1. Live client smoke test.** Register the changed server and confirm the five tools still list and call correctly from Claude Code itself (`.mcp.json` launches `python ${CLAUDE_PLUGIN_ROOT}/bin/adr-mcp`). Note which era the client actually negotiates and record it — this is the first hard evidence of what Claude Code speaks today, which the ADR deliberately did not assume. Repeat for Codex CLI and GitHub Copilot CLI if their MCP surface allows it; if it does not, say so rather than claiming coverage.

**2. Cross-validate with the official SDK client.** The `mcp` SDK 2.0.0 ships a client that probes `server/discover` and falls back to `initialize` (`src/mcp/client/session.py:685-722`, and `mode='auto'` documented at `client.py:335`). Drive our server with that client in a throwaway virtualenv — the SDK is a test-only dependency here and must NOT enter the runtime dependency set. Verify all three of its modes: `auto`, modern-only, and legacy. This is the strongest available conformance signal short of the official test suite.

**3. Backward-compatibility regression.** Confirm the pre-change behaviour still holds for a client that only speaks the handshake era, including one that sends `initialize` with no `protocolVersion` at all.

**4. Latency budget (ADR-015).** ADR-015 pins a two-second deterministic budget as a fixture contract (`tests/fixtures/cli/latency-corpus.json`). The modern era adds a `server/discover` round-trip before any real work. Measure whether that changes the numbers the corpus asserts, and either show it stays inside the budget or update the fixture with justification. Do not silently widen the budget.

**5. Schema validation.** Validate real captured responses against the authoritative JSON schema for 2026-07-28 (available at `schema/2026-07-28.json` in the python-sdk checkout, `$defs` not `definitions`). Validate at minimum a DiscoverResult, a modern ListToolsResult and a modern CallToolResult. Report any field the schema rejects.

**6. Cross-platform.** Run the suite on Windows as well as Linux CI. This repo has a documented history of Windows-specific breakage (CRLF false positives in the adapter drift check, per TASK-57), so a Linux-only pass is not evidence.

Record the outcome as evidence in the task's final summary: which clients were tested, which era each negotiated, and any deviation found. A validation task that reports "looks fine" without naming what was exercised has not been done.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The changed server lists and calls all five tools from Claude Code, and the negotiated era is recorded as evidence
- [ ] #2 Codex CLI and GitHub Copilot CLI are either verified or explicitly documented as not verifiable, with the reason
- [ ] #3 The official mcp 2.0.0 SDK client drives the server successfully in auto, modern-only and legacy modes, from a throwaway venv
- [ ] #4 The SDK does not appear in any runtime dependency declaration of adr-kit after this work
- [ ] #5 A handshake-only client, including one sending initialize with no protocolVersion, still works exactly as before
- [ ] #6 The ADR-015 two-second latency budget is measured with the added server/discover round-trip, and either shown to hold or the fixture is updated with written justification
- [ ] #7 Captured DiscoverResult, modern ListToolsResult and modern CallToolResult payloads validate against schema/2026-07-28.json
- [ ] #8 The suite passes on Windows and on Linux CI
- [ ] #9 The task's final summary names every client and mode exercised, and any deviation found
<!-- AC:END -->
