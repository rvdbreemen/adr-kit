---
id: TASK-141
title: >-
  ADR-021's body still explains why its gate is null, but the gate shipped and
  the frontmatter flipped
status: To Do
assignee: []
created_date: '2026-08-06 06:06'
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
- [ ] #1 ADR-021's `### Verification` paragraph describes the gate as shipped and anchoring the decision, matching `binding: true` and `gate: "adr-hook-index-refresh-v1"`
- [ ] #2 The other 32 records are swept for a `### Verification` paragraph that contradicts its own frontmatter, and any found are corrected in the same pass
- [ ] #3 If the sweep finds more than this one, a check is added so a gate flip cannot leave the prose behind again — the existing `tests/test_declared_gate_flip.py` is the natural home
- [ ] #4 `python bin/adr-lint --strict docs/adr` stays clean and `python bin/adr-index --check docs/adr` reports no drift
<!-- AC:END -->
