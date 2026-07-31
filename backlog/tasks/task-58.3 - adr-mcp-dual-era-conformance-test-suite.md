---
id: TASK-58.3
title: 'adr-mcp: dual-era conformance test suite'
status: Done
assignee: []
created_date: '2026-07-29 22:48'
updated_date: '2026-07-30 21:25'
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

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
58 tests in `tests/test_adr_mcp.py` (39 before), all driven as real newline-delimited JSON-RPC through `serve()`. Full suite: 1001 passed, 5 skipped.

**The no-era-lock property is pinned in both directions**, which is the assertion most likely to regress. One ordered session shows a modern frame after a legacy `initialize` still routing modern, and a bare frame after modern frames still routing legacy — with both `tools/list` bodies asserted identical, so the same request demonstrably gets two era shapes decided only by its own bytes.

**The legacy golden has teeth.** Captured by driving frames through `git show 7d067a2:bin/adr-mcp` — the last commit before TASK-58.1 — against the same fixture, then byte-compared. A negative control was run: mutating the golden's `ping` result is caught on the byte path, mutating a count inside the `adr_status` payload on the structural path. Seven of eight frames are byte-exact.

**Open question 1 resolved with reasoning, and the implementation was found correct.** ADR-016's Decision Contract Must is unqualified by method — "including when the method is `server/discover`" is emphasis on the hardest case, not a restriction to it — while the Confirmation bullet naming `-32601` for an enveloped `ping` sits in a list where every other bullet names its envelope defect explicitly, so it describes the conformant-envelope case. Both are now pinned: `-32601` with a valid envelope, `-32022` with an unsupported version. The reasoning is in the test docstring. `-32022` is also the more useful answer, because `-32601` would tell a 2025-06-18 client that `ping` does not exist when the truth is that its version cannot be spoken through an envelope.

**Open question 2 resolved as asked**, on emitted frames rather than file text: a 13-frame error battery plus two raw malformed lines, reading codes off every stdout line including the id-less parse-error frames. The assertion is the full Must Not via an allowlist covering both halves of the reserved range, and it asserts set equality so no allowlist entry sits there unobserved.

**Three caveats worth carrying forward.**

The brief's "non-string version gives -32602" was ambiguous about era: on `initialize` the implementation must counter-offer, since `-32022` may never reach it. Only the modern envelope gives `-32602`. Both readings are pinned with the asymmetry explained.

`adr_status` is compared structurally rather than byte-exactly, for three documented reasons — and two of them were newly found here, beyond the key-order caveat handed over from TASK-58.1: `avg_age_days`/`age_days` are computed from today's real date, so a byte golden would go stale overnight, and `retrieval.index_error` quotes a native OS path. The third is a genuine defect in `bin/adr-status` and is now TASK-66.

Python 3.10 is **not verified**. It is not installed on this machine (checked `py --list`, `where python`, the Programs\Python tree and conda envs). Passes on 3.12.9 and 3.14.0. The agent audited by review for 3.11+ syntax and found none, but CI's 3.10 leg remains the real check — reported as a gap rather than claimed as coverage.

Also cleaned up: the comment block above the old gate test still described an `xfail(strict=True)` marker that TASK-58.2 had already removed. Rewritten to state the gate is live; `GATE_ADR_MCP_DUAL_ERA_V1` is retained so `bin/adr-lint`'s gate-existence check still resolves.
<!-- SECTION:FINAL_SUMMARY:END -->
