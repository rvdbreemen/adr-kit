---
id: TASK-58.2
title: 'adr-mcp: modern wire contract and server/discover'
status: Done
assignee: []
created_date: '2026-07-29 22:47'
updated_date: '2026-07-30 20:50'
labels:
  - mcp
  - protocol
dependencies:
  - TASK-58.1
references:
  - >-
    docs/adr/ADR-016-serve-both-mcp-protocol-eras-from-one-hand-rolled-stdio-server.md
  - docs/research/2026-07-29-mcp-2026-07-28-revision.md
modified_files:
  - bin/adr-mcp
parent_task_id: TASK-58
priority: high
ordinal: 60500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Second implementation slice of ADR-016, on top of TASK-58.1. Makes modern-era results spec-shaped and adds the discovery RPC. Legacy-era result shapes must stay byte-identical to today.

**Result stamping** — every modern result carries:
- `resultType: "complete"`. The five tools are fully parameterised by their arguments, so the server never emits `"input_required"` and never invents a value of its own.
- `_meta: {"io.modelcontextprotocol/serverInfo": {"name": "adr-kit", "version": server_version()}}`.

**Cache hints** — on `server/discover` and `tools/list` only: `ttlMs` and `cacheScope`. `cacheScope` is `"public"` because the tool list is identical for every caller and carries no user-specific data. `ttlMs` is the Python `int` `300000`, bounding post-upgrade staleness to five minutes. Emitting an int is deliberate: `schema.ts` declares `ttlMs: number` with `@minimum 0` while the generated `schema.json` declares `"type": "integer"`, and an int satisfies both readings.

`tools/call` results are NOT cacheable — `CallToolResult` extends `Result` only, so no `ttlMs`/`cacheScope` there. Tool-internal failures stay `isError: true` inside a `resultType: "complete"` result; an unknown tool name stays a JSON-RPC error.

**`server/discover`** returns exactly the five required `DiscoverResult` fields plus two optional ones:
- `resultType`, `supportedVersions` (= `list(MODERN_PROTOCOL_VERSIONS)`), `capabilities` (`{"tools": {}}`, no `listChanged`, no `extensions`), `ttlMs`, `cacheScope`
- `_meta.serverInfo`, and an `instructions` string

There is deliberately no top-level `serverInfo` and no top-level `protocolVersion`: neither field exists in `DiscoverResult` this revision. Note that `supportedVersions` lists the MODERN versions only — the SDK's own default handler returns `list(MODERN_PROTOCOL_VERSIONS)` (`src/mcp/server/lowlevel/server.py:660-675`), because `server/discover` is itself a modern-era RPC and legacy reachability is settled by the handshake instead. Advertising a handshake version here would invite a client to send it inside a modern envelope, which does not exist.

**`tools/list`** returns the five tools in the fixed declaration order of `TOOL_DEFINITIONS`, satisfying the deterministic-ordering SHOULD.

**`ping`** stays reachable in the legacy era and must NOT be advertised or served in the modern era, where it was removed.

Tolerate without implementing: a client that sends `inputResponses` or `requestState` (MRTR), or `io.modelcontextprotocol/logLevel`. Never emit `-32021` — the server never samples, elicits or asks for roots, so it has no legitimate code path for it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every modern-era result carries `resultType: "complete"`
- [ ] #2 Every modern-era result carries `_meta` with `io.modelcontextprotocol/serverInfo` (name and version)
- [ ] #3 `server/discover` and modern `tools/list` carry `ttlMs: 300000` as an int and `cacheScope: "public"`
- [ ] #4 Modern `tools/call` results carry NO ttlMs and NO cacheScope
- [ ] #5 `server/discover` returns all five required DiscoverResult fields and no top-level serverInfo or protocolVersion
- [ ] #6 `supportedVersions` equals list(MODERN_PROTOCOL_VERSIONS), not the union with handshake versions
- [ ] #7 `tools/list` returns the five tools in TOOL_DEFINITIONS declaration order, stable across calls
- [ ] #8 Legacy-era results are byte-identical to the pre-change output for the same input
- [ ] #9 `ping` answers in the legacy era and is not served in the modern era
- [ ] #10 A tool-internal failure is `isError: true` inside a resultType complete result, not a JSON-RPC error
- [ ] #11 An unknown tool name is still a JSON-RPC error, not an isError result
- [ ] #12 No code path emits -32021 or -32020
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented in `bin/adr-mcp` alongside TASK-58.1. `tests/test_adr_mcp.py`: 39 passed.

Added `_modern_result()` as a single stamping seam (`resultType`, cache hints, `_meta.serverInfo`), `handle_server_discover()`, and split `dispatch()` into `_dispatch_legacy` / `_dispatch_modern`. `_reply_error` gained an optional `data` argument for the -32022 payload. The module docstring was rewritten — it still claimed the server was handshake-era only.

**Verified per criterion**, driven as real frames rather than inspected: `resultType: "complete"` and `_meta.serverInfo` on every modern result; `ttlMs` as an int and `cacheScope: "public"` on `server/discover` and modern `tools/list`; both absent on `tools/call`; `supportedVersions == ["2026-07-28"]` and no top-level `serverInfo` or `protocolVersion` in the DiscoverResult; tools returned in declaration order and stable across calls; a tool-internal failure as `isError: true` inside a `resultType: complete` result while an unknown tool name stays a JSON-RPC error; an enveloped `ping` refused; `logLevel`, `progressToken`, `inputResponses` and `requestState` all tolerated without being implemented.

Legacy-era result shapes are unchanged — see TASK-58.1's summary for the byte-identity evidence and the one `bin/adr-status` key-order caveat.

**Handover note on acceptance criterion 12** (no -32020/-32021 ever emitted): no code path emits either, but there is now a comment at `bin/adr-mcp:685-687` naming both codes to explain *why* they are unreachable. A grep-based assertion would therefore false-positive. TASK-58.3 asserts this against emitted frames from a driven session instead, which is the stronger check anyway.

**Left unclaimed, deliberately:** ADR-016 observes that `bin/adr-mcp:469` should pass `--snapshot worktree` rather than `diff`, since `diff` cannot reconstruct a post-image for a modified file and produces unactionable violations through the MCP `adr_judge` tool. The ADR calls it "a TASK-58 opportunity, not a requirement of this decision" and it appears in neither task's acceptance criteria, so it was not changed. It remains a real defect worth its own task.
<!-- SECTION:FINAL_SUMMARY:END -->
