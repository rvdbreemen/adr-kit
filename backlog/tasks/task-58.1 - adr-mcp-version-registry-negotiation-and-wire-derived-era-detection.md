---
id: TASK-58.1
title: 'adr-mcp: version registry, negotiation and wire-derived era detection'
status: To Do
assignee: []
created_date: '2026-07-29 22:47'
updated_date: '2026-07-30 05:26'
labels:
  - mcp
  - protocol
dependencies: []
references:
  - >-
    docs/adr/ADR-016-serve-both-mcp-protocol-eras-from-one-hand-rolled-stdio-server.md
  - docs/research/2026-07-29-mcp-2026-07-28-revision.md
modified_files:
  - bin/adr-mcp
parent_task_id: TASK-58
priority: high
ordinal: 59500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
First implementation slice of ADR-016 (Accepted 2026-07-30). Replaces the version-echo defect and establishes which era a frame belongs to, without yet changing result shapes.

CORRECTED 2026-07-30: an earlier version of this task described a three-rule ladder with process state and returned -32022 on `initialize`. The final ADR forbids both. The rules below are the Accepted ones.

**Version registry** — replace `DEFAULT_PROTOCOL_VERSION` (`bin/adr-mcp:53`) with three tuples, treating versions as an enumerated set and never as a sortable scalar:

- `HANDSHAKE_PROTOCOL_VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25")`
- `MODERN_PROTOCOL_VERSIONS = ("2026-07-28",)`
- `KNOWN_PROTOCOL_VERSIONS` — their concatenation, oldest first

Membership tests are set lookups. An unrecognised peer string is never ordered against a known one, because date strings only happen to sort lexicographically and `"zzz" > "2025-11-25"` is true.

**Meta keys** — add the five reserved constants verbatim: `io.modelcontextprotocol/protocolVersion`, `/clientCapabilities`, `/clientInfo`, `/serverInfo`, `/logLevel`.

**Era detection — a PURE FUNCTION of the single frame being answered.** The server keeps NO per-process era state, so the same bytes always get the same answer. Exactly two rules:

1. `method == "server/discover"`, or `params._meta` contains `io.modelcontextprotocol/protocolVersion` -> modern. The sentinel is that one key, not the required pair: its prefix is spec-reserved so a legacy client cannot mint it, while a bare `_meta` is not evidence (legacy requests already put `progressToken` there). Checking only the version key means a half-built envelope still routes modern and gets a `-32602` naming the missing key, instead of being misrouted to legacy and failing confusingly.
2. Any other frame — including `initialize` and `notifications/initialized` — -> legacy.

There is deliberately NO third rule and NO era lock. The spec would permit a lock, but a lock makes a byte-identical frame get two different answers depending on what arrived earlier on the same stdin, which is what "Servers MUST NOT rely on prior requests over the same connection to establish context" forbids.

Routing signal and validation stay separate: a modern-routed request missing protocolVersion or clientCapabilities gets `-32602` naming the missing keys.

**Negotiation**
- Modern: test the requested version against `MODERN_PROTOCOL_VERSIONS`. On no match return `-32022` with `error.data = {"supported": [...], "requested": "..."}`, including when the method is `server/discover`. A non-string version is `-32602`, a shape defect.
- Legacy: confirm a version that is in `HANDSHAKE_PROTOCOL_VERSIONS`. A version outside that set, or no version at all, gets a COUNTER-OFFER of `"2025-11-25"`. `-32022` MUST NOT appear in a response to `initialize` — the legacy handshake contract is counter-offer-based, and answering an unknown version with an error would break negotiation for older clients. The verbatim echo is deleted.

Reference implementation read for this slice: `mcp` SDK 2.0.0, `src/mcp/server/runner.py:504-517` (`_has_modern_envelope`) and `src/mcp-types/mcp_types/version.py`. Note that the SDK DOES lock the era per connection (`serve_dual_era_loop`, `:602-640`); ADR-016 deliberately diverges and keeps era a pure per-frame function. Do not copy the lock.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `DEFAULT_PROTOCOL_VERSION` is gone; the three version tuples exist with exactly the values above
- [ ] #2 The five `io.modelcontextprotocol/*` meta-key constants exist and match the spec spelling character for character
- [ ] #3 Era is derived from the single frame only; no per-process or per-connection era state exists anywhere in the file
- [ ] #4 A frame carrying the protocolVersion sentinel routes modern even when it arrives after a legacy initialize on the same stdin
- [ ] #5 A request with a bare `_meta` carrying only `progressToken` routes legacy, not modern
- [ ] #6 `initialize` routes legacy even when the modern envelope is stamped on it
- [ ] #7 A modern-routed request missing protocolVersion or clientCapabilities returns -32602 naming the missing key(s)
- [ ] #8 A modern request naming an unsupported version returns -32022 with supported and requested in error.data, including on server/discover
- [ ] #9 `initialize` naming a version outside HANDSHAKE_PROTOCOL_VERSIONS, or naming none, gets a counter-offer of 2025-11-25
- [ ] #10 No response to `initialize` ever carries -32022
- [ ] #11 No code path reflects a client-supplied version string back unvalidated
<!-- AC:END -->
