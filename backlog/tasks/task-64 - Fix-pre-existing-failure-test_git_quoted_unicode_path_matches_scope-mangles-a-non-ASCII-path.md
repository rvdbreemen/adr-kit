---
id: TASK-64
title: >-
  Fix pre-existing failure: test_git_quoted_unicode_path_matches_scope mangles a
  non-ASCII path
status: To Do
assignee: []
created_date: '2026-07-30 20:34'
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
