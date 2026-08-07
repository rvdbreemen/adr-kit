---
id: "ADR-016"
title: "Serve Both MCP Protocol Eras from One Hand-Rolled Stdio Server"
status: "Accepted"
date: "2026-07-30"
binding: true
gate: "adr-mcp-dual-era-v1"
documents_shipped: true
verified_in:
  - "tests/test_adr_mcp.py"
supersedes: []
superseded_by: null
topics:
  - "model context protocol"
  - "protocol versioning"
  - "backward compatibility"
  - "dependency policy"
  - "stdio transport"
aliases:
  - "dual-era MCP"
  - "2026-07-28 revision"
  - "server/discover"
components:
  - "adr-mcp"
  - "tests"
symbols:
  - "KNOWN_PROTOCOL_VERSIONS"
  - "HANDSHAKE_PROTOCOL_VERSIONS"
  - "MODERN_PROTOCOL_VERSIONS"
  - "server/discover"
  - "handle_initialize"
  - "dispatch"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-016 Serve Both MCP Protocol Eras from One Hand-Rolled Stdio Server

## Status

Accepted, 2026-07-30.

## Status History

```yaml
status_history:
  - date: 2026-07-30
    status: Proposed
    changed_by: adr-kit
    reason: Initial proposal for TASK-58 (MCP revision 2026-07-28 support)
    changed_via: adr-kit
  - date: 2026-07-30
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Human acceptance in session after all seven lint gates passed; require_pattern rules deferred to TASK-58.5 so enforcement cannot block incremental work before the implementation exists
    changed_via: adr-kit lifecycle
  - date: 2026-07-31
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Dual-era surface shipped in TASK-58.1/58.2 and validated against three real clients plus the official mcp 2.0.0 SDK in TASK-58.4; gate adr-mcp-dual-era-v1 is live in the conformance suite
    changed_via: adr-kit lifecycle
```

**Decision Maker:** User: Robert van den Breemen — accepted 2026-07-30 in an
interactive session. Not self-approved by an agent.

## Context and Problem Statement

`bin/adr-mcp` is a 763-line, 28,075-byte hand-rolled Model Context Protocol
server on the Python standard library only, with zero runtime dependencies. It
speaks newline-delimited JSON-RPC (JSON Remote Procedure Call) 2.0 over stdio
and exposes exactly five read-only tools (`adr_context`, `adr_judge`,
`adr_status`, `adr_quality`, `adr_readiness`), each a subprocess call into a
sibling `bin/` script, and none of them makes a large language model (LLM)
call. Its own
module docstring states the design intent: "The protocol surface is
deliberately tiny (initialize, initialized, tools/list, tools/call, ping); the
dispatch table in serve() is shaped so swapping in the official `mcp` SDK
later is a local change" (`bin/adr-mcp:7-9`). The same file ships in
triplicate: `clients/installer/payload.py:175` copies `root/bin`,
`root/codex/bin` and `root/copilot/bin`, and all three `adr-mcp` copies are
byte-identical (28,075 bytes each) modulo line endings.

MCP specification revision `2026-07-28`, published 2026-07-28, invalidates that
surface. The revision makes the protocol **stateless** and **removes the
`initialize` / `notifications/initialized` handshake entirely**: there is no
`InitializeRequest`, `InitializeResult` or `InitializedNotification` anywhere in
the 3,197-line `schema.ts`, and the single remaining occurrence of the word
"initialization" is a doc comment explaining that capabilities are now declared
per request. Concretely, for a STDIO (standard input/output) tools-only server
the following apply, with the specification's RFC 2119 keywords MUST (an
absolute requirement), MUST NOT (an absolute prohibition) and MAY (a truly
optional permission) quoted as published:

* `server/discover` replaces the handshake and servers **MUST** implement it.
* Every request carries `params._meta` with two required reserved keys,
  `io.modelcontextprotocol/protocolVersion` and
  `io.modelcontextprotocol/clientCapabilities`. `RequestParams` declares
  `_meta` as required and `RequestMetaObject` declares both keys as required,
  so this applies to every method including `server/discover`. "A request
  missing any required field is malformed; the server **MUST** reject it with
  JSON-RPC error code `-32602` (Invalid params)."
* Statelessness is normative: "Servers **MUST NOT** rely on prior requests
  over the same connection to establish context (e.g., capabilities, protocol
  version, client identity). Every request supplies this metadata in its
  `_meta` field", and "an open connection, such as a STDIO process, is not a
  conversation or session".
* Every result **MUST** carry `resultType`; `tools/list` additionally **MUST**
  carry `ttlMs` and `cacheScope` because `ListToolsResult` now extends
  `CacheableResult`.
* A version the server does not implement **MUST** be answered with
  `UnsupportedProtocolVersionError`, code `-32022`, whose `data` carries
  `supported: string[]` and `requested: string`.

Three defects were reproduced against the shipped server (v0.42.0, this
repository, 2026-07-29) by piping raw frames into `bin/adr-mcp --root .`:

1. **The handshake echoes any version string.** `handle_initialize`
   (`bin/adr-mcp:639-646`) computes
   `protocol = requested if isinstance(requested, str) and requested else DEFAULT_PROTOCOL_VERSION`.
   Sending `initialize` with `protocolVersion: "2026-07-28"` returns
   `{"protocolVersion": "2026-07-28", "capabilities": {"tools": {}}, ...}`. The
   server claims agreement with a revision it does not implement, and would do
   the same for a nonsense string. Nothing in the suite pins this defect:
   `tests/test_adr_mcp.py:203`
   (`test_initialize_echoes_client_protocol_version`) sends
   `protocolVersion="2024-11-05"` and asserts the same value comes back, and
   `"2024-11-05"` is a declared handshake revision, so echo and correct
   confirmation are indistinguishable on that input. The test passes unchanged
   under the negotiation below; only its name is wrong. No existing test sends
   `initialize` an undeclared version string, which is the coverage gap.
2. **`server/discover` is absent.** The same session returns
   `{"error": {"code": -32601, "message": "Method not found: server/discover"}}`,
   violating an unconditional server MUST.
3. **The dispatch loop never validates era or ordering.** `dispatch`
   (`bin/adr-mcp:669-705`) branches on `method` alone. A `tools/list` carrying a
   full modern `_meta` envelope, sent as the very first frame with no
   `initialize` at all, is answered `{"tools": [...]}` — no `resultType`, no
   `ttlMs`, no `cacheScope`, no `_meta.serverInfo`. This is precisely the
   "era-ambiguous method" hazard the revision's compatibility matrix names: a
   legacy server "may reject the request with an implementation-defined error,
   stay silent, or even process an era-ambiguous method under legacy
   semantics". A modern-only client gets silent legacy behaviour instead of a
   deterministic failure.

