---
id: TASK-161
title: >-
  One shared ADR-id reader, and a Rust-parity assertion that survives
  re-wrapping
status: Done
assignee:
  - '@claude'
created_date: '2026-08-09 15:24'
updated_date: '2026-08-09 15:33'
labels:
  - refactor
  - tests
dependencies: []
priority: medium
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Three near-identical id parsers exist (adr-judge's filename reader, adr_llm_judge_migration._adr_id, and the inline set comprehension TASK-157 added to cmd_stamp) and the duplication is what allowed the silent-prune id-mismatch bug; they already disagree on zero-padding normalization. Separately, the Rust-parity test's rust_joined = text.replace(backslash-newline) is defeated by CRLF line endings in adr-hook.rs (backslash+CRLF does not match backslash+LF), so it passes only because the instruction fragment happens to sit unbroken on one source line: a re-wrap would fail it spuriously and a real divergence could hide. Review finding NF6+NF7; NF6's mechanism verified as CRLF, not the literal backslash-n the reviewer named.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 One shared filename-to-ADR-id helper lives in a sibling module and cmd_stamp uses it; the other two parsers either use it or carry a pointer comment explaining why not
- [x] #2 The parity test normalizes both CRLF and LF continuations (or compares a continuation-free canonical form) and fails when the instruction text genuinely diverges
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
cmd_stamp now uses adr_catalog's adr_id_from_filename and normalize_adr_id - the kit's one id reader - instead of a fourth local regex. Bonus semantics: normalize_adr_id zero-pads, so ADR-1 resolves to the ADR-001 file and stamps it (tested) while genuinely unresolvable ids are still refused before any write. The parity test canonicalises the Rust line continuation the way rustc does (backslash + CRLF-or-LF + leading whitespace) and demands the WHOLE instruction. Record straightened: the reviewer's mechanism claim was right after all - the test file literally contained replace(backslash+n), a no-op against real newlines; my CRLF theory had tested a fresh snippet instead of the file. The migration module's _adr_id keeps its local parser with adr-migrate's other format duties; unifying that one is out of scope here.
<!-- SECTION:FINAL_SUMMARY:END -->
