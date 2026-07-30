---
id: TASK-58.3
title: 'adr-mcp: dual-era conformance test suite'
status: To Do
assignee: []
created_date: '2026-07-29 22:48'
labels:
  - mcp
  - protocol
  - tests
dependencies:
  - TASK-58.1
  - TASK-58.2
references:
  - >-
    docs/adr/ADR-016-serve-both-mcp-protocol-eras-from-one-hand-rolled-stdio-server.md
modified_files:
  - tests/test_adr_mcp.py
parent_task_id: TASK-58
priority: high
ordinal: 61500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Prove both eras through `serve()` rather than by inspection. The existing suite in `tests/test_adr_mcp.py` covers the handshake era only and encodes one behaviour that ADR-016 deliberately removes.

**Test that must change:** `test_initialize_echoes_client_protocol_version` (`tests/test_adr_mcp.py:203`) asserts the version echo as intended behaviour. Rewrite it to assert negotiation: a known handshake version is confirmed, an unknown or modern-era version returns -32022. Keep the test name honest — rename it so it no longer claims echoing is correct.

**Coverage required, all driven as real JSON-RPC lines through `serve()`:**

*Era routing* — modern envelope routes modern; bare `_meta` with only `progressToken` routes legacy; `initialize` routes legacy even with the envelope stamped on it; a request after a legacy `initialize` stays legacy; `server/discover` routes modern without any prior message.

*Negotiation* — each of the four handshake versions is confirmed; absent version counter-offers 2025-11-25; a modern version on `initialize` gets -32022 with the handshake list; a garbage string gets -32022, not a crash and not a reflected echo; a non-string version gets -32602.

*Modern shapes* — `resultType` present on every result; `_meta.serverInfo` present; `ttlMs`/`cacheScope` on `server/discover` and `tools/list`; absent on `tools/call`; `supportedVersions` is the modern list only; no top-level `serverInfo` or `protocolVersion` in DiscoverResult.

*Legacy regression* — capture the current legacy output for `initialize`, `ping`, `tools/list` and each of the five `tools/call` shapes BEFORE the change and assert byte-equality after. This is the guard that the dual-era work does not silently alter what today's clients receive.

*Robustness* — malformed JSON line does not kill the loop (already covered, keep); unknown method returns -32601; unknown notification silently ignored; a client sending `inputResponses`/`requestState`/`logLevel` is tolerated, not rejected; concurrent-era confusion (enveloped request arriving after legacy `initialize`) produces a deterministic error rather than a mixed-shape result.

Run the full suite on both CI Python versions (3.10 and 3.12, per `.github/workflows/validate.yml:175`), not just the local interpreter.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `test_initialize_echoes_client_protocol_version` is rewritten and renamed to assert negotiation, not echoing
- [ ] #2 Era-routing tests cover all five routing cases listed in the description
- [ ] #3 Negotiation tests cover all four handshake versions plus absent, modern-on-initialize, garbage-string and non-string cases
- [ ] #4 Modern-shape tests assert resultType, _meta.serverInfo, and the presence/absence of ttlMs and cacheScope per method
- [ ] #5 A legacy golden-output regression test asserts byte-equality with the pre-change output for initialize, ping, tools/list and all five tools/call shapes
- [ ] #6 Robustness tests cover malformed JSON, unknown method, unknown notification, and tolerated MRTR/logLevel fields
- [ ] #7 The whole suite passes on Python 3.10 and 3.12
- [ ] #8 No test asserts behaviour that ADR-016 explicitly rejects
<!-- AC:END -->
