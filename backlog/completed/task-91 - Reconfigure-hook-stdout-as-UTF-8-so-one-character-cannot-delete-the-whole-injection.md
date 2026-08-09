---
id: TASK-91
title: >-
  Reconfigure hook stdout as UTF-8, so one character cannot delete the whole
  injection
status: Done
assignee: []
created_date: '2026-08-03 18:57'
updated_date: '2026-08-03 20:15'
labels:
  - P1
  - hooks
  - windows
  - encoding
dependencies: []
priority: high
ordinal: 96500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
On Windows, a single character outside cp1252 anywhere in the injected text makes the hook write nothing at all. Verified:

```
$ python -c 'import sys; sys.stdout.write("before [U+23F3] after")'
UnicodeEncodeError: 'charmap' codec can't encode character
exit=1, stdout=''
```

`hooks/adr-hook.py` and `hooks/adr_hook_core.py` never call `sys.stdout.reconfigure(encoding="utf-8")`, unlike the `bin/` entrypoints, which all do. When stdout is a pipe and no `PYTHONIOENCODING` is set, Python uses the locale encoding — cp1252 on this machine.

**This is live today, not theoretical.** `docs/adr/ADR-016` contains an arrow (U+2192), which cp1252 cannot encode. Any prompt that retrieves ADR-016 and injects a line carrying it produces an empty injection. The verification script written to find this crashed on the same character while printing its own result.

**The failure is silent by construction.** Hooks fail open, so the harness treats an empty result as "nothing to inject" and continues. The user sees no error, no warning, and no ADR context — indistinguishable from a session where no ADR was relevant. Em-dash and bullet survive because cp1252 happens to carry them at 0x97 and 0x95; arrows, checkmarks, emoji and CJK do not.

Check `hooks/native/adr-hook.rs` for the same assumption rather than assuming it is safe.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 hooks/adr-hook.py reconfigures stdout and stderr to UTF-8 before writing, guarded like the bin/ entrypoints are
- [x] #2 A test injects text containing a character outside cp1252 with PYTHONIOENCODING unset and asserts the injection arrives intact
- [x] #3 The test fails against the current code, proving it guards the real defect
- [ ] #4 The Rust native hook is checked for the same assumption and fixed if it shares it
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude
created: 2026-08-03 20:15
---
AC#1 was met by a stronger route than it asks for: the frame is written as UTF-8 bytes to `sys.stdout.buffer`, so there is no text layer to reconfigure and no encoder left that can fail into the fail-open catch. AC#4 is folded into TASK-104: the native host was measured against the Python oracle and diverges on result count as well, so it is now opt-in rather than preferred, and its encoding is checked as part of restoring that preference.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed by writing the frame as UTF-8 bytes to `sys.stdout.buffer` rather than reconfiguring the text layer.

Reproduced live during this session, which is how the scope turned out to be worse than the ticket said: running `hooks/adr-hook.py` on a `pre-tool-use` payload against this repository's own `ADR-INDEX.json` returned 1846 bytes that **do not decode as UTF-8** — byte 0x97 at offset 190, the cp1252 em dash, and four more after it. A title carrying a character cp1252 cannot represent raises `UnicodeEncodeError` instead, which `except BaseException: return 0` swallows into zero bytes and exit 0.

Why bytes rather than `sys.stdout.reconfigure(encoding="utf-8")`: reconfigure fixes the encoding but leaves a text encoder in the path, so a future failure still lands in the fail-open catch and disappears. Writing bytes removes the failure mode. It also settles the question the ticket asked — whether the bare `except` should distinguish an encoding failure — as: no longer applicable, there is no encoding step left to fail.

`newline=""` was deliberately not adopted; the byte write bypasses newline translation anyway, and this repository has an open CRLF sensitivity (TASK-57).

`tests/test_adr_hook_dispatch_matrix.py::test_the_frame_is_utf8_bytes_whatever_the_console_encoding_is` asserts on raw bytes with a fixture ADR titled `Serve Both Protocol Eras → One Process (≥ 2 clients)` — U+2192 and U+2265, both outside cp1252. It fails on the pre-fix state for all three clients.

Shipped in v0.44.1.
<!-- SECTION:FINAL_SUMMARY:END -->
