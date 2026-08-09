---
id: TASK-156
title: >-
  Raise UserPromptSubmit to five results and let the model choose them (spec B4,
  R5)
status: To Do
assignee: []
created_date: '2026-08-09 13:22'
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
- [ ] #1 UserPromptSubmit injects up to five candidates and instructs the model to select what applies
- [ ] #2 Injection stays inside inject.max_tokens and the event budget; python -m pytest -q passes
<!-- AC:END -->
