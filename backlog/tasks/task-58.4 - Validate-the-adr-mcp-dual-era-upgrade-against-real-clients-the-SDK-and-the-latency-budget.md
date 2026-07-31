---
id: TASK-58.4
title: >-
  Validate the adr-mcp dual-era upgrade against real clients, the SDK and the
  latency budget
status: Done
assignee: []
created_date: '2026-07-29 22:48'
updated_date: '2026-07-31 05:04'
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
- [x] #1 The changed server lists and calls all five tools from Claude Code, and the negotiated era is recorded as evidence
- [x] #2 Codex CLI and GitHub Copilot CLI are either verified or explicitly documented as not verifiable, with the reason
- [x] #3 The official mcp 2.0.0 SDK client drives the server successfully in auto, modern-only and legacy modes, from a throwaway venv
- [x] #4 The SDK does not appear in any runtime dependency declaration of adr-kit after this work
- [x] #5 A handshake-only client, including one sending initialize with no protocolVersion, still works exactly as before
- [x] #6 The ADR-015 two-second latency budget is measured with the added server/discover round-trip, and either shown to hold or the fixture is updated with written justification
- [x] #7 Captured DiscoverResult, modern ListToolsResult and modern CallToolResult payloads validate against schema/2026-07-28.json
- [x] #8 The suite passes on Windows and on Linux CI
- [x] #9 The task's final summary names every client and mode exercised, and any deviation found
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-07-30 22:53
---
Validation run complete 2026-07-30. Eight of nine criteria met; **AC8 is the only one open** and it cannot be closed from here, because the Linux/macOS leg runs in `validate.yml` and nothing has been committed yet. Windows passed on both Python 3.12.9 and 3.14.2 (58 tests each). Python 3.10 is not installed on this machine; `ast.parse(feature_version=(3,10))` accepts both files, which is a grammar check, not a runtime one. Recorded as unverified rather than assumed.

**Eras actually negotiated** (the point of AC1/AC2 — none of this was assumed by ADR-016):

| Client | Version | Era | Tools |
|---|---|---|---|
| Claude Code 2.1.220 | 2025-11-25 | handshake | 5/5 |
| Codex CLI 0.145.0 | 2025-06-18 | handshake | 5/5 |
| GitHub Copilot CLI 1.0.71 | 2025-11-25 | handshake | 5/5 |
| mcp 2.0.0 SDK, auto | 2026-07-28 | modern | 5/5 |
| mcp 2.0.0 SDK, pinned | 2026-07-28 | modern | 5/5 |
| mcp 2.0.0 SDK, legacy | 2025-11-25 | handshake | 5/5 |

No client's stored config was mutated; each was driven through an explicit per-invocation config pointing at the working tree via a byte-transparent recorder. Note that `.mcp.json` resolves `${CLAUDE_PLUGIN_ROOT}` to the 0.42.0 plugin cache, which contains no `server/discover` at all — so `.mcp.json` itself was *not* what got validated.

**AC6, latency.** The task's premise turned out to be wrong: `server/discover` does not add a round-trip, it *replaces* `initialize` one for one. Warm p50: discover 4.74 ms vs initialize 2.10 ms. Cold start to first tool result: legacy p50 578 / p95 865 ms, modern p50 622 / p95 657 ms — modern is +44 ms at p50 and 208 ms *faster* at p95, both about a third of the 2000 ms budget. `tests/fixtures/cli/latency-corpus.json` was deliberately left untouched: nothing breaches the budget, so there is nothing to justify. Adding an `adr-mcp` entry to `budgets` was also declined — the corpus scopes itself to one-shot user-facing CLI invocations, and a long-lived server's per-request latency is a different metric that would need its own semantics. That is a decision for the owner, not a silent addition. Scope limit worth recording: measured at 17 ADRs, and the corpus's own `adr_count_scaling` block shows these paths grow with ADR count.

