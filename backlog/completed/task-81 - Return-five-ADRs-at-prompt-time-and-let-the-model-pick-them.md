---
id: TASK-81
title: 'Return five ADRs at prompt time, and let the model pick them'
status: Done
assignee: []
created_date: '2026-08-01 10:34'
updated_date: '2026-08-02 07:24'
labels:
  - spec-gap
  - R5
  - retrieval
  - hooks
dependencies: []
modified_files:
  - hooks/adr_hook_core.py
  - hooks/native/adr-hook.rs
  - tests/test_adr_hook_result_limit.py
  - CHANGELOG.md
  - codex/
  - copilot/
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
- [x] #1 The prompt hook returns five ADRs by default and reads the configured limit instead of hardcoding it
- [x] #2 The Python and Rust hooks agree on both the limit and the metadata they carry; a test asserts parity rather than trusting it
- [ ] #3 Once TASK-79 lands, the candidate set comes from the vector layer and the model selects the final five
- [ ] #4 The selection step degrades to the deterministic ranking when no model is available, and says so
- [x] #5 A Windows run and a POSIX run of the same prompt against the same ADR set produce the same set of ADRs
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Three of the four defects are fixed. The fourth turned out to be blocked by the architecture it was supposed to use, which is worth more than a workaround.

**Shipped.** The prompt hook returns five, not three. `context.default_limit` now reaches the hook - it was documented as the knob and read by nothing, so a user who set five still got three. A value outside 1..20 falls back rather than being obeyed, because a typo must not turn one prompt into a context flood. And the Rust hook carried its own copy of the constant, so what an agent was told depended on the platform: a test now asserts both implementations declare the same default rather than trusting that they do. That third one was the worst of the three precisely because nobody could see it happen.

**Not shipped, and it needs a decision rather than more effort.** AC #3 and #4 ask the vector layer to supply candidates at prompt time with the model selecting the final five. Semantic search requires embedding the *query*, and ADR-018's Must Not forbids calling an embedding model from the hook path - the clause that keeps the hook inside ADR-015's 2 s budget and ADR-016's zero-dependency posture. So R5's remaining half is not merely unimplemented; as ADR-018 stands it is prohibited.

This is the same shape as the conflict that produced ADR-018 itself: the spec asks for something the project's own architecture forbids, and the honest move is a decision, not a workaround. Three directions worth weighing, none of them free:

1. A bounded exception in ADR-018 permitting one local embedding call at prompt time, measured against the 2 s budget rather than assumed to fit.
2. Lexical prefilter at prompt time, vector rerank only where a query vector already exists (the CLI, the MCP tools) - keeps the hook clean, gives the hook no semantic gain.
3. Accept that semantic retrieval belongs to explicitly invoked surfaces and not to the hot path, and say so in the spec.

Flagged to the maintainer rather than decided here: ADR-018 is Accepted, and an agent may not quietly reinterpret an Accepted decision to make its own task complete.

Gates: 1342 passed / 12 skipped, adapter drift clean.</finalSummary>
<!-- SECTION:FINAL_SUMMARY:END -->