The urgency is real but bounded, and the ADR should not overstate it. Per the
stdio backward-compatibility rules, a dual-era client probing `server/discover`
gets one of three outcomes, the third being: "The server returns any other
error, or does not respond within a reasonable timeout: the server is legacy.
Fall back to the `initialize` handshake." That fallback "**MUST NOT** be keyed
to one specific error code". Today's `-32601` therefore produces a working
session for dual-era clients. **The server is non-compliant, not broken.**

What actually fails is the `Modern client / Legacy server` row of the
compatibility matrix — "Fails. The server may reject the request with an
implementation-defined error, stay silent, or even process an era-ambiguous
method under legacy semantics." No deadline forces this. The revision does not
deprecate the handshake on a clock: changelog Major change 2 *removes* the
`initialize` / `notifications/initialized` handshake outright, and the
deprecated-features registry for `2026-07-28` lists six entries (Roots,
Sampling, Logging, Dynamic Client Registration, the `includeContext` values,
HTTP+SSE (Server-Sent Events) transport) — none of them the handshake, and its
Removed section reads
"No features have been removed under this policy yet." The forcing function is
population, not policy: `2025-11-25` and earlier remain valid published
revisions that shipping clients speak, nothing in `2026-07-28` obliges a client
to migrate on a schedule, the matrix marks `Legacy client / Modern server` as
"Fails" with "Legacy clients have no fall-forward mechanism", and adr-kit ships
through three marketplaces (ADR-012) into environments whose client version it
does not choose.

The alternative on the table was to stop hand-rolling and adopt the official
`mcp` Python SDK, which released 2.0.0 on 2026-07-28T13:45:28Z — the same day
as the spec. Its v2 architecture is genuinely good and worth reading: a
three-way version registry (`KNOWN_PROTOCOL_VERSIONS` /
`HANDSHAKE_PROTOCOL_VERSIONS` / `MODERN_PROTOCOL_VERSIONS`) that treats
versions as an enumerated set rather than a sortable scalar, era detection from
one spec-reserved sentinel key, one dispatch kernel for both eras, and one
outbound serialization seam that stamps `resultType`, cache hints and
`serverInfo`. But measured on this machine (Windows 11, Python 3.12.9, pip
26.0.1), `pip install mcp==2.0.0` with no extras resolves **30 packages,
14.6 MiB of wheels, 5 of them native/compiled** (cffi, cryptography,
pydantic_core, pywin32, rpds-py), and `import mcp.server.stdio` loads **571
modules**, eagerly pulling `httpx2`, `starlette`, `uvicorn`, `sse_starlette`,
`cryptography` and `opentelemetry` into a stdio tools-only server that needs
none of them. Median cold start over 9 subprocess spawns: **+3.7 s** versus a
171 ms venv baseline, against ~0 ms for the current file.

## Decision Drivers

* The `2026-07-28` MUSTs for a stdio tools-only server are non-negotiable if
  the server is to be conformant: `server/discover`, per-request `_meta`,
  `resultType`, cache hints on `tools/list`, and `-32022` on version mismatch.
* One process must serve both eras for as long as legacy clients exist, which
  is not a dated window: `2025-11-25` and earlier are still valid published
  revisions, no rule obliges a client to migrate, and a legacy client meeting a
  modern-only server "Fails" with no fall-forward mechanism. adr-kit ships
  through three marketplaces (ADR-012) and does not choose its users' client
  version.
* Zero runtime dependencies is a load-bearing property of this repository, not
  an aesthetic: the plugin is installed by three marketplaces (ADR-012) into
  environments adr-kit does not control.
* Era selection must be deterministic and a pure function of the single frame
  being answered — never from configuration and never from process state,
  because the spec's statelessness rule forbids establishing context from prior
  requests on the same connection.
* The version the server advertises must be a declared set it actually
  implements, never a string reflected from the client.
* An unimplemented or ambiguous request must fail loudly and actionably, not
  degrade silently into the wrong era.
* Out-of-scope parts of the revision must be named, so a future reader can see
  they were decided rather than missed.

## Considered Options

* Extend the hand-rolled server to serve both eras from one process, reading
  the official `mcp` SDK 2.0.0 as a reference implementation but not depending
  on it.
* Adopt `mcp` 2.0.0 as a runtime dependency and delete the hand-rolled loop.
* Adopt only the separately-installable `mcp-types` 2.0.0 distribution for wire
  types and the version registry, keeping the hand-rolled loop.
* Implement the modern era only and drop legacy `initialize`.
* Do nothing for now and rely on dual-era clients falling back to `initialize`.

## Decision Outcome

Chosen option: **extend the hand-rolled stdio server to serve both protocol
eras from one process, with the official `mcp` SDK 2.0.0 read as a reference
implementation and not adopted as a runtime dependency.** `bin/adr-mcp` keeps
zero runtime dependencies and the standard library only.

The implementation surface is all three shipped copies of the file —
`bin/adr-mcp`, `codex/bin/adr-mcp` and `copilot/bin/adr-mcp` — which
`clients/installer/payload.py` ships to the three marketplaces and which must
stay byte-identical. Every rule below applies to each copy.

### Version registry

Replace `DEFAULT_PROTOCOL_VERSION` (`bin/adr-mcp:53`) with three explicit
tuples and treat protocol versions as an enumerated set, never as a sortable
scalar:

* `HANDSHAKE_PROTOCOL_VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18",
  "2025-11-25")` — the four revisions reachable through `initialize`. One
  stateless code path serves all four, and this was checked against the four
  published `schema.ts` files rather than assumed: across them
  `InitializeRequest` carries the same three params (`protocolVersion`,
  `capabilities`, `clientInfo`), `InitializeResult` carries the same four
  fields, `ListToolsRequest` / `ListToolsResult` / `PingRequest` are unchanged,
  and `CallToolRequest` still takes `name` plus optional `arguments`. The only
  differences in the subset are additive and optional — `CallToolResult` gained
  `structuredContent` in `2025-06-18` and its `content` union widened to
  `ContentBlock` — and `bin/adr-mcp` neither emits nor requires them. Because
  the subset is stable, the server needs no memory of which revision was
  negotiated, so the legacy branch stays as state-free as the modern one.
* `MODERN_PROTOCOL_VERSIONS = ("2026-07-28",)` — the stateless per-request
  envelope era.
* `KNOWN_PROTOCOL_VERSIONS` — their concatenation, oldest first, and the single
  source of every ordering answer.

