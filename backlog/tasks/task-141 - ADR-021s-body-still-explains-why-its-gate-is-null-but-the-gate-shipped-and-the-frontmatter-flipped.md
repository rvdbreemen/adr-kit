---
id: TASK-141
title: >-
  ADR-021's body still explains why its gate is null, but the gate shipped and
  the frontmatter flipped
status: Done
assignee: []
created_date: '2026-08-06 06:06'
updated_date: '2026-08-06 18:32'
labels:
  - adr
  - docs
  - consistency
dependencies: []
references:
  - >-
    docs/adr/ADR-021-regenerate-a-stale-adr-index-from-the-events-that-can-afford-it.md
  - tests/test_declared_gate_flip.py
priority: low
ordinal: 112500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`docs/adr/ADR-021-*.md` contradicts itself.

Frontmatter (current):

```yaml
status: "Accepted"
binding: true
gate: "adr-hook-index-refresh-v1"
```

Body, `### Verification`, lines 216-220:

> `adr-hook-index-refresh-v1`: the gate this decision is to be anchored by. It does not exist yet, so `gate` is null and `binding` is false: a frontmatter that declares enforcement it cannot deliver is worse than one that admits the gap. Both fields flip back together when the gate ships, covering the write-then-prompt sequence, the concurrent-hook case, and the budget bail-out.

The gate shipped and both fields flipped, exactly as the paragraph promised. The paragraph explaining why they were null was left behind, so the record now reads as though the enforcement does not exist.

This is narrow but it matters more here than in most repositories: this is the ADR corpus of the tool that lints ADR corpora. `tests/test_declared_gate_flip.py` exists precisely to cover a gate flip — it caught the frontmatter half and not the prose half, which is a reasonable thing for a test to miss and a reasonable thing to close.

Worth checking whether any other Accepted ADR carries the same shape: a `### Verification` paragraph written while the gate was still pending, never revised once it landed. A sweep is cheap; there are 33 records.

Found while refreshing the C4 architecture documentation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ADR-021's `### Verification` paragraph describes the gate as shipped and anchoring the decision, matching `binding: true` and `gate: "adr-hook-index-refresh-v1"`
- [x] #2 The other 32 records are swept for a `### Verification` paragraph that contradicts its own frontmatter, and any found are corrected in the same pass
- [x] #3 If the sweep finds more than this one, a check is added so a gate flip cannot leave the prose behind again — the existing `tests/test_declared_gate_flip.py` is the natural home
- [x] #4 `python bin/adr-lint --strict docs/adr` stays clean and `python bin/adr-index --check docs/adr` reports no drift
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Closed on `fix/backlog-todo-sweep` (commit fee596c).

**The sweep found eleven records, not one.** TASK-127 flipped `gate` and `binding` in the frontmatter when each gate shipped and left the paragraph next to those fields behind.

- ADR-021, ADR-022, ADR-024 — the whole pending paragraph survived.
- ADR-020, ADR-023, ADR-025, ADR-026, ADR-027, ADR-028, ADR-029 — **half-corrected**: TASK-127 replaced the opening sentence and left the trailing clause, so each read "the gate that anchors this decision. Both fields flip back together when the gate ships" — corrected and stale in the same sentence.
- ADR-016 — same defect in a different field: its Verification bullet and its Confirmation lead said `verified_in` stays empty until the suite lands, while the frontmatter names `tests/test_adr_mcp.py` and that file exists carrying the gate anchor at :715.

All eleven gate anchors were confirmed present under `tests/` before rewriting. Every Verification bullet now names the file its gate ships in, in the present tense.

**Record correction:** the task cited `docs/adr/ADR-021-regenerate-a-stale-adr-index-from-the-events-that-can-afford-it.md`. The real filename is `ADR-021-let-the-session-scoped-hooks-regenerate-a-stale-adr-index.md`.

**AC#3 fired.** `tests/test_declared_gate_flip.py` gains `test_the_prose_half_of_the_flip_is_not_left_behind`: a record declaring `gate` and `binding: true` may not keep a sentence that is only true while the gate is pending. Keyed on the frontmatter rather than on the anchor, so it catches the seven half-corrected records too — a partial sweep is what a check catches and a reader does not. Verified failing on all eleven before the fix, passing after.

**Not changed, deliberately:** ADR-016's Negative consequence about the acceptance-to-implementation window. That paragraph argues about a period that has passed; rewriting it would edit the record's reasoning rather than a stale fact.

Verification: `python bin/adr-lint --strict docs/adr` exit 0, `python bin/adr-index --check docs/adr` exit 0 after regenerating `ADR-INDEX.json`, `tests/test_declared_gate_flip.py` 4 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
