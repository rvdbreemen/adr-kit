---
id: TASK-58.2
title: 'adr-mcp: modern wire contract and server/discover'
status: To Do
assignee: []
created_date: '2026-07-29 22:47'
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
