---
id: TASK-69
title: >-
  adr-mcp violates MCP stdio encoding: non-UTF-8 bytes and CRLF framing on
  Windows
status: Done
assignee: []
created_date: '2026-07-30 22:35'
updated_date: '2026-07-30 22:52'
labels:
  - mcp
  - bug
  - windows
  - release-blocker
dependencies: []
references:
  - 'bin/adr-mcp:693-695'
  - 'bin/adr-mcp:987'
  - 'bin/adr-status:433'
  - >-
    docs/adr/ADR-016-serve-both-mcp-protocol-eras-from-one-hand-rolled-stdio-server.md
modified_files:
  - bin/adr-mcp
  - tests/test_adr_mcp.py
priority: high
ordinal: 74500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`bin/adr-mcp` writes JSON-RPC frames to `sys.stdout` in text mode using the platform default encoding, and reads `sys.stdin` the same way. The MCP stdio transport mandates UTF-8 and newline-delimited framing. On a cp1252 Windows host it delivers neither.

Found during TASK-58.4 client validation. **Pre-existing and era-independent** — `_write_message` is byte-identical at HEAD (before the dual-era working-tree changes) and is shared by both dispatch paths, so the dual-era work neither introduced nor fixed it.

**Reproduced directly**, feeding `initialize` + `tools/call adr_status` to the server as a subprocess with `PYTHONIOENCODING` removed from the environment so the platform default applies:

```
exit: 0
total bytes: 15584
CRLF frame endings: 2 | bare LF: 0
UTF-8 decode: FAILS -> 'utf-8' codec can't decode byte 0x97 in position 6839
  context (cp1252): "reason": "Superseded — consider archiving"
```

Byte `0x97` is the cp1252 encoding of U+2014, emitted by `bin/adr-status:433` (`f"{status} — consider archiving"`). Exit code is 0, so the server reports success while putting invalid UTF-8 on the wire.

**Three distinct symptoms, all observed:**

1. **Silent corruption.** The official `mcp==2.0.0` client's strict reader aborts the session in all three modes. Claude Code's decoder is lenient and silently accepted `Superseded � consider archiving`.
2. **Lost tool results.** U+2192 from `adr-context` is unmappable in cp1252, so `_write_message` raises `UnicodeEncodeError`, which `dispatch()`'s broad handler converts into JSON-RPC `-32603`. Reproduced live against Claude Code 2.1.220: `adr_context=FAIL:MCP -32603 'charmap' codec can't encode '→'`. Framing survives; the result does not.
3. **CRLF framing.** Every frame ends `\r\n` rather than `\n`.

**Why the existing suite misses it, and how a regression test must differ.** The synthetic `project` fixture's ADRs are ASCII-only, so no tool payload ever carries a non-ASCII character — the gap is invisible by construction. Worse, `run_session_lines` drives the server with `text=True, encoding="utf-8"`, which *imposes* correct encoding on the child and masks the defect. **A regression test must read raw bytes and must use a fixture containing non-ASCII content**, or it will pass against the unfixed server.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `bin/adr-mcp` writes every frame as UTF-8 and terminates it with a bare LF, regardless of the host's default encoding
- [x] #2 Reading stdin is likewise pinned to UTF-8, so a client sending non-ASCII arguments is parsed correctly
- [x] #3 A regression test drives the server as a subprocess reading raw BYTES, with PYTHONIOENCODING absent from the child environment, against a fixture whose ADR content contains non-ASCII characters; it asserts the output decodes as UTF-8 and contains no CRLF frame terminators
- [x] #4 A tool result containing a character unmappable in cp1252 (for example U+2192) is returned as a normal result rather than JSON-RPC -32603
- [x] #5 The fix is verified on the real repository, not only the synthetic fixture, since the trigger (an em dash from bin/adr-status) originates in real ADR data
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed in `bin/adr-mcp` by pinning our own stdio, plus a narrower hardening of the subprocess environment.

**The fix that mattered: `_pin_stdio_to_utf8()`**, called once at the top of `main()` before `serve()`. It reconfigures stdin/stdout to UTF-8 and sets `newline=""` on stdout so the `"\n"` appended in `_write_message` reaches the wire as one byte instead of being translated to CRLF. stderr gets `errors="replace"` so an unmappable character in a diagnostic line cannot raise inside the server. A `hasattr` guard covers a caller that replaced a std stream with an object lacking `reconfigure`.

Measured on the real repository, same probe before and after:

```
before: 15584 bytes | CRLF 2, bare LF 0 | UTF-8 decode FAILS (0x97 at 6839)
after:  15586 bytes | CRLF 0, bare LF 2 | UTF-8 decode OK
```

The +2 bytes are the confirmation: two em dashes, each now 3 UTF-8 bytes instead of 1 cp1252 byte.

**What I got wrong on the way, corrected.** I first added `PYTHONIOENCODING=utf-8` to `run_cli`'s child environment believing the corruption originated one process earlier. An A/B with that line disabled produced byte-identical output, and direct measurement showed why: every wrapped CLI dumps JSON with `ensure_ascii=True`, so `Café` crosses the subprocess boundary as the ASCII escape `é` and the child's stdout encoding is irrelevant. The line is kept — the child's *stderr* carries free-form warning text that can quote a non-ASCII path, and a future CLI could dump with `ensure_ascii=False` — but its comment now states plainly that it is defence in depth and **not** what fixed this defect. An earlier draft of that comment claimed a corruption path that does not exist.

I also briefly chased a `Caf�` in a test failure message as if it were data corruption. It was pytest rendering `é` through a cp1252 console, compounded by a case error in my own assertion. No code defect.

**Three regression tests in `tests/test_adr_mcp.py`, all with verified teeth.** Each was run against a copy with `_pin_stdio_to_utf8()` disabled; all three fail there and pass with it:

- `test_frames_are_utf8_and_lf_terminated_under_a_hostile_locale`
- `test_non_ascii_stdin_is_decoded_as_utf8_not_the_host_codepage`
- `test_non_ascii_adr_content_survives_the_round_trip`

Two design points. They read raw **bytes**: the existing `run_session_lines` helper drives the server with `text=True, encoding="utf-8"`, which imposes the correct encoding on the child and hides this class of defect completely. And they force `PYTHONIOENCODING=cp1252` on the child rather than merely unsetting it — unsetting reproduces the bug only on a cp1252 host, so the test would be dead weight on Linux CI where the default is already UTF-8. Forcing a hostile encoding makes the assertion meaningful everywhere.

The disabled-fix run reproduced the exact live symptom from the TASK-58.4 client validation: `-32603 Internal error: 'charmap' codec can't encode character '→'`. That is independent confirmation of the reported failure rather than a restatement of it.

**A fourth instance of the same class, found by my own tooling.** A throwaway script I wrote to scan the CLIs for non-ASCII characters crashed with `UnicodeEncodeError` on `→` in `bin/adr-judge` — the identical defect, one directory over. Not in scope here; noted because it suggests the pattern is worth a sweep.

Verification: `tests/test_adr_mcp.py` 61 passed. `bin/adr-judge --diff <adr-mcp diff> --snapshot worktree` reports 0 violations, 0 advisory. AC5 checked against the real repository, not only the synthetic fixture, since the trigger (`bin/adr-status:433`) fires on ADR-001 being Superseded.

**Still open:** the `codex/` and `copilot/` mirrors of `bin/adr-mcp` need a `scripts/build-client-adapters.py` run. Deliberately not done here — two other agents are editing this shared tree, so the generator runs once at the end.</finalSummary>
<!-- SECTION:FINAL_SUMMARY:END -->