Membership tests are set lookups. An unrecognised peer string is never
compared, because date strings only happen to sort lexicographically and
`"zzz" > "2025-11-25"` is true.

### Era detection

Era is a pure function of the single frame being answered. The server keeps no
per-process era state, so the same bytes always get the same answer:

1. `method == "server/discover"`, or `params._meta` contains
   `io.modelcontextprotocol/protocolVersion` → **modern**. The sentinel is that
   one key, not the full required pair: its prefix is spec-reserved so a legacy
   client cannot mint it, while a bare `_meta` is not evidence (legacy requests
   already put `progressToken` there). Checking the version key alone means a
   half-built envelope still routes modern and receives an `-32602` naming the
   missing key, instead of being misrouted to legacy and failing confusingly.
2. Any other frame — including `initialize` and `notifications/initialized` —
   → **legacy**.

There is deliberately no third rule and no era lock. The spec permits one
("An `initialize` request selects legacy semantics, scoped to the stdio process
… A dual-era server **MAY** serve both eras concurrently on the same endpoint
or process"), so a lock would be legal; it is rejected because it is
unnecessary and because it would make the answer depend on history. A bare
frame already routes legacy by rule 2, which is what a legacy client sends
after its handshake, and the handshake subset needs no remembered revision (see
Version registry). Locking would instead mean that a byte-identical frame gets
two different answers depending on what arrived earlier on the same stdin —
precisely what "Servers **MUST NOT** rely on prior requests over the same
connection to establish context" forbids.

Routing signal and validation stay separate. A modern-routed request missing
`io.modelcontextprotocol/protocolVersion` or
`io.modelcontextprotocol/clientCapabilities` is answered `-32602` (Invalid
params) naming the missing keys.

### Version negotiation

* Modern: test `params._meta["io.modelcontextprotocol/protocolVersion"]` for
  membership in `MODERN_PROTOCOL_VERSIONS`. On no match, return
  `UnsupportedProtocolVersionError` — `error.code = -32022`, `error.data =
  {"supported": [...], "requested": "..."}` — never a bare `-32601`. A
  non-string version is `-32602`, a shape defect, because `-32022` is the one
  code auto-negotiating clients do not fall back from.
* Legacy: one rule, no exceptions. Confirm the requested version when it is in
  `HANDSHAKE_PROTOCOL_VERSIONS`; otherwise — absent, unknown, or a modern-era
  value such as `"2026-07-28"` — counter-offer the newest entry,
  `"2025-11-25"`. The verbatim echo is deleted. `-32022` is never emitted on
  the legacy surface: the handshake revisions mandate a counter-offer ("If the
  server supports the requested protocol version, it **MUST** respond with the
  same version. Otherwise, the server **MUST** respond with another protocol
  version it supports. This **SHOULD** be the *latest* version supported by the
  server"), an error there would be a regression for old clients, and `-32022`
  is a code from a range a legacy client has never heard of. The versioning
  page's advice that a server "**SHOULD** name the protocol versions it
  supports in any error it returns to an `initialize` request" is scoped to "A
  server that supports only modern versions", which this server is not.

`data.supported` and `supportedVersions` are era-scoped: a modern-era answer
lists only `MODERN_PROTOCOL_VERSIONS`. This is an interpretation, and it
departs from the spec's worked example, which is mixed-era (`"supported":
["2026-07-28", "2025-11-25"]`) against a MUST that reads "respond with an
`UnsupportedProtocolVersionError` listing the versions it does support". The
reading taken here is that a modern client is told to "Select a mutually
supported version from `supportedVersions` and continue" in the modern era, so
offering it handshake-only revisions inside a modern envelope would advertise
versions it cannot reach through that envelope. The legacy branch never faces
the question, because it counter-offers instead of erroring.

### Modern wire contract

Everything in this section is modern-era only. Legacy-routed results keep
exactly their current shape: no `resultType`, no `_meta.serverInfo`, no `ttlMs`
and no `cacheScope`. `CacheableResult` does not exist in the handshake
revisions, so stamping those fields on a legacy result would invent wire fields
the client's schema does not define. TASK-58 acceptance criteria 6 and 7 carry
the same qualifier that criterion 5 already carries.

Every modern result carries:

* `resultType: "complete"`. The five tools are fully parameterised by their
  arguments, so the server never emits `"input_required"` and never invents a
  `resultType` value of its own.
* `_meta: {"io.modelcontextprotocol/serverInfo": {"name": "adr-kit",
  "version": server_version()}}`.
* On `server/discover` and `tools/list` only: `ttlMs` and `cacheScope`.
  `cacheScope` is `"public"` because the tool list is identical for every
  caller and carries no user-specific data. `ttlMs` is the Python integer
  `300000`, which bounds post-upgrade staleness to five minutes without
  re-fetching on every call. It is emitted as an `int` deliberately:
  `schema.ts` declares `ttlMs: number` with `@minimum 0` while the generated
  `schema.json` declares `"type": "integer"`, and an integer satisfies both
  readings of that discrepancy.

`server/discover` returns the five required `DiscoverResult` fields —
`resultType`, `supportedVersions` (`list(MODERN_PROTOCOL_VERSIONS)`),
`capabilities` (`{"tools": {}}`, no `listChanged`, no `extensions`), `ttlMs`,
`cacheScope` — plus `_meta.serverInfo` and an `instructions` string. There is no
top-level `serverInfo` and no top-level `protocolVersion`: neither exists in
`DiscoverResult` this revision.

`server/discover` is **not** exempt from envelope validation or version
negotiation, and the two error paths take precedence over the result. This is
the one frame where getting the precedence wrong is expensive, so both cases are
decided here:

* A probe whose `params._meta` omits either required key is answered `-32602`.
  `DiscoverRequest.params` is typed `RequestParams`, which declares `_meta`
  required, and `RequestMetaObject` declares both reserved keys required, so a
  probe without them is malformed and the `-32602` MUST applies unconditionally.
  The consequence is disclosed: a dual-era client reads `-32602` as "any other
  error" and falls back to `initialize`, which still works, while a modern-only
  client that omits the required keys fails — correctly, because it is the
  client that is non-conformant. Conformant probes carry the envelope; the stdio
  page tells clients to probe "setting its preferred modern version in `_meta`".
* A probe declaring a version outside `MODERN_PROTOCOL_VERSIONS` is answered
  `-32022`, not a `DiscoverResult`. This is not self-defeating and does not
  create a chicken-and-egg: `error.data.supported` carries exactly the list
  `supportedVersions` would have carried, and it is the spec's own second probe
  outcome — "The server returns a recognized modern JSON-RPC error such as
  `UnsupportedProtocolVersionError`: the server is modern but does not support
  the requested version. Use one of the versions in its advertised `supported`
  list. Do **not** fall back to `initialize`."

`tools/call` results are **not** cacheable: `CallToolResult` extends `Result`
only, so no `ttlMs` or `cacheScope` appears there. Tool-internal failures stay
`isError: true` inside a `resultType: "complete"` result; an unknown tool name
stays a JSON-RPC error. `tools/list` returns the five tools in the fixed
declaration order of `TOOL_DEFINITIONS`, satisfying the deterministic-ordering
SHOULD.

### Explicitly out of scope

Named so a future reader sees these were decided, not overlooked:

* **Streamable HTTP mechanics** — `Mcp-Method` / `Mcp-Name` headers,
  `x-mcp-header`, session-id removal, `Last-Event-ID`, and
  `HeaderMismatchError` (`-32020`). A newline-delimited stdio transport has no
  HTTP headers, so nothing can mismatch and `-32020` has no reachable code
  path. On stdio, `params._meta` is the only version source.
* **MRTR (multi round-trip requests) / `InputRequiredResult`** — all five tools
  are fully determined by
  their arguments and the server never initiates a request to the client, so it
  always emits `resultType: "complete"` and never parses `inputResponses` or
  `requestState`. It must nonetheless tolerate a client that sends them.
* **`MissingRequiredClientCapabilityError` (`-32021`)** — the server never
  samples, never elicits, and never asks for roots, so it has no code path that
  legitimately emits this error. The shape is safe to ignore and unsafe to emit.
* **Roots, Sampling and Logging deprecations (SEP-2577), `logging/setLevel`,
  the Tasks extension, and `subscriptions/listen`** — all unused. The spec's own
  recommended logging migration for stdio is "log to `stderr`", which is
  already what `bin/adr-mcp:750` and `:754` do. These three are the features to
  which the lifecycle policy's minimum twelve-month deprecation window actually
  applies: the registry gives them an earliest removal of "First revision
  released on or after 2027-07-28", and `schema.ts` says of
  `io.modelcontextprotocol/logLevel` that it "Remains in the specification for
  at least twelve months". None of them is implemented here, so the window is
  irrelevant to adr-kit. `ping` disappears from the modern surface but is
  retained on the legacy one, where it is still defined.
* **Request-scoped notifications (`notifications/cancelled`,
  `notifications/progress`)** — accepted and ignored.
  `CancelledNotification` (`schema.ts:648-650`) is the only client notification
  in this revision and the only cancellation mechanism on stdio; `bin/adr-mcp`
  already drops every `notifications/*` frame without replying
  (`bin/adr-mcp:683-685`), and that behaviour is preserved. It is conformant:
  the notification rules forbid a response, the five tool handlers are
  synchronous subprocess calls that cannot be interrupted mid-flight, and the
  server emits nothing further for a cancelled request, satisfying "Servers
  … **MUST NOT** send any further messages for it". `progressToken` is likewise
  read and ignored, so no `notifications/progress` is ever emitted.
* **Closing the era gap for envelope-less requests** — a request that carries
  no `_meta` at all is served under legacy semantics by design. On stdio a
  modern client that forgot its envelope and a legacy `tools/list` are
  byte-identical, so no rule can separate them without inventing state; the
  Base Protocol `-32602` MUST for a malformed envelope is therefore unreachable
  for such a frame. Reproduced defect 3 is closed for enveloped requests, which
  is every conformant modern request.
* **`capabilities.extensions`** — none declared; any client-advertised
  extension is ignored, which is permitted because the MUST-revert-or-reject
  clause binds only the party that supports the extension.

### Revisit trigger

This decision turns on dependency weight, not on API quality. If a future
`mcp` release adds a lazy-import or extras boundary so that a stdio tools-only
server no longer pays for the HTTP client and web-server stack, the trade-off
changes materially and this decision should be revisited by supersession. Whether
today's eager import is an upstream defect or a deliberate packaging choice is
unresolved upstream — no issue was found — but the answer does not change the
decision, only the date on which it is worth re-measuring.

### Confirmation

The suite has since landed, which is why `verified_in` names it.
`tests/test_adr_mcp.py` carries the conformance suite for gate
`adr-mcp-dual-era-v1`, driving all three shapes through `serve()` — the legacy
`initialize` handshake, a stateless request carrying the modern `_meta` envelope
with no prior `initialize`, and `server/discover` — and asserting:

* Modern `-32022` payload shape (`data.supported`, `data.requested`) for a
  version outside `MODERN_PROTOCOL_VERSIONS`.
* Legacy `initialize` counter-offers `"2025-11-25"` for an absent
  `protocolVersion`, for a nonsense string, and for `"2026-07-28"`, and never
  returns `-32022`. This is the assertion that inverts today's behaviour;
  `test_initialize_echoes_client_protocol_version` passes unchanged because it
  sends the declared version `"2024-11-05"`, so it is renamed
  `test_initialize_confirms_declared_protocol_version` and joined by the
  undeclared-version cases that nothing covers today.
* `-32602` on a modern-routed request with an incomplete envelope.
* `server/discover` with no `_meta` → `-32602`; `server/discover` declaring an
  unsupported version → `-32022`, not a `DiscoverResult`.
* An enveloped `ping` → `-32601`.
* A bare frame after a modern-enveloped frame is still answered under legacy
  semantics, pinning the absence of an era lock.
* `resultType` and `_meta.serverInfo` present on every modern result and absent
  from every legacy result.
* `ttlMs` / `cacheScope` on `server/discover` and `tools/list`, absent on
  `tools/call`, and absent from all legacy results.
* Deterministic tool order across `tools/list` calls.

## Decision Contract

### Must

* `bin/adr-mcp` declares its supported protocol versions in explicit
  `HANDSHAKE_PROTOCOL_VERSIONS` / `MODERN_PROTOCOL_VERSIONS` /
  `KNOWN_PROTOCOL_VERSIONS` tuples and answers only from that set.
* `bin/adr-mcp` implements `server/discover` and returns all five required
  `DiscoverResult` fields.
* A request routed to the modern era is answered with `resultType`,
  `_meta["io.modelcontextprotocol/serverInfo"]`, and — for `server/discover`
  and `tools/list` — an integer `ttlMs` and a `cacheScope` of `"public"`.
* A modern-routed request declaring a version outside
  `MODERN_PROTOCOL_VERSIONS` is answered `-32022` with `data.supported` and
  `data.requested`, including when the method is `server/discover`.
* A legacy `initialize` naming a version outside `HANDSHAKE_PROTOCOL_VERSIONS`,
  or naming none, is answered with a counter-offer of `"2025-11-25"`.
* Era selection is a pure function of the frame being answered
  (`server/discover` or the `io.modelcontextprotocol/protocolVersion` sentinel →
  modern; anything else → legacy), never from configuration and never from
  process state.
* `bin/adr-mcp` runs on the Python standard library with zero third-party
  runtime imports, and `codex/bin/adr-mcp` and `copilot/bin/adr-mcp` stay
  byte-identical to it.

### Must Not

* No response may reflect a client-supplied `protocolVersion` that is not a
  member of the declared set for that era.
* No request carrying the `io.modelcontextprotocol/protocolVersion` sentinel
  may be answered under legacy semantics, whatever arrived earlier on the same
  stdin. There is no era lock and no connection-scoped era state.
* `-32022` must not appear in a response to `initialize`.
* No legacy-routed result may carry `resultType`, `_meta.serverInfo`, `ttlMs`
  or `cacheScope`.
* `bin/adr-mcp` and its two shipped mirrors must not import `mcp`, `mcp_types`,
  `pydantic`, or any other third-party package.
* The server must not emit `-32020` or `-32021`, nor any undefined code in the
  spec-reserved `-32020`..`-32099` range, and must not allocate new codes in
  the legacy `-32000`..`-32019` range.
* `tools/call` results must not carry `ttlMs` or `cacheScope`.

### Exceptions

* The `mcp` and `mcp-types` 2.0.0 sources may be read, and their patterns
  copied, as reference material. That is documentation, not a dependency.
* `ping` remains implemented for legacy clients although revision `2026-07-28`
  removes it. It is reachable on a modern-routed request — any frame carrying
  the sentinel routes modern, including `ping` — and the answer there is
  `-32601`, with no result stamping, because there is no result to stamp.

### Verification

* `tests/test_adr_mcp.py` — the conformance suite described under Confirmation,
  carrying the gate id `adr-mcp-dual-era-v1`. This is where every positive
  obligation of this contract is verified. It ships, carrying the gate anchor,
  and `verified_in` names it.
* `bin/adr-judge` declarative rules from the Enforcement block below. They are
  deliberately negative only — a `forbid_pattern` tripwire against the version
  echo and a `forbid_import` allowlist for the zero-dependency rule. No
  `require_pattern` rule is declared: `require_pattern` is evaluated against
  the post-image of every diffed file matching its glob, so a code-presence
  rule on a file under active development blocks every incremental commit and
  fails closed under `--snapshot diff` (the CLI default, and what the
  `adr_judge` MCP tool passes at `bin/adr-mcp:469`). Presence is a test's job.
* The semantic obligations that no regex can express — `resultType` stamping,
  `cacheScope: "public"`, the `-32022` `data` shape, era routing, cache hints
  absent from `tools/call` — are covered by the conformance suite and human
  review, not by the LLM judge. `llm_judge` is `false`: the pass is off in this
  repository anyway (`docs/adr/.adr-kit.json` sets no `judge.llm_enabled`, and
  per ADR-001 it is opt-in), and `bin/adr-judge`'s `extract_decision` resolves
  the MADR `## Decision Outcome` heading only, so `## Decision Contract` — every
  Must and Must Not above — would not reach the prompt.

## Consequences

### Positive

* Zero runtime dependencies survive: no ASGI (Asynchronous Server Gateway
  Interface) stack, no cryptography stack, no
  OpenTelemetry, no native wheels, and no 14.6 MiB install in a plugin cache
  the project does not control.
* Modern-only clients get a conformant server instead of a silent legacy
  session, and legacy clients keep working for as long as they exist, with one
  visible behaviour change: a client that omits `protocolVersion` on
  `initialize` is now counter-offered `"2025-11-25"` instead of the current
  `DEFAULT_PROTOCOL_VERSION` of `"2025-06-18"` (`bin/adr-mcp:53`).
* The version-echo defect is replaced by an inspectable declared set, so the
  server can no longer claim to speak a revision it does not implement.
* Failures become actionable: `-32022` hands the client a `supported` list it
  can retry against, and `-32602` names the missing envelope key.
* The reference-reading approach captures the SDK's best ideas — enumerated
  version sets, one sentinel for era detection, one outbound stamping seam —
  at the cost of reading rather than importing.

### Negative

* adr-kit now owns a wire-format implementation that tracks an evolving
  specification by hand. Every future revision is manual work that an SDK
  dependency would have absorbed. Mitigation: the surface is five methods, the
  conformance suite pins the shapes, and the SDK stays readable as a reference.
* Serving two eras from one process is more code than either era alone — a
  classification step and two result-shaping paths — though not more state:
  refusing the permitted era lock keeps the dispatch loop as state-free as it is
  today.
* Refusing the era lock has a cost. A modern client that omits its envelope on
  a follow-up request is served under legacy semantics rather than being told
  it is malformed, because on stdio that frame is indistinguishable from a
  legacy request. Named under "Explicitly out of scope"; the alternative would
  be exactly the history-dependent behaviour the statelessness rule forbids.
* Enforcement covers less than the decision states. Only two negative rules are
  mechanical; everything positive rests on a conformance suite that does not
  exist yet, so between acceptance and implementation this ADR is a promise, not
  a guard. This gap is deliberate and visible rather than hidden: `verified_in`
  stays empty until the suite lands, so `bin/adr-readiness` reports the gap
  instead of a green light, and the Enforcement block carries no
  `require_pattern` rule precisely so that accepting ahead of implementation
  cannot block the incremental commits that TASK-58 needs. The residual risk is
  that the decision is binding while nothing mechanical checks its positive
  half; the mitigation is that TASK-58 lands the suite under gate
  `adr-mcp-dual-era-v1`, which `bin/adr-lint` requires to exist somewhere in the
  tree for an Accepted `binding: true` ADR.
* Hand-rolled cache hints and `resultType` stamping can drift from the schema
  in ways a validating SDK would catch at runtime; the conformance tests are
  the only backstop.
* The one test that names this defect,
  `test_initialize_echoes_client_protocol_version`
  (`tests/test_adr_mcp.py:203`), passes unchanged: it sends the declared version
  `"2024-11-05"`, where echo and correct confirmation are the same answer. The
  fix is therefore *not* visible as a flipped assertion in review. It has to be
  made visible by renaming that test and adding the undeclared-version cases,
  which is why they are itemised under Confirmation.

## Pros and Cons of the Options

### Dual-era hand-rolled server, SDK as reference (chosen)

* Good, because it keeps zero runtime dependencies while reaching full
  conformance for the surface the server actually exposes.
* Good, because the SDK's design lessons are available for free: the
  enumerated version registry, the reserved-prefix sentinel for era detection,
  one dispatch kernel with the era as a field, and one outbound seam that
  stamps `resultType`, cache hints and `serverInfo` in a documented order.
* Good, because era selection stays derived from the wire, which is what the
  spec prescribes for a dual-era server ("A dual-era **server** selects its
  behavior from how the client opens").
* Bad, because adr-kit carries the maintenance burden of protocol evolution
  by hand.

### Adopt `mcp` 2.0.0 as a runtime dependency

* Good, because the SDK already implements the whole dual-era model correctly,
  including `server/discover`, the classification ladder, per-`(method,
  version)` reachability, and the outbound stamping seam. The API surface a
  tools-only stdio server needs is genuinely small — roughly six to ten names
  (`Server`, `on_list_tools`, `on_call_tool`, `ServerRequestContext`,
  `stdio_server`, `create_initialization_options`).
* Good, because adr-kit never used `mcp` 1.x, so the 1.x-to-2.0 migration cost
  the upstream guide documents is zero for this project.
* Bad, because 30 packages and 14.6 MiB with 5 native wheels is a
  disproportionate cost for a five-tool read-only server, and it lands in
  plugin caches across three marketplaces (ADR-012) on machines adr-kit does
  not control.
* Bad, because `import mcp.server.stdio` loads 571 modules and eagerly pulls
  `httpx2`, `starlette`, `uvicorn`, `sse_starlette`, `cryptography` and
  `opentelemetry` — an HTTP client and a web server for a stdio process. There
  is no lazy-import or extras boundary at this version.
* Bad, and this is the decisive number: the measured **+3.7 s** import would be
  paid once per server process, which the persistent `for line in sys.stdin:`
  loop softens — but the five tools are subprocess calls into one-shot CLIs, and
  any of that dependency reaching them would cost +3.7 s **per tool call**,
  before doing any work. One of those CLIs, `bin/adr-lint`, carries a committed
  budget in `tests/fixtures/cli/latency-corpus.json` of 1200 ms p50 and a
  2000 ms hard timeout, so the import alone would break a budget that is
  already enforced by a test today.
* Bad, because the release is one day old with no patch version, three bug
  issues filed within ~36 hours, and upstream's own advice to pin
  `mcp>=1.28,<2` until migrated. The release notes also contradict the README
  on whether 1.x still receives bug fixes or only security fixes.
* Bad, because it imposes an async/anyio execution model on a synchronous
  server and turns OpenTelemetry tracing on by default.

### Adopt only `mcp-types` 2.0.0

* Good, because it is the honest middle of the spectrum: 6 packages, 2.56 MiB,
  +738 ms import, giving schema-accurate models and the version registry while
  keeping the existing loop. Upstream designed it for exactly this
  ("Its only runtime dependencies are pydantic and typing-extensions, so it can
  be installed on its own").
* Bad, because it buys types, not behaviour: `server/discover`, era detection,
  negotiation and the outbound stamping still have to be written by hand, so
  the maintenance burden barely moves.
* Bad, because it trades the zero-dependency property — the thing actually
  worth protecting — for convenience, adding `pydantic` and a native
  `pydantic_core` wheel to a plugin cache.
* Bad, because the registry it provides is ~25 lines of stdlib tuples that can
  simply be copied.

### Modern era only

* Good, because it is the least code and matches where the ecosystem is going.
* Bad, because legacy clients have no fall-forward mechanism at all: the
  compatibility matrix marks `Legacy client / Modern server` as **Fails**, with
  the note "Legacy clients have no fall-forward mechanism". Dropping
  `initialize` would break every currently-shipping client, with no deadline by
  which they are obliged to migrate — `2025-11-25` and earlier remain valid
  published revisions.

### Do nothing

* Good, because dual-era clients already work: the `-32601` on
  `server/discover` is read as "legacy" and they fall back to `initialize`, and
  the fallback must not be keyed to a specific error code.
* Bad, because it leaves an unconditional server MUST unimplemented, leaves the
  server claiming to speak `2026-07-28` while implementing none of it, and
  leaves modern-only clients silently served under legacy semantics — the exact
  era-ambiguity the spec warns about, reproduced above.

## Related Decisions

* **ADR-011 (Adopt Deterministic Readiness and Human-Gated Grilling Across the
  ADR Lifecycle)**: extends, does not supersede. ADR-011 governs the readiness
  engine and the human-gated grilling workflow; the MCP server is one of its
  consumption surfaces ("MCP exposes readiness only"), which is why it names
  `bin/adr-mcp:1` in its References and requires `adr_readiness` in its
  Enforcement block. This ADR changes only how that surface speaks on the wire.
  It preserves both ADR-011 invariants: the tool set stays read-only with no
  lifecycle mutation, and the server stays key-free. ADR-011 also states a
  100 ms MCP adapter overhead target — non-binding (`binding: false`, `gate:
  null`, `verified_in: []`), so a target rather than an enforced contract; an
  in-process dict response stays far below it.
* **ADR-015 (Enforce a Two-Second Deterministic Latency Budget as a Test
  Fixture Contract)**: complements. This ADR reads ADR-015 by its enforced
  scope, consistently and in both directions. That scope is
  `tests/fixtures/cli/latency-corpus.json`, which today carries entries for
  `adr-lint` and `adr-retire` only; `adr-mcp` has none, and neither do the other
  wrapped CLIs. Read broadly, ADR-015's Must ("Every deterministic user-facing
  CLI or hook path keeps a p50/p95/hard-budget entry in a committed latency
  fixture") would want an `adr-mcp` entry, and `server/discover` is a new
  user-facing method. TASK-58 deliberately does not add one, and the gap is
  recorded here rather than argued away: the measured paths are the wrapped
  CLIs, and `server/discover` adds one in-process dict response on an
  already-running persistent process — no subprocess, and no file read beyond
  the `server_version()` manifest read that already happens. If `adr-mcp` ever
  gains a path that spawns or scans per request, it needs a corpus entry. The
  rejected SDK option is rejected on the `adr-lint` budget that does exist, as
  recorded above.
* **ADR-001 (Make Per-Commit LLM Gates Opt-In)**: complements; the key-free
  property this ADR preserves is why `adr_judge` never passes `--llm`.
* **ADR-010 (Certify Three Native CLI Clients Through One Outcome Contract)**:
  depends on; the MCP server is shipped through the same client certification
  contract, so a wire-format change must not alter tool names or schemas.
* **ADR-012 (Release to the Three Coding-Agent Marketplaces from the Public
  Repository)**: constrains; the server is installed into plugin caches on
  machines adr-kit does not control, which is why dependency weight is a
  first-order concern rather than a preference.

## References

* MCP schema, revision 2026-07-28 —
  <https://modelcontextprotocol.io/specification/2026-07-28/schema>, verified
  against the authoritative sources
  <https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/schema/2026-07-28/schema.ts>
  (3,197 lines) and `.../schema/2026-07-28/schema.json` plus the shipped
  `examples/` fixtures. Note the rendered docs page is incomplete: its Schema
  Reference omits `DiscoverRequest`, `DiscoverResult`, `ServerCapabilities` and
  `Implementation`, which is enough reason to drive implementation from
  `schema.ts` / `schema.json`. Two nearby absences are *not* defects and are
  recorded so nobody chases them: `CacheableResult` is marked `@internal` in
  `schema.ts` (as is `PaginatedResult`), so the generator drops it by design;
  and `Result.resultType` really is `"type": "string"` in `schema.json` because
  `schema.ts` declares `export type ResultType = "complete" | "input_required" |
  string`, a union that collapses to `string`. The `_meta` objects
  (`RequestMetaObject`, `ResultMetaObject`) are present on the page.
* Versioning and Compatibility —
  <https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning>:
  the modern / legacy / dual-era terminology, the seven-row compatibility
  matrix, and "A dual-era **server** selects its behavior from how the client
  opens".
* Base Protocol overview —
  <https://modelcontextprotocol.io/specification/2026-07-28/basic>: the
  reserved `_meta` key table, the per-request protocol fields table, the
  `-32602` rejection MUST for a malformed envelope, and the error-code
  allocation policy for `-32020`..`-32099`.
* Tools —
  <https://modelcontextprotocol.io/specification/2026-07-28/server/tools> and
  caching —
  `.../2026-07-28/server/utilities/caching`: `ttlMs` >= 0, `cacheScope`
  `"public"` for tool lists identical across users, deterministic ordering
  SHOULD, and `tools/call` absent from the cacheable-operation list.
* stdio transport, Backward Compatibility and Cancellation —
  <https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio>:
  the three probe outcomes ("The server returns any other error, or does not
  respond within a reasonable timeout: the server is legacy. Fall back to the
  `initialize` handshake."), "The fallback **MUST NOT** be keyed to one
  specific error code", and the `notifications/cancelled` rules.
* Deprecated features registry and changelog —
  <https://modelcontextprotocol.io/specification/2026-07-28/deprecated> and
  `.../changelog`: the six Deprecated entries and the empty Removed section,
  changelog Major change 2 ("Make MCP stateless: remove the
  `initialize`/`notifications/initialized` handshake"), and the governance entry
  adopting "a minimum twelve-month deprecation window" — which binds Deprecated
  features, not removed ones, and so does not apply to the handshake.
* Legacy handshake version negotiation —
  <https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle>:
  "If the server supports the requested protocol version, it **MUST** respond
  with the same version. Otherwise, the server **MUST** respond with another
  protocol version it supports." Cross-checked against the published
  `schema.ts` files for `2024-11-05`, `2025-03-26`, `2025-06-18` and
  `2025-11-25` (1,117 / 1,258 / 1,613 / 2,582 lines) for the unchanged
  tools-only subset claim: `InitializeRequest`, `InitializeResult`,
  `ListToolsRequest`, `ListToolsResult` and `PingRequest` carry the same fields
  in all four; `CallToolResult` differs only by the additive optional
  `structuredContent` (`2025-06-18`) and a widened `content` union.
* SEP-2575 (`server/discover`, `subscriptions/listen`), SEP-2577 (Roots,
  Sampling, Logging deprecation), SEP-2322 (multi round-trip requests) —
  <https://modelcontextprotocol.io/specification/2026-07-28/changelog>.
* `mcp` Python SDK 2.0.0, published 2026-07-28T13:45:28Z —
  <https://pypi.org/project/mcp/2.0.0/> and
  <https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.0.0>.
  Read at the `v2.0.0` tag (`git describe --tags` = `v2.0.0`, commit
  `6f69a37`) from two independent roots verified byte-identical modulo
  carriage-return/line-feed (CRLF) endings. Patterns
  borrowed: `src/mcp-types/mcp_types/version.py` (three-way registry,
  `is_version_at_least`), `src/mcp/server/runner.py:504`
  (`_has_modern_envelope` sentinel), `:341` (`_serialize` stamping order),
  `:602` (`serve_dual_era_loop`), `src/mcp/shared/inbound.py:370`
  (`classify_inbound_request` ladder).
* Dependency measurements (Windows 11, Python 3.12.9, pip 26.0.1,
  `--dry-run --report`, median of 9 subprocess spawns): `mcp==2.0.0` = 30
  packages / 15,277,675 bytes / 5 native wheels / 571 modules imported /
  +3.7 s; `mcp-types==2.0.0` = 6 packages / 2.56 MiB / +738 ms; current
  `bin/adr-mcp` = 0 packages / 28,075 bytes / ~0 ms. Absolute figures are
  win32-only; the ratios are the portable part. Linux and macOS not measured.
* Reproduced defects: `bin/adr-mcp:53` (`DEFAULT_PROTOCOL_VERSION`),
  `:639-646` (`handle_initialize` verbatim echo), `:669-705` (`dispatch`, no
  era or ordering validation), `:683-685` (`notifications/*` dropped without
  reply), `:710` (persistent `for line in sys.stdin:` loop);
  `tests/test_adr_mcp.py:203`
  (`test_initialize_echoes_client_protocol_version`, which sends the declared
  version `"2024-11-05"` and therefore does not distinguish echo from
  confirmation). The file ships in triplicate via
  `clients/installer/payload.py:175`; `bin/adr-mcp`, `codex/bin/adr-mcp` and
  `copilot/bin/adr-mcp` are 28,075 bytes each.
* Enforcement behaviour reproduced against `bin/adr-judge` rather than reasoned
  about: `require_pattern` compiles with `re.MULTILINE` only and is evaluated
  over `read_snapshot_content` post-images, and `_read_snapshot_content` returns
  `unknown` — a fail-closed violation — for any modified (non-new) file under
  `--snapshot diff`. With this ADR flipped to Accepted in a scratch copy, a diff
  adding one unrelated docstring line to `bin/adr-mcp` produced 3 spurious
  violations under `--snapshot worktree` and 4 under `--snapshot diff`. That is
  why the Enforcement block declares no `require_pattern` rule.
* TASK-58 in `backlog/tasks/` — the twelve acceptance criteria this decision
  backs.

## Open Questions

None. The one unresolved upstream matter — whether `mcp` 2.0.0's eager
HTTP/ASGI import is a defect or a packaging choice — is recorded as a revisit
trigger under Decision Outcome rather than as an open question, because its
answer changes when to re-measure, not what to decide.

## Enforcement

Scoped to all three shipped copies of the file. The two `forbid_*` rules
describe things that must never appear, so neither depends on the
implementation existing. The four `require_pattern` rules were added on
2026-07-31, once both preconditions recorded below had actually been met — see
"Why `require_pattern` was empty at acceptance".

```json
{
  "forbid_pattern": [
    {
      "pattern": "requested if isinstance\\(requested, str\\)",
      "path_glob": "{bin,codex/bin,copilot/bin}/adr-mcp",
      "message": "Do not re-introduce the verbatim protocolVersion echo: negotiate against the declared sets, confirm or counter-offer on the legacy surface, and return -32022 on the modern one (ADR-016)."
    }
  ],
  "forbid_import": [
    {
      "pattern": "^[ \\t]*(?:from[ \\t]+(?!(?:__future__|argparse|collections|dataclasses|enum|functools|json|os|pathlib|re|shutil|subprocess|sys|textwrap|time|typing)\\b)[A-Za-z_][\\w.]*[ \\t]+import\\b|import[ \\t]+(?!(?:__future__|argparse|collections|dataclasses|enum|functools|json|os|pathlib|re|shutil|subprocess|sys|textwrap|time|typing)\\b)[A-Za-z_][\\w.]*[ \\t]*(?:,|as\\b|#|$))",
      "path_glob": "{bin,codex/bin,copilot/bin}/adr-mcp",
      "message": "adr-mcp is stdlib-only with zero runtime dependencies (ADR-016). Only the listed standard-library modules may be imported; the mcp SDK is a reference to read, not to import. Adding another stdlib module means amending this allowlist."
    }
  ],
  "require_pattern": [
    {
      "pattern": "MODERN_PROTOCOL_VERSIONS",
      "path_glob": "{bin,codex/bin,copilot/bin}/adr-mcp",
      "message": "The modern-era version set must stay declared: era routing is a pure function of the frame and needs an enumerated set to match against (ADR-016)."
    },
    {
      "pattern": "server/discover",
      "path_glob": "{bin,codex/bin,copilot/bin}/adr-mcp",
      "message": "server/discover is the modern era's entry point; removing it strands every client that does not send the reserved _meta key (ADR-016)."
    },
    {
      "pattern": "UNSUPPORTED_PROTOCOL_VERSION",
      "path_glob": "{bin,codex/bin,copilot/bin}/adr-mcp",
      "message": "-32022 must remain reachable on the modern surface; the handshake counter-offers instead, so this is the only path that can refuse a version (ADR-016)."
    },
    {
      "pattern": "server/discover",
      "path_glob": "tests/test_adr_mcp.py",
      "message": "The conformance suite must keep exercising server/discover: it is the gate adr-mcp-dual-era-v1 (ADR-016)."
    }
  ]
}
```

### Why `require_pattern` was empty at acceptance

> **Resolved 2026-07-31 (TASK-58.5).** The four rules are now in the block
> above. Both blockers below were removed by later work rather than argued
> away, and the original reasoning is kept verbatim as the historical record.
>
> The first failure mode was conditional on the implementation being absent; it
> ended when TASK-58.1 and TASK-58.2 landed. The second — the one called
> permanent — was fixed by TASK-65, which is the very change this section
> called for two paragraphs down ("`bin/adr-mcp:469` should pass
> `--snapshot worktree` rather than `diff`"). `require_pattern` under
> `--snapshot diff` now emits an **advisory** instead of a violation, and the
> MCP tool asks for `worktree`.
>
> Re-measured against the shipped implementation before adding the rules, not
> predicted: an innocent one-line change to `bin/adr-mcp` draws 0 violations
> under `worktree` and 4 advisories under `diff`; a copy with the modern
> surface stripped draws 3 violations naming each missing symbol. The rules
> distinguish the compliant implementation from a breach, which is the bar this
> section set for not shipping a decorative rule.

Declined, not deferred. The acceptance record above anticipated deferring these
rules to TASK-58.5; on the evidence below the correct answer is stronger than a
deferral, because one of the two failure modes never goes away. Both were
reproduced against `bin/adr-judge` rather than predicted.

First, a `require_pattern` is evaluated against the post-image of every diffed
file matching its `path_glob`, so a rule requiring `MODERN_PROTOCOL_VERSIONS` or
`server/discover` fails on *any* commit touching `bin/adr-mcp` until the whole
implementation has landed — and then on every later unrelated edit if any part
is ever refactored under a different name. With this ADR flipped to Accepted in
a scratch copy, a one-line docstring change to `bin/adr-mcp` drew three
violations. That forces TASK-58 into one atomic commit and pushes the author
toward `ADR_KIT_HOOK_DISABLE=1`, which defeats the enforcement floor this
repository relies on (ADR-004).

Second, the failure is not transient. `bin/adr-judge`'s `--snapshot diff` — the
CLI default, and what the `adr_judge` MCP tool hardcodes at `bin/adr-mcp:469` —
has no post-image for a modified file and fails closed, so every
`require_pattern` on `bin/adr-mcp` reports a violation through that tool
regardless of file content, forever. ADR-011's existing rule already does this:
one spurious violation today, five if these four had been added. The pre-commit
hook is unaffected because it passes `--snapshot staged`, which is why a
regex-only check misses this.

The `forbid_*` rules have neither failure mode: they match only added lines in
the diff, so they fire on re-introduction and are silent otherwise. Positive
obligations belong in the conformance suite named under Verification, which is
the pattern ADR-015 uses. Separately, `bin/adr-mcp:469` should pass
`--snapshot worktree` rather than `diff`; `diff` is the wrong default for a tool
whose caller has a worktree. That is a TASK-58 opportunity, not a requirement of
this decision.

`llm_judge` does not cover the gap either, and is set `false` for two reasons
given under Verification: the pass is off in this repository, and
`bin/adr-judge`'s `extract_decision` resolves only the MADR `## Decision
Outcome` heading, so the Must / Must Not text it would need to judge against
never reaches the prompt. Adding a declarative rule later would be a mechanical
tightening rather than a change to the decision — the Decision Contract already
states each requirement as binding — but on the evidence above no
`require_pattern` on `bin/adr-mcp` is worth adding, and the conformance suite is
where these obligations are checked.
