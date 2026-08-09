---
id: TASK-58
title: 'Support MCP protocol revision 2026-07-28 in adr-mcp (stdio, dual-era)'
status: Done
assignee: []
created_date: '2026-07-29 21:35'
updated_date: '2026-07-31 05:04'
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

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Umbrella closed: 58.1 through 58.5 are all Done, and CI on `dev` is green across Python 3.10 and 3.12 on ubuntu, macos and windows.

`bin/adr-mcp` now serves both MCP protocol eras from one process, governed by ADR-016. The load-bearing design point is that **era is a pure function of the single frame** — no per-process and no per-connection state, so the same bytes always get the same answer. Revision 2026-07-28 forbids relying on prior requests over a connection to establish context, and a lock would mean a byte-identical frame gets two different answers depending on history. The official SDK does lock per connection; this deliberately diverges, and TASK-58.4 validated that the divergence holds up against the SDK's own client.

What the validation actually established, rather than assumed: all three real clients (Claude Code 2.1.220, Codex CLI 0.145.0, GitHub Copilot CLI 1.0.71) negotiate the **handshake** era today, and the modern surface is exercised only by the official `mcp` 2.0.0 SDK. ADR-016 deliberately made no assumption about this; now there is evidence. All three put vendor keys in `params._meta` without using the reserved `io.modelcontextprotocol/` prefix, which is direct empirical support for keying era detection on the reserved key rather than on `_meta` merely being present.

`server/discover` does not add a round trip — it replaces `initialize` one for one. Cold start to first tool result is 578 ms p50 legacy versus 622 ms modern, both roughly a third of ADR-015's 2000 ms budget, and modern is 208 ms *faster* at p95. The latency corpus was deliberately left untouched: nothing breaches the budget, so there was nothing to justify.

**Three defects surfaced along the way that the plan did not anticipate**, all now fixed with regression tests:

- `bin/adr-mcp` did not speak UTF-8 on Windows (TASK-69) — invalid bytes on the wire, CRLF framing, a tool result lost to `-32603`. Pre-existing and era-independent, but it made the official SDK client unable to drive the server on a cp1252 host in any era.
- `require_pattern` under `--snapshot diff` blocked on a finding no author could act on (TASK-65), which is also what had made ADR-016 decline its four `require_pattern` rules as permanently unworkable. Fixing it inverted that reasoning, and the rules are now in the Enforcement block, re-measured to fire on a breach and stay silent on the compliant implementation.
- `bin/adr-status` emitted `summary.by_status` in `PYTHONHASHSEED`-dependent order (TASK-66), which is why the conformance suite could not get a byte-exact golden for that one frame.

ADR-016 is Accepted, `documents_shipped: true`, `verified_in: tests/test_adr_mcp.py`, gate `adr-mcp-dual-era-v1` live. Shipped in v0.43.0.</finalSummary>
<!-- SECTION:FINAL_SUMMARY:END -->
