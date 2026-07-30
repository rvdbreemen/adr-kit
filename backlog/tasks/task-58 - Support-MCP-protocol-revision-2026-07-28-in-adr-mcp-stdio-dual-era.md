---
id: TASK-58
title: 'Support MCP protocol revision 2026-07-28 in adr-mcp (stdio, dual-era)'
status: To Do
assignee: []
created_date: '2026-07-29 21:35'
updated_date: '2026-07-30 05:26'
labels:
  - mcp
  - protocol
  - compatibility
dependencies: []
references:
  - 'https://modelcontextprotocol.io/specification/2026-07-28/changelog'
  - >-
    https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio
  - >-
    https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http#backward-compatibility
  - 'https://pypi.org/project/mcp/2.0.0/'
  - docs/adr/ADR-011-deterministic-readiness-with-human-gated-grilling.md
modified_files:
  - bin/adr-mcp
  - tests/test_adr_mcp.py
  - docs/adr/
priority: high
ordinal: 58500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
MCP specification revision 2026-07-28 (released 2026-07-28) makes the protocol stateless and removes the `initialize`/`notifications/initialized` handshake. `bin/adr-mcp` is a hand-rolled stdio JSON-RPC server that currently speaks the `initialize` era only (`DEFAULT_PROTOCOL_VERSION = "2025-06-18"`).

Governed by ADR-016 (Accepted 2026-07-30). Read that ADR before implementing; it is the binding spec for this work.

CORRECTED 2026-07-30: an earlier version of this task claimed the server must serve both eras "for the length of the twelve-month deprecation window". That is wrong and was verified against the primary source. The `initialize` handshake was REMOVED in 2026-07-28, not deprecated. The lifecycle policy's minimum twelve-month window (SEP-2596) binds only features in the Deprecated state, and the registry at /specification/2026-07-28/deprecated lists exactly six — Roots, Sampling, Logging, Dynamic Client Registration, the `includeContext` values, and HTTP+SSE transport — none of them the handshake. The Removed section is empty. There is no spec clock running on legacy handshake support.

The real reasons one process must serve both eras:
- `2025-11-25` and earlier remain valid published revisions that shipping clients speak, and nothing in 2026-07-28 obliges a client to migrate on any schedule.
- The compatibility matrix marks Legacy client / Modern server as "Fails", noting that legacy clients have no fall-forward mechanism.
- adr-kit ships through three marketplaces (ADR-012) into environments whose client version it does not choose.

Scope is bounded to what applies to a stdio, tools-only server. Explicitly out of scope: everything in the Streamable HTTP half of the revision (session-id removal, `subscriptions/listen`, `Last-Event-ID`, `Mcp-Method`/`Mcp-Name` headers, `x-mcp-header`, `HeaderMismatchError` -32020), the MRTR `InputRequiredResult` pattern (the server never initiates requests), the Tasks extension, `MissingRequiredClientCapabilityError` -32021 (no code path can legitimately emit it), and the Roots/Sampling/Logging deprecations (unused).

Two pre-existing defects, both reproduced by piping raw frames into `bin/adr-mcp --root .`:

1. `handle_initialize` (`bin/adr-mcp:639-646`) returns the client's requested `protocolVersion` verbatim, so the server claims agreement with `2026-07-28` — or any nonsense string — without implementing it.
2. The dispatch loop never validates era or ordering. A `tools/list` carrying a full modern `_meta` envelope, sent as the first frame with no `initialize`, is answered with a bare `{"tools": [...]}`: no `resultType`, no `ttlMs`, no `cacheScope`, no `_meta.serverInfo`. This is the "era-ambiguous method" hazard the compatibility matrix names.

On the existing test: `test_initialize_echoes_client_protocol_version` (`tests/test_adr_mcp.py:203`) sends `protocolVersion="2024-11-05"` and asserts the same value returns. Because `2024-11-05` IS a declared handshake revision, echo and correct confirmation are indistinguishable on that input — the test passes unchanged under the new negotiation and only its NAME is wrong. The real coverage gap is that no test sends `initialize` an undeclared version string.

Backward compatibility is safe in the interim: a client probing `server/discover` and getting any unrecognized error (commonly -32601) treats the server as legacy and falls back to `initialize`, and that fallback MUST NOT be keyed to one specific error code. The server is non-compliant, not broken.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `server/discover` is implemented and returns all five required DiscoverResult fields
- [ ] #2 Requests carrying `_meta.io.modelcontextprotocol/protocolVersion` are served statelessly, with no `initialize` required
- [ ] #3 The legacy `initialize` / `notifications/initialized` handshake keeps working unchanged for older clients
- [ ] #4 Era is a pure function of the single frame; no per-process or per-connection era state exists
- [ ] #5 A modern request naming a version outside MODERN_PROTOCOL_VERSIONS gets -32022 with data.supported and data.requested; `initialize` NEVER gets -32022 but a counter-offer of 2025-11-25 instead
- [ ] #6 Every modern-era result carries `resultType: "complete"`
- [ ] #7 `server/discover` and modern `tools/list` carry ttlMs and cacheScope; `tools/call` carries neither
- [ ] #8 Each modern result's `_meta` carries `io.modelcontextprotocol/serverInfo`
- [ ] #9 `tools/list` returns the five tools in deterministic declaration order
- [ ] #10 A modern-enveloped frame is answered under modern semantics even when it follows a legacy `initialize` on the same stdin
- [ ] #11 Conformance tests drive all three shapes through `serve()`: legacy `initialize`, stateless `_meta`, and `server/discover`
- [ ] #12 `test_initialize_echoes_client_protocol_version` is renamed; its assertion still holds because 2024-11-05 is a declared handshake version, so the fix is the name plus a new test that sends an undeclared version string
- [ ] #13 ADR-016 governs this work and is Accepted
<!-- AC:END -->
