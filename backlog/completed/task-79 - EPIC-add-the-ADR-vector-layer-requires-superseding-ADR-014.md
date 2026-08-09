---
id: TASK-79
title: 'EPIC: add the ADR vector layer (requires superseding ADR-014)'
status: Done
assignee: []
created_date: '2026-08-01 10:33'
updated_date: '2026-08-02 02:18'
labels:
  - spec-gap
  - R6
  - R10
  - R11
  - retrieval
  - blocked-on-adr
dependencies: []
modified_files:
  - bin/adr-embed
  - bin/adr_vector_store.py
  - bin/adr_llm.py
  - tests/test_adr_vector_store_contract.py
  - .gitignore
  - CHANGELOG.md
  - codex/
  - copilot/
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
- [x] #2 Semantic search returns relevant ADRs for a query whose wording does not overlap the ADR text, demonstrated on a concrete example from this repository
- [x] #3 The store carries status and supersession metadata; a superseded ADR is retrievable and clearly marked non-governing
- [x] #4 The hook hot path keeps its budget: either it reads a precomputed store, or the successor ADR explicitly overturns the constraint and says what replaces it
- [x] #5 Embedding generation is reproducible and its provenance recorded, so two machines agree on what is in the store
- [x] #6 The dependency question is answered explicitly: what ships, what is optional, and what happens when it is absent
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

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The vector layer ships: `bin/adr-embed` (build, status, query) over `bin/adr_vector_store.py`, with the gate anchor extended to cover staleness now that a store exists to be stale.

**Verified end to end** on a scratch copy of this ADR set rather than by assertion alone: 18 records embedded at 768 dimensions through nomic-embed-text via Ollama, `status` reporting the set current, and a query with no shared vocabulary surfacing ADR-002 at rank two where the lexical ranking missed it entirely. Reported honestly: on queries that do share vocabulary the two rank similarly, which is what a candidate generator should do rather than a replacement.

The boundary from ADR-018 is implemented as written. `build` is the only path that may call a model and is invoked by a human or CI - nothing embeds because a prompt arrived. The read path is standard-library cosine over a file, so ADR-016's zero dependencies and ADR-015's budget both hold, and the gate anchor asserts structurally that neither hot-path module imports anything able to reach a model or the network.

Staleness is detectable rather than silent: model identity, dimension and a per-ADR content hash. An edited, added or removed record marks the store stale; a dimension mismatch refuses the store outright rather than scoring against vectors from a different model. Missing or stale degrades to lexical ranking with a reason.

Similarity never confers authority - a Superseded decision stays findable and stays non-governing, tested by giving the superseded record the *nearest* vector and asserting it is still excluded.

Embedding reuses the judge registry per the maintainer's answer. `HttpBackend` gained `_post_to` so embedding reaches a sibling endpoint under one set of failure semantics instead of a second copy that would drift. `host` reports plainly that no coding-client CLI exposes an embeddings endpoint, which is the honest consequence recorded in ADR-018.

**Not in scope, and left to TASK-81:** wiring the store into the UserPromptSubmit hook so the model picks five from vector candidates. That needs the Python and Rust hooks to stay in parity and the 2 s budget measured, which is exactly what TASK-81 already describes. The store and its read API are ready for it.

AC #1 was met before this task started: ADR-018 was Accepted and ADR-014 superseded on 2026-08-01.

Gates: 1313 passed / 12 skipped, adapter drift clean, adr-lint --strict clean.</finalSummary>
<!-- SECTION:FINAL_SUMMARY:END -->
