---
id: TASK-156
title: >-
  Raise UserPromptSubmit to five results and let the model choose them (spec B4,
  R5)
status: Done
assignee:
  - '@claude'
created_date: '2026-08-09 13:22'
updated_date: '2026-08-09 14:44'
labels: []
dependencies: []
references:
  - docs/plans/kiss-simplification-plan.md
priority: low
ordinal: 123500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The second half of R5: MAX_RESULTS = 3 in hooks/adr_hook_core.py and the selection is a deterministic scoring formula. R5 asks for the top 5, chosen by the model from a retrieved candidate set - retrieval narrows, the model chooses. Two-part change per spec B4: widen the injected candidate set to five (mind the injection token budget, inject.max_tokens), and phrase the injection so the session model performs the final relevance selection instead of treating the ranked list as the answer. Purely lexical+graph candidates (ADR-036); no model call in the hook itself.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 UserPromptSubmit injects up to five candidates and instructs the model to select what applies
- [x] #2 Injection stays inside inject.max_tokens and the event budget; python -m pytest -q passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Premise partially stale: the widen-to-five half landed earlier via cd992f3 (DEFAULT_MAX_RESULTS = 5, config-honouring). What remains is the phrasing half of B4/R5: the UserPromptSubmit headings assert relevance ('Governing Accepted ADRs relevant to this prompt') instead of presenting a retrieval-ranked candidate set for the session model to select from. Scope of this change: the UserPromptSubmit branch only; the plan-exit injection has its own contract (TASK-150, B1).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shipped as PR #85. The widen-to-five half of R5 had already landed (cd992f3, DEFAULT_MAX_RESULTS=5, config-honouring), so this task delivered the phrasing half plus two premise corrections recorded in the notes (MAX_RESULTS was not 3; inject.max_tokens does not exist, the operative budget is the 4KiB MAX_CONTEXT_CHARS slice, unchanged). UserPromptSubmit now injects candidate-framed headings (Accepted/Proposed ADR candidates for this prompt) followed by one selection instruction telling the session model to apply what governs and ignore the rest; plan-exit and pre-edit injections deliberately keep their assertive headings since at edit time governance is fact, not retrieval. Rust host mirrors the phrasing byte-for-byte, exe rebuilt per the README recipe and verified at binary level. New real-workspace behaviour test (generated index) and a Rust parity test in the MAX_RESULTS pattern; two protocol tests that pinned the old heading for both events are now event-specific, forced by the native-parity failure. Full suite 1756 passed / 12 skipped with the exit code read directly rather than through a pipe.
<!-- SECTION:FINAL_SUMMARY:END -->
