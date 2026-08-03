---
id: "ADR-018"
title: "Add a Local Precomputed Vector Layer for ADR Retrieval"
status: "Accepted"
date: "2026-08-01"
binding: true
gate: "adr-vector-store-v1"
documents_shipped: false
verified_in: []
supersedes:
  - "ADR-014"
superseded_by: null
topics:
  - "retrieval"
  - "embeddings"
  - "semantic proximity"
  - "selective context"
aliases:
  - "vector layer"
  - "semantic retrieval"
  - "ADR embeddings"
components:
  - "adr-context"
  - "adr-index"
  - "lifecycle hooks"
symbols:
  - "query_adr_context"
  - "FIELD_WEIGHTS"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-018 Add a Local Precomputed Vector Layer for ADR Retrieval

## Status

Accepted, 2026-08-01.

## Status History

```yaml
status_history:
  - date: 2026-08-01
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: spec R6 requires semantic proximity; ADR-014 forbids it in the query path
    changed_via: adr-kit
  - date: 2026-08-01
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Maintainer approved the vector layer direction and resolved all four open questions
    changed_via: adr-kit lifecycle
  - date: 2026-08-01
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: ADR-018 permits a precomputed embedding store in the read path
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

Retrieval today is weighted lexical token overlap over the generated graph.
`bin/adr_query.py:35-44` scores a query against path, symbols, components,
topics, aliases, title and decision summary. It is fast, explainable and
model-free, and for a query that shares vocabulary with an ADR it works well.

It fails on the case the toolkit exists for. A developer writes "should the
commit hook still run when the model is unreachable?" and the ADR that governs
it says "fail open on tooling drift". No token overlaps. The decision is not
retrieved, the agent proceeds without it, and the record that would have kept
the project on course is silent at exactly the moment it was needed.

`spec.md` R6 asks for semantic proximity, retrieval-augmented generation in the
usual industry term, and R5 asks that a model select the final five from the
retrieved candidates. Two Accepted decisions forbid this:

* ADR-014 Must Not: "Introduce a hosted service, database, embedding model, or
  language-model call into the default query or hook path."
* ADR-004 rejects "LLM or embedding retrieval (RAG) for injection", citing "the
  toolkit's standing 'no database, no embeddings, parse Markdown live' design".

So the gap is not effort, it is authority. The constraint was recorded, it is
still doing its job, and it now has to be changed deliberately rather than
worked around. This ADR supersedes ADR-014 because a Decision Contract cannot be
partially amended in this toolkit: there is no `amends` relationship, only
supersession. Everything in ADR-014 that still holds is restated below, and the
single clause that changes is named.

Evidence that the constraint is real rather than assumed: every occurrence of
`embedding`, `cosine`, `faiss`, `chroma` or `sentence-transformer` in this
repository sits inside an ADR's rejected alternatives. Nothing was ever built
and then removed.

## Decision Drivers

* Semantic proximity, because vocabulary mismatch is the dominant miss.
* The hook hot path must stay inside the 2 s budget (ADR-015), stdlib-only
  (ADR-016), and free of network calls, daemons and credentials.
* Determinism first, model judgement where meaning is genuinely the question.
* The final selection of five is a model's judgement (spec R5).
* Reproducibility: two machines must agree on what is in the store, or know
  that they do not.
* Lifecycle authority must remain independent of relevance: a similarity score
  may never make a Superseded decision govern.
* Whatever ships must degrade to today's behaviour rather than break.

## Considered Options

* **Local precomputed store, read-only at hook time.** An explicit build step
  embeds each ADR; the query path reads vectors from disk and scores with
  standard-library arithmetic; the host session model does the final selection.
* **Live embedding at query time** against a local runtime such as Ollama or LM
  Studio.
* **Hosted vector database or retrieval service** as the retrieval engine.
* **Do nothing**, keeping lexical retrieval and rejecting spec R6.

## Decision Outcome

Chosen option: **a local precomputed vector store that the query and hook paths
only read**, because it delivers semantic proximity without putting a model, a
daemon, a credential or a network call anywhere near the hot path.

The generated graph stays exactly as ADR-014 defined it. Markdown remains the
authoring and decision authority. The graph remains the runtime projection, the
lifecycle-authority policy is unchanged, ranking still explains itself, and
`adr-judge` remains the fail-closed enforcement floor while injection stays
fail-open. **The one clause that changes** is ADR-014's prohibition on an
embedding model: embeddings become permitted in a build step, and permitted as
a read in the query path, while remaining prohibited as a computation in the
hook path.

Three properties make that safe.

**The cost moves to a moment where it is visible.** Embedding happens in an
explicit build step, alongside the existing index generation, where a human or
a continuous-integration job asked for it. Nothing embeds because a prompt was
submitted.

**The store is derived, so staleness is detectable rather than silent.** Each
entry records the embedding model identity, the vector dimension and a content
hash of the ADR it came from. A hash mismatch, a dimension mismatch or an
unknown model marks the store stale, and a stale store falls back to lexical
ranking with a visible warning. That is the same posture ADR-014 already takes
towards a stale graph.

**The model that should choose is already running.** Spec R5 asks the language
model to pick the five. It does not follow that the hook must call one. The hook
injects a bounded candidate set with its metadata, and the agent reading that
context, itself a model, already loaded and already paid for, selects what to
apply. This keeps the hook model-free, adds no latency and no per-prompt cost,
and still satisfies R5. A hook that called a model to decide what to tell a
model would be paying twice for one judgement.

Similarity is a candidate generator, never an authority. Lifecycle status
decides what governs, exactly as ADR-014 specified.

### Resolved by the maintainer, 2026-08-01

**Which model embeds.** The same preference order the judge already uses, through
the same `judge.backend` registry: the coding client's own model first, then a
local runtime, then a remote endpoint. The user may force any one of the three.
One registry, one setting, one security rule: repository-tracked configuration
may select a backend but never introduce a command, an endpoint or a credential.

Two consequences of that reuse are accepted deliberately. Changing the judge
backend changes the embedding model, which marks the whole store stale and
forces a rebuild; the recorded model identity makes that visible rather than
silent. And **no coding-client CLI exposes an embeddings endpoint today**:
`claude -p`, `codex exec` and `copilot -p` generate text, and Anthropic publishes
no embeddings API. The client-first order is therefore the stated intent, and in
practice it degrades to the local runtime until a client offers one. Writing the
order down without that sentence would document a preference that silently never
takes effect.

**Where the store lives.** Machine-local and untracked by default, because it is
derived and specific to one embedding model. A team that wants byte-identical
retrieval across machines may switch it to committed through the settings
surface. Both paths ship and both are tested.

**Binding, with a named gate.** This decision is binding and its verification
anchor is `adr-vector-store-v1`. The anchor must exist in source before the
record can be Accepted, which means the first implementation carries the test
that proves the contract rather than the record promising it.

### Confirmation

A query whose wording shares no tokens with the governing ADR returns that ADR.
The worked example above, "fail open when the model is unreachable", is the
acceptance case. Hook latency stays inside the ADR-015 fixture contract with the
store present, and the fallback path is exercised by deleting the store.

## Decision Contract

### Must

* Compute embeddings only in an explicit build step, never during a query or a
  hook.
* Read the store with the standard library only; no third-party runtime
  dependency may be required for retrieval to work.
* Record, per entry: the embedding model identity, the vector dimension, and a
  content hash of the source ADR.
* Treat a missing, unreadable, dimension-mismatched or hash-mismatched store as
  stale, fall back to lexical ranking, and say so.
* Carry lifecycle status and the superseded-by link in the store, so a
  historical decision stays retrievable but never governing.
* Keep the store machine-local and untracked by default, because it is derived
  and specific to one embedding model.
* Keep hook injection fail-open and the commit-time judge fail-closed, unchanged
  from ADR-014.

### Must Not

* Call an embedding model, a language model, or any network endpoint from the
  hook path.
* Require a running daemon for retrieval to function.
* Let a similarity score confer authority on a Proposed, Superseded, Rejected or
  Deprecated decision.
* Hand-edit the store, or treat it as an authoring surface.
* Introduce a hosted vector service.

### Exceptions

* The build step may call a local or remote model, because it is explicitly
  invoked, its cost is visible, and its failure blocks nothing at runtime.

### Verification

* `adr-vector-store-v1`: the named gate anchoring this decision in source. It
  must assert the fallback contract (retrieval works, and says so, with no store
  present) and the staleness contract (a recorded model identity or content hash
  that no longer matches marks the store stale).

## Consequences

### Positive

* Decisions are found by meaning, which is the failure mode lexical retrieval
  could not address.
* The hot path keeps every property that made it defensible: bounded, local,
  deterministic, key-free and model-free.
* The model-chosen five of spec R5 arrives without a second model call.
* The store's staleness rules make a wrong answer detectable instead of quiet.

### Negative

* A second derived artefact to build and keep fresh, with its own staleness
  mode. Mitigated by the content hash and by falling back rather than failing.
* Retrieval quality now depends on an embedding model whose identity must be
  recorded; two machines on different models hold different stores. Mitigated by
  recording the model identity and treating a mismatch as stale.
* Standard-library similarity is slower than a native library. Bounded by the
  ADR set's size, and measured against the ADR-015 budget rather than assumed.
* The absence of embeddings that ADR-014 defended is genuinely lost. That is the
  price of spec R6, and it is being paid deliberately.

## Pros and Cons of the Options

### Local precomputed store, read-only at hook time

* Good, because the hot path stays model-free, offline and standard-library
  only.
* Good, because cost and failure both land in a build step a human triggered.
* Good, because staleness is detectable through a recorded hash and model
  identity.
* Bad, because it adds a derived artefact that can drift.
* Bad, because a fresh clone has no store until the build step runs.

### Live embedding at query time

* Good, because there is nothing to keep fresh.
* Bad, because it needs a daemon reachable at hook time, which breaks the
  offline and no-dependency properties in one step.
* Bad, because it adds per-prompt latency to a path budgeted at two seconds and
  per-prompt cost to a path that currently costs nothing.

### Hosted vector database or retrieval service

* Good, because it scales past any plausible ADR set.
* Bad, because it sends the project's decisions to a third party, needs a
  credential, and fails when the network does. ADR-016's zero-dependency posture
  and ADR-014's key-free hot path both fall.

### Do nothing

* Good, because the current design is simple, fast and proven.
* Bad, because it rejects spec R6 and leaves the vocabulary-mismatch miss
  unaddressed, which is the case the toolkit most needs to catch.

## Open Questions

None. The four questions this record opened were answered by the maintainer on
2026-08-01 and are recorded in the Decision Outcome above.

## Related Decisions

* **ADR-014 Use the Generated ADR Graph as the Selective-Context Query
  Engine:** superseded by this decision. Its graph contract, lifecycle-authority
  policy, explainability rules and fail-open posture are restated here
  unchanged; only its prohibition on an embedding model in the query path is
  overturned.
* **ADR-004 Layered ADR Context Injection for Agent Work:** its rejection of
  embedding retrieval for injection is the second constraint this decision
  changes. The three fail-open injection tiers and the fail-closed enforcement
  floor are preserved.
* **ADR-015 Enforce a Two-Second Deterministic Latency Budget as a Test Fixture
  Contract:** the budget this decision measures against rather than argues with.
* **ADR-016 Serve Both MCP Protocol Eras from One Hand-Rolled Stdio Server:**
  its zero-runtime-dependency property is the reason the store is read with the
  standard library.
* **ADR-007 JSON ADR Graph Index for Agent Retrieval:** the generated-graph
  foundation both this decision and ADR-014 build on.

## References

* `bin/adr_query.py:35-44`: the lexical field weights this decision extends.
* `docs/adr/ADR-014-use-the-generated-adr-graph-as-the-selective-context-query-engine.md`
  Must Not, line 220: the clause being overturned.
* `docs/adr/ADR-004-layered-adr-context-injection.md` lines 138-142: the
  rejected retrieval alternative.
* `spec.md` R5, R6 and R11: the maintainer's stated intent, 2026-08-01.
* `hooks/adr_hook_core.py:24`: the candidate bound this decision feeds.
* MADR, Markdown Any Decision Records, the body profile this record uses:
  https://adr.github.io/madr/
* Cosine similarity over sentence embeddings, the retrieval technique adopted
  here: https://en.wikipedia.org/wiki/Cosine_similarity

## Enforcement

```json
{
  "forbid_pattern": [],
  "forbid_import": [
    {
      "pattern": "^\\s*(?:import|from)\\s+(?:urllib|http|socket|ssl|requests|httpx|subprocess|asyncio)\\b",
      "path_glob": "hooks/adr_hook_core.py",
      "message": "ADR-018 (adr-vector-store-v1): the hook path reads a precomputed store; it may not reach a model, a daemon or the network. Put it in the build step."
    },
    {
      "pattern": "^\\s*(?:import|from)\\s+(?:urllib|http|socket|ssl|requests|httpx|subprocess|asyncio)\\b",
      "path_glob": "bin/adr_query.py",
      "message": "ADR-018 (adr-vector-store-v1): the query path reads a precomputed store; it may not reach a model, a daemon or the network. Put it in the build step."
    }
  ],
  "require_pattern": [],
  "llm_judge": false,
  "llm_judge_reason": "the forbid rules above state the whole constraint mechanically; a model would add cost without adding a verdict"
}
```
