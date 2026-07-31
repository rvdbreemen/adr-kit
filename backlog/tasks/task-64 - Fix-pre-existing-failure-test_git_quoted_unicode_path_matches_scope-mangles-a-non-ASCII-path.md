---
id: TASK-64
title: >-
  Fix pre-existing failure: test_git_quoted_unicode_path_matches_scope mangles a
  non-ASCII path
status: Done
assignee: []
created_date: '2026-07-30 20:34'
updated_date: '2026-07-30 21:33'
labels:
  - windows
  - tests
  - judge
dependencies: []
references:
  - .full-review/02-security-performance.md
modified_files:
  - bin/adr-judge
  - tests/test_adr_judge_precommit.py
priority: medium
ordinal: 69500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Pre-existing on HEAD (7d067a2), not introduced by the enforcement-floor fixes. Surfaced while establishing a baseline for that work; recorded so it does not get attributed to a later change.

`tests/test_adr_judge_precommit.py::test_git_quoted_unicode_path_matches_scope` fails on Windows. The judge reports the path as `src/Ã©.py` where the test expects `src/é.py` — classic UTF-8 bytes rendered through a cp1252 lens (`é` is `0xC3 0xA9`, which cp1252 shows as `Ã©`).

The path travels: git writes the filename in a diff as a C-quoted escape (`"src/\303\251.py"`), `_decode_git_quoted_path` (`bin/adr-judge:~490`) unescapes it to bytes and decodes with `errors="surrogateescape"`, and it is then printed to stderr, which the test captures.

Related observation from the Phase 2 security audit, worth reading before starting: the auditor hypothesised that a surrogate-escaped path would raise `UnicodeEncodeError` when it reaches `subprocess.run` argv at `bin/adr-judge:842`, and found it does **not** on Python 3.12/Windows — the argument passes through, git receives replacement bytes and reports the path as missing. The observable effect there is a false `require_pattern` violation rather than a crash. That is a different symptom of the same non-ASCII path handling and may share a root cause with this test failure.

Determine first whether the defect is in the judge (decoding or output encoding) or in the test (its expectation or how it captures stderr), because the fix differs completely. Check the stderr encoding the judge writes with, and what `sys.stderr` uses under pytest on a non-UTF-8 Windows console.

Same family as TASK-57 (Windows CRLF false positive in the adapter drift check): platform-specific text handling that a Linux-only CI run would never surface.</description>
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The failure is diagnosed as either a judge defect or a test defect, with the evidence stated
- [ ] #2 `test_git_quoted_unicode_path_matches_scope` passes on Windows and on Linux
- [ ] #3 If the judge is at fault, a non-ASCII path is reported correctly on a non-UTF-8 console, and the require_pattern false-violation described in the Phase 2 audit is re-checked against the fix
- [ ] #4 No new dependency is introduced; the project is stdlib-only
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The defect was in the test, not in the judge, and it was environment-dependent — which is why two people saw different results.

**Diagnosis.** `_run_wrapper` captured the child's output as raw bytes and decoded them with `locale.getpreferredencoding(False)` — cp1252 on this Windows machine. But the child writes with whatever `PYTHONIOENCODING` dictates. With that variable set to `utf-8`, the judge emitted UTF-8 bytes and the test read them through a cp1252 lens, so `src/é.py` arrived as `src/Ã©.py` — the classic mojibake signature of `0xC3 0xA9` misread.

Proven by toggling one variable, nothing else:

```
PYTHONIOENCODING unset   -> 1 passed
PYTHONIOENCODING=utf-8   -> 1 failed
```

**Correction to the record.** I reported this as "a pre-existing failure on HEAD" in commit ebdbbf6 and in several task summaries. That was misleading. It is pre-existing in the sense that no code change of mine caused it, but it is not a defect in the shipped code at all — I was setting `PYTHONIOENCODING=utf-8` in nearly every command (a habit to avoid Windows cp1252 problems) and that is what made it fail. The concurrent judge agent, which did not set it, correctly reported the test as passing.

**Fix.** Pin both ends. `_run_wrapper` now passes `PYTHONIOENCODING=utf-8` to the child explicitly and decodes as UTF-8 to match, so the outcome depends on the code under test rather than on the shell that launched pytest. `errors="replace"` is kept, so a genuinely undecodable byte still produces a readable assertion failure instead of a `UnicodeDecodeError` inside the harness.

**Verified** under both environments: 9 passed with `PYTHONIOENCODING=utf-8`, 9 passed without.

**The judge needs no change**, which also settles the related hypothesis from the Phase 2 security audit. That audit had wondered whether a surrogate-escaped path would crash on `subprocess.run` argv and found it does not; this failure was a different symptom with a different cause, in the test harness rather than in path handling. `_decode_git_quoted_path` is behaving correctly.
<!-- SECTION:FINAL_SUMMARY:END -->
