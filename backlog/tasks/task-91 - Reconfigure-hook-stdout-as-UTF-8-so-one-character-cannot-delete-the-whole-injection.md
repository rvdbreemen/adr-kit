---
id: TASK-91
title: >-
  Reconfigure hook stdout as UTF-8, so one character cannot delete the whole
  injection
status: To Do
assignee: []
created_date: '2026-08-03 18:57'
updated_date: '2026-08-03 18:57'
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
- [ ] #2 A test injects text containing a character outside cp1252 with PYTHONIOENCODING unset and asserts the injection arrives intact
- [ ] #3 The test fails against the current code, proving it guards the real defect
- [ ] #4 The Rust native hook is checked for the same assumption and fixed if it shares it
<!-- AC:END -->