**AC5, one intended wire delta.** Six of seven legacy scenarios are byte-identical to HEAD~2. The seventh: `initialize` with no or unknown `protocolVersion` is now counter-offered 2025-11-25 instead of 2025-06-18 — a consequence of TASK-58.1, spec-legal (the handshake mandates a counter-offer, never an error), and asserted by an existing test. A client that both omits `protocolVersion` and does not know 2025-11-25 would be offered a version it may reject; all three real clients declare one, so that population is empty in practice.

**AC7.** DiscoverResult, modern ListToolsResult and five modern CallToolResults validate clean against `schema/2026-07-28.json`, plus all seven whole JSONRPCResponse envelopes. Five negative controls and an envelope control were correctly rejected, so the validator is proven bound rather than vacuously passing.

**Positive finding on ADR-016's design.** All three clients put vendor keys in `params._meta` (`claudecode/toolUseId`, `progressToken`, `threadId`, `x-codex-turn-metadata`) and none used the reserved `io.modelcontextprotocol/` prefix. Every such frame routed legacy correctly. Keying era detection on the reserved key rather than on `_meta` merely being present is empirically the right call, not just a theoretical nicety.

**Blocking defect found, and since fixed: TASK-69.** The run surfaced that `bin/adr-mcp` did not speak UTF-8 on Windows — invalid bytes on the wire, CRLF framing, and a tool result lost to `-32603`. Pre-existing and era-independent, so not a regression from this work, but it made the SDK client unable to drive the server on a cp1252 host in any era. Fixed and covered by three teeth-verified regression tests. That is why AC3 is marked met: the SDK drove all three modes successfully, though at the time only with `PYTHONIOENCODING=utf-8` forced on the server as a workaround. That workaround is no longer needed.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
All nine criteria met. AC8 closed by CI run 30605623277 on `dev`: **validate → success**, with Python 3.10 and 3.12 both green on ubuntu, macos and windows, plus markdownlint.

Getting there took two follow-up commits, and the reason is exactly why this criterion could not be waved through locally.

**The first push went red on Python 3.10 across all three platforms while 3.12 passed everywhere** — a version problem, not a platform one. `tests/test_bin_import_safety.py` (from TASK-62) runs each executable twice, plain and with `-P`. `-P` (PYTHONSAFEPATH) landed in CPython 3.11; on 3.10 it is not a flag at all, so the interpreter exits 2 with "Unknown option" and the assertion `returncode in (0, 1)` read that as the tool being broken. Now skipped below 3.11 rather than skipping the whole test: the plain run still proves the shadowing defence on every supported version, and `-P` only adds the case where CPython's own mitigation is active too.

I develop on 3.12. Nothing local would ever have caught this.

**The second push turned all six matrix jobs green but validate stayed red** on a single markdownlint MD012 — two consecutive blank lines at `skills/init/SKILL.md:297`, introduced with the backend-choice section. Swept the entire linted scope rather than patching the reported line, since markdownlint stops at the first file and a second violation would only have surfaced on the next run. All 53 files under the configured globs are clean; five other MD012 hits elsewhere in the repository are outside those globs and left alone.

**A correction to my own reporting.** After the first push I read `gh run watch --exit-status` returning 0 as success and said so. The run had in fact concluded `failure`; the watcher's exit code did not reflect the run's conclusion. I now read `--json conclusion` per job instead. Stating it because the wrong claim went out before the right one did.

The substance of the validation — three real clients, the official SDK in three modes, schema conformance, the latency measurements, the byte-diffed legacy regression — is recorded in comment #1 and is unchanged by any of this. What changed is only that the cross-platform leg is now evidence rather than an assumption.

Also worth recording: this run surfaced a defect the task did not ask about. `bin/adr-mcp` did not speak UTF-8 on Windows — invalid bytes on the wire, CRLF framing, and a tool result lost to `-32603`. Pre-existing and era-independent, so not a regression from the dual-era work, but it made the official SDK client unable to drive the server on a cp1252 host in any era. Fixed and covered by three teeth-verified regression tests under TASK-69.</finalSummary>
<!-- SECTION:FINAL_SUMMARY:END -->
