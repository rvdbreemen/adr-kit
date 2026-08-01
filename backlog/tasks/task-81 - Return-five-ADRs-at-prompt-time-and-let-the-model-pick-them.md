---
id: TASK-81
title: 'Return five ADRs at prompt time, and let the model pick them'
status: To Do
assignee: []
created_date: '2026-08-01 10:34'
labels:
  - spec-gap
  - R5
  - retrieval
  - hooks
dependencies: []
priority: medium
ordinal: 86500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
spec.md R5. The hook exists and fires — `hooks/hooks.json:15-25` registers user-prompt-submit, `hooks/adr_hook_core.py:440-452` queries and renders "Governing Accepted ADRs relevant to this prompt". Three gaps against the intent.

**Three, not five.** `MAX_RESULTS = 3` is hardcoded at `hooks/adr_hook_core.py:24`, identically in the codex/ and copilot/ copies, and as `const MAX_RESULTS: usize = 3` at `hooks/native/adr-hook.rs:19`. The hook never reads `.adr-kit.json`, so a user who sets `context.default_limit: 5` still gets three — the documented knob does not reach the hook. Only the CLI honours it (`bin/adr-context:159`).

**A formula picks, not the model.** Selection is weighted lexical scoring. R5 asks for the vector layer to supply candidates and the *model* to choose which five are relevant. That is a two-part change and the second part depends on TASK-79.

**The Rust hook is behind.** `hooks/native/adr-hook.rs` parses only the `adrs` array and contains no occurrence of relationship, superseded or related. On Windows `run-hook.cmd` prefers that binary, so the graph-aware half of retrieval silently does not apply there — a platform-dependent difference in what an agent is told, which is worse than a missing feature because nobody sees it happen.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The prompt hook returns five ADRs by default and reads the configured limit instead of hardcoding it
- [ ] #2 The Python and Rust hooks agree on both the limit and the metadata they carry; a test asserts parity rather than trusting it
- [ ] #3 Once TASK-79 lands, the candidate set comes from the vector layer and the model selects the final five
- [ ] #4 The selection step degrades to the deterministic ranking when no model is available, and says so
- [ ] #5 A Windows run and a POSIX run of the same prompt against the same ADR set produce the same set of ADRs
<!-- AC:END -->
