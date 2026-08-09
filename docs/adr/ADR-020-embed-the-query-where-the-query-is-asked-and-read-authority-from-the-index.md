---
id: "ADR-020"
title: "Embed the Query Where the Query Is Asked, and Read Authority From the Index"
status: "Superseded"
date: "2026-08-09"
binding: true
gate: "adr-query-embedding-v1"
documents_shipped: false
verified_in: []
supersedes:
  - "ADR-018"
superseded_by: "ADR-036"
topics:
  - "retrieval"
  - "embeddings"
  - "semantic proximity"
  - "lifecycle authority"
aliases:
  - "query embedding"
  - "authority join"
  - "vector layer"
components:
  - "adr-context"
  - "adr-embed"
  - "lifecycle hooks"
symbols:
  - "query_adr_context"
  - "search"
  - "staleness"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-020 Embed the Query Where the Query Is Asked, and Read Authority From the Index

## Status

Superseded by ADR-036, 2026-08-09.

## Status History

```yaml
status_history:
  - date: 2026-08-03
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: spec R6.1 permits query-time embedding; ADR-018 forbids it and carries a frozen authority copy that supersession never invalidates
    changed_via: adr-kit
  - date: 2026-08-04
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: "Accepted by the maintainer: query-time embedding is permitted in a query step and in a hook, and authority is read from the index rather than frozen into the store."
    changed_via: adr-kit lifecycle
  - date: 2026-08-04
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: "ADR-020 replaces the embedding-moment prohibition and the frozen authority join: the query is embedded where the query is asked, and authority is read from the index."
    changed_via: adr-kit lifecycle
  - date: 2026-08-09
    status: Superseded
    changed_by: "User: Robert van den Breemen"
    reason: "Superseded by ADR-036: the vector layer is retired; retrieval is lexical over the index plus the graph"
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

ADR-018 authorised a local precomputed vector layer and shipped it. Two months
of it existing have produced no semantic retrieval, because two clauses of its
own Decision Contract make the read path it promises impossible, and a third
assumption in it is false.

**The clauses.** ADR-018 Must: "Compute embeddings only in an explicit build
step, never during a query or a hook." ADR-018 Must Not: "Call an embedding
model, a language model, or any network endpoint from the hook path."

Semantic retrieval is a comparison between two vectors. The store supplies the
first; the second can only come from embedding the query, and the query does not
exist until it is asked. `bin/adr-embed:183` calls `backend.embed()` on the
query for exactly this reason, which is why the standalone diagnostic works and
`query_adr_context` and `hooks/adr_hook_core.py` still rank lexically. Under the
specification's own reading — "a mechanism that exists in the code but that no
shipped path reaches does not count as implemented" — R6 is unimplemented, and
it is unimplemented because a decision forbids the only way to implement it.

This is not a defect in the code. ADR-018 drew its cost boundary at "nothing
embeds because a prompt was submitted", which is the right instinct applied one
step too far: it rules out re-embedding the corpus, and it also rules out the
one small vector that makes the corpus usable.

**The false assumption.** ADR-018 Must: "Treat a missing, unreadable,
dimension-mismatched or hash-mismatched store as stale", and separately "Carry
lifecycle status and the superseded-by link in the store, so a historical
decision stays retrievable but never governing." Those two do not compose.
`embed_text` hashes title, topics, aliases, components and decision — and a
supersession edits none of them. Reproduced twice independently: present the
same record as `Superseded` with `superseded_by` set, and `staleness()` returns
`stale: False` while `search()` returns status `Accepted`, authority
`governing`, `superseded_by` `None`. `adr-embed status` calls the store current.
`bin/adr-embed:42-46` filters only on `adr_id` presence, so a rebuild would not
report the entry as removed either.

The consequence is precisely the failure ADR-014 and ADR-018 both spend
paragraphs preventing: a retired decision handed to an agent as binding, with
nothing anywhere reporting a problem.

A Decision Contract cannot be partially amended in this toolkit — there is no
`amends` relationship, only supersession — so both changes arrive in one
successor. They are one insight in two places: **each fact should be read from
wherever it is currently true.**

## Decision Drivers

* Semantic proximity has to actually reach the query and hook paths, or R6
  remains a diagnostic.
* Lifecycle authority must never lag the record. A supersession takes effect the
  moment it is written, not the next time someone rebuilds a derived artefact.
* The hot path stays inside the 2 s ceiling of spec R21, measured rather than
  asserted.
* Degradation must be visible. A path that silently answers worse is worse than
  one that says it is answering worse.
* The common case stays offline, key-free and free.
* No lifecycle command may become dependent on a model being reachable.

## Considered Options

For the embedding half:

* **Embed the query at query time; keep the corpus a build step.**
* **Keep the ADR-018 prohibition** and accept that semantic retrieval never
  reaches a shipped path.
* **Precompute query vectors** for an anticipated set of queries.

For the authority half:

* **Join status and `superseded_by` from `ADR-INDEX.json` at search time.**
* **A separate lifecycle fingerprint on each entry**, so a status change marks it
  stale.
* **Rebuild the store inside `_commit_lifecycle_changes`**, alongside
  `run_index`.

## Decision Outcome

Chosen option: **embed the query where the query is asked, and read authority
from the index**, because it puts each fact where it is cheap and where it is
current, and it removes a frozen copy that had no way to know it was wrong.

**The corpus stays a build step.** Re-embedding every ADR on every prompt would
exceed R21 by orders of magnitude and would spend model work on text that has not
changed. ADR-018 was right about that, and nothing here relaxes it.

**Embedding the query is a different act, and it is permitted — in a query step
and in a hook.** It is one short string and one small vector, so the cost is
bounded in a way that rebuilding the corpus is not. This is the clause of
ADR-018 that changes, and it changes because the alternative is a feature that
cannot exist.

**Authority is joined at search time, never carried.** The store answers *which*
ADRs; `ADR-INDEX.json` answers *what they are worth*. Status, `superseded_by` and
the derived authority come from the index on every search. An entry whose
`adr_id` is absent from the index is a record that no longer exists and is
dropped rather than returned unlabelled.

Three properties keep the embedding change honest, and each is a test rather
than a promise:

**Budget.** The query path stays inside R21's ceiling with the backend's own
timeout well under it. The manifest budgets 500 ms for `session-start` and
`user-prompt-submit` and 100 ms for the pre- and post-tool events; an embedding
round trip does not fit 100 ms, so those events keep the index-only route.

**Fail-soft, and audible.** An unreachable, slow, or erroring backend falls back
to lexical ranking, exits 0, and names which route answered in the output. It
never fails a hook and never blocks a prompt. A user must be able to see that
they got the lexical answer.

**A local default.** The backend is the local runtime of spec R16, so the common
case is offline and key-free. A remote endpoint is the user's choice, made
through the settings surface after being told the latency and privacy
consequence.

Everything else in ADR-018 stands and is restated by reference rather than
rewritten: Markdown remains the authoring and decision authority, the store is
read with the standard library only, the store is machine-local and untracked by
default with a committed option, the build step may call a model because it is
explicitly invoked, the host session model still performs R5's final selection,
injection stays fail-open and `adr-judge` stays fail-closed.

### Why not the alternatives

**Keeping the prohibition** would mean amending spec R6 to say the toolkit does
not do semantic retrieval. That is an honest option and it was weighed; it was
rejected because the failure R6 exists to fix — a query whose wording shares no
tokens with the governing ADR — is the dominant miss, and lexical ranking cannot
close it by construction.

**Precomputing query vectors** requires knowing the queries, which is the one
thing that cannot be known ahead of a prompt.

**A lifecycle fingerprint** keeps the store self-describing without the index,
but every acceptance and every supersession would then mark it stale and demand
a rebuild — model work triggered by a metadata change. It also leaves a window
in which the store is knowingly wrong.

**Rebuilding inside the lifecycle transaction** makes `bin/adr accept` depend on
a reachable embedding backend. A lifecycle command that fails because a local
runtime is not running is a worse failure than a slightly stale vector, and it
would put model latency inside a transaction that must stay atomic.

### Confirmation

Three acceptance cases, all of which fail against the code as it stands:

1. A query sharing no tokens with the governing ADR returns that ADR through a
   shipped path — `query_adr_context`, not the standalone diagnostic.
2. Superseding an ADR without touching its Decision text makes the store stop
   returning it as `governing`, with no rebuild.
3. With the embedding backend unreachable, the same query returns the lexical
   answer, exit 0, with the route named in the output.

Latency is measured against R21 through the fixture contract of ADR-015 rather
than wall-clock against a live model.

## Decision Contract

### Must

* Compute corpus embeddings only in an explicit build step.
* Embed the query in the path that asks it, including a hook, when the store is
  present and a backend is configured.
* Read status, `superseded_by` and authority from `ADR-INDEX.json` on every
  search, never from the stored entry.
* Drop a stored entry whose `adr_id` is absent from the index.
* Name the retrieval route — vector or lexical — in the output the user sees.
* Fall back to lexical ranking and exit 0 on any backend failure, timeout, or
  malformed response.
* Keep the query-embedding path inside spec R21's ceiling, with a backend
  timeout strictly below it, verified by a test.
* Keep the 100 ms pre- and post-tool events on the index-only route.
* Read the store with the standard library only.
* Record, per entry: the embedding model identity, the vector dimension, and a
  content hash of the source ADR.
* Keep hook injection fail-open and the commit-time judge fail-closed.

### Must Not

* Re-embed the corpus during a query or a hook.
* Let a lifecycle command depend on a reachable embedding backend.
* Let a similarity score confer authority on a Proposed, Superseded, Rejected or
  Deprecated decision.
* Answer from vectors without saying so when the lexical route was used instead.
* Require a running daemon for retrieval to function at all.
* Hand-edit the store, or treat it as an authoring surface.
* Introduce a hosted vector service.

### Exceptions

* A remote embedding endpoint is permitted when the user has selected one
  through the settings surface, having been told the latency and privacy
  consequence. It is never the default and never selected by probing.

### Verification

* `adr-query-embedding-v1`: the gate that anchors this decision. It ships in
  `tests/test_adr_semantic_route.py`, so `gate` carries the name and `binding`
  is true. It covers the three acceptance cases above and the R21 latency
  bound.

## Consequences

### Positive

* R6 becomes reachable from a shipped path rather than a diagnostic.
* A supersession takes effect immediately, everywhere, with no rebuild.
* One source of lifecycle truth. The index was already required to be current
  (spec R7); this stops a second copy from disagreeing with it.
* Changing the embedding model no longer needs to invalidate authority, only
  similarity — a smaller and more honest blast radius.

### Negative

* **The hot path now depends on an embedding backend being reachable.** That is
  the real cost of this decision and it is not mitigated away: it is bounded.
  The failure is soft, it is visible in the output, and the default backend is
  local. A user with no runtime gets today's lexical behaviour and is told so.
* **Retrieval correctness now depends on index freshness.** Joining authority
  from `ADR-INDEX.json` means a stale index yields stale authority. The index was
  already required to be current, and the stale-index route is a sibling decision
  rather than an afterthought.
* **A remote backend sends the query text off the machine.** Stated here so the
  settings surface can state it too. The local default exists for this reason.
* ADR-018 is superseded within days of being accepted. That reads badly and it is
  the correct record: the decision was made, its contract was found to forbid its
  own purpose, and the correction is visible rather than quietly patched into an
  Accepted document.

## Pros and Cons of the Options

### Embed the query at query time

* Good, because it is the only option under which semantic retrieval exists.
* Good, because the cost is one short string per query, not a corpus.
* Bad, because the hot path acquires a dependency it did not have.

### Keep the ADR-018 prohibition

* Good, because the hot path stays trivially offline and free.
* Bad, because it means amending spec R6 to abandon semantic retrieval.

### Precompute query vectors

* Good, because it would preserve the read-only hot path exactly.
* Bad, because it requires knowing the queries in advance, which is the one
  thing that cannot be known.

### Join authority from the index

* Good, because authority is read where it is current, so a supersession needs
  no rebuild.
* Good, because it costs one dictionary lookup per result.
* Bad, because retrieval correctness now depends on index freshness.

### Lifecycle fingerprint on each entry

* Good, because the store stays readable without the index.
* Bad, because every acceptance and supersession triggers model work.
* Bad, because it leaves a window where the store is knowingly wrong.

### Rebuild inside the lifecycle transaction

* Good, because the store is fresh by construction after every command.
* Bad, because `bin/adr accept` would fail when a local runtime is not running.

## Open Questions

* None.

## Related Decisions

* Supersedes ADR-018, whose embedding-moment prohibition and frozen authority
  copy this decision replaces.
* Builds on ADR-014's separation of similarity from authority, which is the
  principle this decision implements more strictly rather than relaxes.
* Constrained by ADR-016's zero-third-party-dependency rule: the store is read
  with the standard library, and a backend is reached over a socket rather than
  through a client library.
* Bounded by ADR-015's latency contract, extended to the command line by spec
  R21.

## References

* `bin/adr-embed:183` — the query embedding call that only the standalone
  diagnostic reaches.
* `bin/adr-embed:42-46` — the rebuild filter that keys on `adr_id` presence
  alone.
* `hooks/adr_hook_core.py` `_query` — the shipped path that ranks lexically.
* `docs/adr/ADR-018-add-a-local-precomputed-vector-layer-for-adr-retrieval.md` —
  the Decision Contract this supersedes.
* `spec.md` R6.1, R7, R16, R21.
