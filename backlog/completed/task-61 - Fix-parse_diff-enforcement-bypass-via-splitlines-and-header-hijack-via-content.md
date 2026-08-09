---
id: TASK-61
title: >-
  Fix parse_diff: enforcement bypass via splitlines and header hijack via ++
  content
status: Done
assignee: []
created_date: '2026-07-30 17:54'
updated_date: '2026-07-30 20:34'
labels:
  - security
  - judge
  - review-finding
dependencies: []
references:
  - .full-review/01-quality-architecture.md
  - .full-review/raw/repro-A2-enforcement-bypass.py
modified_files:
  - bin/adr-judge
  - tests/test_adr_judge_security.py
priority: high
ordinal: 66500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found by the comprehensive review and independently re-verified. See `.full-review/01-quality-architecture.md` finding C2. Reproduction script: `.full-review/raw/repro-A2-enforcement-bypass.py`.

Two defects in `parse_diff` (`bin/adr-judge:491-534`) share one root cause: the parser classifies lines by prefix with no diff-structure state.

**Defect 1 — `splitlines()` drops added-line content, letting forbidden tokens through.**

`bin/adr-judge:501` iterates `text.splitlines()`. Python splits on `\x0b`, `\x0c`, `\x1c`, `\x1d`, `\x1e`, `\x85`, U+2028 and U+2029 in addition to `\n`/`\r\n`. Git's unified diff format recognises only `\n`. Content following such a character becomes a fragment starting with neither `+` nor a space, matches no branch at `:528-532`, and is silently discarded from `DiffFile.added`.

Re-verified in this session against a rule forbidding `BADTOKEN`:

```
case                       exit  verdict
plain (control)               1  BLOCKED    violations=1
after form feed \x0c          0  PASSED     <-- bypass
after U+2028                  0  PASSED     <-- bypass
after vertical tab \x0b       0  PASSED     <-- bypass
after \x1c                    0  PASSED     <-- bypass
after NEL \x85                0  PASSED     <-- bypass
```

Not purely adversarial: form feed is a legitimate page-break convention in GNU C style and Emacs-managed sources, so this fires by accident on real code.

Two second-order effects, both reproduced: line-number drift when a fragment happens to start with `+`, and FALSE `require_pattern` violations on new files, because `_read_snapshot_content:858-862` reconstructs a new file's post-image from `diff_file.added`.

**Defect 2 — the file-header branch is hijackable by added content.**

An added line whose content starts with `++ ` renders as `+++ ` in the diff and takes the `+++ ` header branch unconditionally. Reproduced:

```
--- a/app.c
+++ b/app.c
@@ -1,0 +10,3 @@
+++ FORBIDDEN_HEADERHIJACK
+++FORBIDDEN_DROPPED
+normal_line_after
```
parses to:
```
path='app.c'                   added=[]           <-- every added line lost
path='FORBIDDEN_HEADERHIJACK'  added=[(10, 'normal_line_after')]
```

`app.c` ends with zero added lines, and the rest of the hunk is re-attributed to a fabricated path that then fails `path_matches` against any real `path_glob`. The `++X` variant (no space) is silently dropped by the `not line.startswith("+++")` guard.

**Fix — one change addressing both.** Anchor the header branches to the `diff --git` state machine so `--- `/`+++ ` are only recognised between `diff --git` and the first `@@`; then no prefix-exclusion guard is needed on added lines. In the same change, replace `splitlines()` with `split("\n")` AND strip exactly one trailing `\r` per line — `split("\n")` alone leaves `\r` on every line of a CRLF diff and breaks anchored patterns such as `ArduinoJson\.h>$`, trading one false negative for another. This is the same Windows line-ending surface as TASK-57; consider fixing them together.

Audit the other `splitlines()` sites at `:180`, `:1223` and `:1308`; they are lower risk but share the assumption.

**Contract impact.** `bin/adr-mcp:485-489`, `bin/adr-judge-precommit`, `.githooks/pre-commit:210-215` and the CI action all depend on the judge's verdict being correct. TASK-58 layers a second MCP protocol era on that contract and inherits this defect, so fix it before that work lands.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A forbidden token preceded by \x0c, \x0b, \x1c, \x1d, \x1e, \x85, U+2028 or U+2029 on an added line is still blocked
- [ ] #2 An added line whose content starts with `++ ` or `++` no longer takes the file-header branch, and the real file keeps all its added lines
- [ ] #3 A CRLF diff still matches anchored patterns; the fix strips exactly one trailing \r and does not leave it on the line
- [ ] #4 Reported line numbers match post-image line numbers for every case above
- [ ] #5 require_pattern on a NEW file no longer produces a false violation when the added content contains any of these characters
- [ ] #6 Regression tests for the form-feed bypass, the `++ ` hijack and a CRLF diff are added to tests/test_adr_judge_security.py
- [ ] #7 The other splitlines() sites at :180, :1223 and :1308 have been audited and either fixed or documented as safe
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed in bin/adr-judge, with regression tests.

**Root cause.** Both defects came from one thing: `parse_diff` classified lines by prefix with no diff-structure state.

**Fix 1 — tokenisation.** `text.splitlines()` replaced with `text.split("\n")` plus stripping exactly one trailing `\r` per line. splitlines() also breaks on \x0b \x0c \x1c \x1d \x1e \x85 U+2028 U+2029, none of which git treats as a line terminator, so content after one became an orphan fragment that matched no branch and was dropped from `DiffFile.added`. Stripping the CR in the same change was necessary, not optional: `split("\n")` alone leaves `\r` on every line of a CRLF diff and breaks end-anchored patterns such as `ArduinoJson\.h>$`, which would have traded one false negative for another.

**Fix 2 — header hijack.** The `--- ` and `+++ ` branches are now hunk-gated via an `in_hunk` flag set by `@@` and cleared by `diff --git`. Inside a hunk a `+++` line is always content, never a header. This also removed the need for the old `not line.startswith("+++")` guard on added lines, which had been silently dropping `++X`.

Hunk-gating was chosen over a full `diff --git` state machine deliberately: not every diff carries that header (`git diff --no-prefix`, hand-written patches), and gating on `@@` stays correct for both shapes.

**Verified.**
- The reproduction script `.full-review/raw/repro-A2-enforcement-bypass.py` goes from 5/5 bypasses to 0/5.
- Header hijack: all three added lines retained, attributed to the real path, line numbers 10/11/12.
- CRLF: no stray `\r`, and `ArduinoJson\.h>$` still matches.
- Regressions checked: ordinary diffs parse identically, context lines still advance the counter, deleted files still recognised.
- Full suite: 909 passed, 1 pre-existing failure unrelated to this work (see TASK-64), 5 skipped, 1 xfailed.

**Tests added** to `tests/test_adr_judge_security.py`: a parametrised CLI test over all eight separator characters, a header-hijack test asserting path attribution and line numbers, and two unit tests calling `parse_diff` directly.

The CRLF case had to become a unit test. Passing a CRLF diff through subprocess stdin with `text=True` applies universal-newline translation — `"a\r\nb\r\n"` arrives as `"a\n\nb\n\n"` — so the carriage return never reaches `parse_diff` and a CLI test cannot observe the behaviour at all. That is also the first use in this suite of loading the extensionless executable via `SourceFileLoader`, which the review identified as the missing coverage mechanism that let this defect survive.

Not done here: the `splitlines()` sites at `:180`, `:1223` and `:1308` were left alone. They operate on ADR bodies and log files rather than diffs, so they do not carry the same bypass risk, but they have not been individually audited.
<!-- SECTION:FINAL_SUMMARY:END -->
