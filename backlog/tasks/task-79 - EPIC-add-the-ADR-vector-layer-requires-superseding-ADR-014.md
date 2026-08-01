---
id: TASK-79
title: 'EPIC: add the ADR vector layer (requires superseding ADR-014)'
status: To Do
assignee: []
created_date: '2026-08-01 10:33'
updated_date: '2026-08-01 10:47'
labels:
  - spec-gap
  - R6
  - R10
  - R11
  - retrieval
  - blocked-on-adr
dependencies: []
priority: high
ordinal: 84500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
spec.md R6, plus the vector halves of R10 and R11.

**Current state.** There is no vector database, no embedding model, no vectors on disk and no similarity metric anywhere in the repository. Retrieval is weighted lexical token overlap over `docs/adr/ADR-INDEX.json` (`bin/adr_query.py:35-44`, FIELD_WEIGHTS path 1.0 / symbols 0.95 / components ...). Every grep hit for embedding, cosine, faiss, chroma or sentence-transformer lands inside an ADR's *rejected alternatives*.

**This is blocked on a decision, not on effort.** R6 is in direct conflict with Accepted ADRs: ADR-014's Must Not forbids introducing a hosted service or a vector index for the query path, and ADR-004:138-142 rejects a vector index for injection. Building the vector layer while those stand would be a violation of the project's own architecture — caught by the kit itself, which is the point.

So this epic starts with a successor ADR (TASK-84) and only then builds.

**What the layer must deliver, once decided:**
- semantic proximity, not only tag/theme/keyword match (R6);
- supersession and lifecycle metadata carried in the vector store as well as the index, so a superseded decision is findable but not governing (R10);
- the candidate set for R5, where the model then picks the five.

**Constraints inherited from the existing architecture, which the successor ADR must either keep or explicitly overturn:** hook hot paths stay local, deterministic, bounded, stdlib-first, model-free and key-free (ADR-014 Must); the 2 s latency budget (ADR-015); zero runtime dependencies (ADR-016). An embedding layer that needs numpy, a daemon or a network call at hook time breaks all three at once. A cached, precomputed store that the hook only *reads* may not.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A successor ADR to ADR-014 is Accepted before any vector code lands
- [ ] #2 Semantic search returns relevant ADRs for a query whose wording does not overlap the ADR text, demonstrated on a concrete example from this repository
- [ ] #3 The store carries status and supersession metadata; a superseded ADR is retrievable and clearly marked non-governing
- [ ] #4 The hook hot path keeps its budget: either it reads a precomputed store, or the successor ADR explicitly overturns the constraint and says what replaces it
- [ ] #5 Embedding generation is reproducible and its provenance recorded, so two machines agree on what is in the store
- [ ] #6 The dependency question is answered explicitly: what ships, what is optional, and what happens when it is absent
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-08-01: ADR-018 is Accepted and ADR-014 is Superseded, both sides linked by `bin/adr supersede`. The blocking decision is resolved; vector work may now start.

Maintainer answers recorded in ADR-018:
- Embedding backend reuses `judge.backend`: client model first, then local, then remote, with the user able to force any one. Noted honestly in the record that no coding-client CLI exposes an embeddings endpoint today, so the client-first order degrades to local in practice.
- Store is machine-local and untracked by default, switchable to committed through the settings surface. Both paths ship and both are tested.
- ADR-018 is binding with named gate `adr-vector-store-v1`.

**Immediate consequence: `adr-lint --strict docs/adr` now exits 1** with `consistency FAIL: gate 'adr-vector-store-v1' was not found`. The named-gate rule requires the anchor to appear literally in a scanned non-docs file. Release workflows run strict lint, so a release is blocked until the first implementation carries that anchor. This was the maintainer's deliberate choice: the record does not promise the contract, the code proves it.

First implementation step should therefore be the anchor plus the part of the contract that is verifiable today: retrieval works, and says so, with no vector store present.
<!-- SECTION:NOTES:END -->
