---
id: "ADR-036"
title: "Retire the vector layer and run the judge on the host model only"
status: "Accepted"
date: "2026-08-09"
binding: true
gate: "adr-host-only-judge-v1"
documents_shipped: false
verified_in:
  - "tests/test_adr_judge_llm.py"
supersedes:
  - "ADR-017"
  - "ADR-020"
superseded_by: null
related:
  - "ADR-001"
  - "ADR-014"
  - "ADR-025"
  - "ADR-034"
topics:
  - "simplification"
  - "llm judging"
  - "backend selection"
  - "semantic retrieval"
aliases:
  - "KISS simplification"
  - "vector layer retirement"
  - "host-only judge"
components:
  - "adr-judge"
  - "adr-embed"
  - "adr-context"
symbols:
  - "judge.backend"
  - "BACKENDS"
  - "ADR_KIT_LLM_CMD"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-036 Retire the vector layer and run the judge on the host model only

## Status

Accepted, 2026-08-09.

## Status History

```yaml
status_history:
  - date: 2026-08-09
    status: Proposed
    changed_by: adr-kit
    reason: Initial proposal
    changed_via: adr-kit
  - date: 2026-08-09
    status: Proposed
    changed_by: adr-kit
    reason: Related to ADR-001
    changed_via: adr-kit lifecycle
  - date: 2026-08-09
    status: Proposed
    changed_by: adr-kit
    reason: Related to ADR-014
    changed_via: adr-kit lifecycle
  - date: 2026-08-09
    status: Proposed
    changed_by: adr-kit
    reason: Related to ADR-025
    changed_via: adr-kit lifecycle
  - date: 2026-08-09
    status: Proposed
    changed_by: adr-kit
    reason: Related to ADR-034
    changed_via: adr-kit lifecycle
  - date: 2026-08-09
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: "Approved in session: KISS simplification, four framing choices made by the maintainer on 2026-08-09"
    changed_via: adr-kit lifecycle
  - date: 2026-08-09
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: "Superseded by ADR-036: judge runs on the host model only; the multi-backend registry is retired"
    changed_via: adr-kit lifecycle
  - date: 2026-08-09
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: "Superseded by ADR-036: the vector layer is retired; retrieval is lexical over the index plus the graph"
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

The maintainer reviewed the embedding and backend machinery on 2026-08-09 and
judged it heavier than the problem it solves. Measured against the spec's own
bar - "a mechanism that exists in the code but that no shipped path reaches
does not count as implemented" - the two heaviest subsystems fail it:

**The vector layer** (ADR-018, ADR-020). No vector store exists in this
repository, so the layer has never run here. The shipped rerank in
`bin/adr_query.py` receives the lexical candidate list only after the
`min_score` filter and the `ordered[:limit]` truncation, so an ADR whose
wording shares no tokens with the query - the exact miss spec R6 existed to
close - never reaches the vector pass at all. The pass reorders candidates
lexical ranking already found. Full semantic search over the store exists only
in `adr-embed query`, whose own help text labels it a diagnostic for checking
the store. The corpus this repository governs is 36 records.

**The backend registry beyond `host`** (ADR-017). Three HTTP backends
(openrouter, ollama, openai-compatible), their credential refusals, the
runtime probes and the spec R16 setup dialogue total roughly 550 lines of
`bin/adr_llm.py` plus about 700 dedicated test lines. The `host` backend -
the one that actually runs, spawning the coding client's own CLI on stdin -
is about 60 lines. No user of this repository has selected any other backend.

Combined footprint: roughly 1,500 production lines, 1,300 dedicated test
lines, about 12 configuration keys, one spec requirement (R16) that exists
only to provision another (R6), and a per-prompt network declaration on the
`user-prompt-submit` hook event (ADR-034) that exists only for query
embedding.

The complexity is specified, not accidental: spec R6, R6.1, R11 (embedding
half), R12 (multi-backend) and R16 demand exactly this machinery. The kit
therefore cannot become simpler and stay conformant unless the spec moves.
Amending the spec deliberately, and superseding the records that implement
it, is this decision.

## Decision Drivers

* The maintainer's stated judgement: the vector layer and the local-model
  backend surface feel heavy and unnecessary for what they deliver.
* The spec's implemented-means-reachable bar, which both subsystems fail.
* At 36 ADRs, frontmatter retrieval metadata (`topics`, `aliases`, `symbols`,
  `components`) plus one-hop graph neighbours already answer the
  zero-token-overlap miss; the scorer reads all of them.
* Every removed line is maintenance, test time and attack surface the kit no
  longer pays for; R18's zero-dependency stance makes hand-rolled subsystems
  expensive by construction.
* A network path in a per-prompt hook is a standing privacy and latency
  liability even when it points at localhost (ADR-034 had to declare it).

## Considered Options

* Retire the vector layer and the HTTP backends definitively; the judge runs
  on the host model plus one operator escape hatch.
* Retire with a named re-entry condition (a measured recall failure in the
  retrieval probes, or corpus growth toward ~500 records).
* Keep the vector layer and fix the recall gap (widen the candidate set ahead
  of the rerank).
* Keep one local HTTP backend (ollama) for headless and CI judging.
* Do nothing.

## Decision Outcome

Chosen option: **retire definitively; host model plus operator escape hatch**.

The maintainer chose definitive retirement over a re-entry condition: a
half-open door invites relitigating the decision without new evidence. If the
need ever returns, a future ADR supersedes this one on its own evidence -
that is the ordinary supersession path (R10), and it needs no reservation
written here.

Concretely:

1. **Spec.** R6, R6.1 and R16 are retired and tombstoned in `spec.md` (the
   requirement number remains with a three-line note naming this ADR). R11
   keeps the graph and drops the embeddings clause. R12 reduces to the host
   backend plus the operator escape hatch.
2. **Records.** This ADR supersedes ADR-017 (backend registry) and ADR-020
   (query-time embedding, itself the successor of ADR-018's vector store, so
   the chain 014 to 018 to 020 to this record stays traceable). ADR-025's
   rule -
   tracked configuration selects, only a machine may introduce - stands
   unchanged and becomes structurally true: with no network backend to
   select, committed configuration has nothing left to point off-machine.
   ADR-014's original prohibition on embedding models in the retrieval path,
   which ADR-018 had carved an exception into, holds again without exception.
3. **Judge.** `judge.backend` resolves to the host client's CLI recorded at
   install time (`claude -p`, `codex exec`, `copilot -p`), exactly as
   ADR-017 shipped it. The operator escape hatch (`ADR_KIT_LLM_CMD`,
   `--llm-cmd`) remains, because it is operator-controlled and never
   repository-controlled. On a machine without an agent CLI the LLM pass
   degrades to declarative-only with one warning - the floor ADR-001
   defined and ADR-017 retained.
4. **Retrieval.** Lexical scoring over the generated index plus one-hop graph
   neighbours; the session model performs the final relevance selection
   (spec R5). The `user-prompt-submit` hook event returns to
   `network_allowed: false`. The graph carries a Decision Contract only for
   governing records: a Superseded node keeps its identity, links and
   metadata, but its contract is emptied in the index, because authority is
   joined from status at search time and the full contract stays in the
   Markdown record. This is what keeps the graph inside ADR-014's
   2 KiB-per-ADR context budget as the superseded tail grows.
5. **Code.** The embedding subsystem, the three HTTP backends and their
   configuration keys are removed under TASK-144, TASK-145 and TASK-146,
   in that order, after this record is Accepted. Removed configuration keys
   are refused by name with a sentence naming the replacement.

What this deliberately reverses is acknowledged by task id rather than
erased: TASK-79, TASK-85, TASK-87, TASK-94, TASK-107, TASK-109, TASK-135
built what this decision retires. The work was competently done; the scale
that would justify it never arrived.

### Confirmation

`docs/plans/kiss-simplification-plan.md` carries the execution order.
TASK-144 and TASK-145 implement the removals. The gate
`adr-host-only-judge-v1` is registered at acceptance as a strict-xfail
placeholder in `tests/test_adr_judge_llm.py`, the same way
`adr-judge-backend-registry-v1` began under ADR-017: the placeholder asserts
the end state (the registry resolves `host` and nothing else), xfails while
the HTTP backends still exist, and turns into an error the moment TASK-145
lands, forcing its replacement with the real conformance suite.

## Decision Contract

### Must

* `bin/adr_llm.py` resolves one named backend: `host`.
* The operator escape hatch (`ADR_KIT_LLM_CMD`, `--llm-cmd`) keeps its
  existing behaviour and safety checks.
* Without host client or escape hatch, the LLM pass degrades to
  declarative-only with one warning (ADR-001 floor).
* No hook event declares `network_allowed: true` (ADR-034).
* Removed configuration keys are refused by name, replacement named.

### Must Not

* Reintroduce an HTTP backend, embedding call or vector-store read into a
  shipped path without superseding this ADR.
* Let tracked configuration name a binary, endpoint or credential (ADR-025).

### Exceptions

* None.

### Verification

* TASK-145's registry regression test, recorded here as the gate when it
  ships; `python -m pytest -q` green across TASK-144 and TASK-145.

## Consequences

### Positive

* Roughly 1,500 production and 1,300 test lines retired; about 12
  configuration keys removed; no daemon, no model download, no network in
  any hook.
* The security rule of ADR-025 becomes structural instead of argued: there
  is no network backend for committed configuration to select.
* Setup loses the R16 dialogue entirely, which clears the way for one setup
  entry point (TASK-148).
* The judge's behaviour is again identical on every machine with the same
  client installed.

### Negative

* Headless machines (CI, a laptop without an agent CLI) lose the LLM pass
  and run declarative-only. Accepted: that is ADR-001's floor, and the
  declarative gates are the enforcement tier that matters at commit time.
  The escape hatch remains for an operator who needs more.
* A future genuine recall problem has no semantic layer to lean on.
  Accepted: it would take a new ADR with its own evidence, and frontmatter
  metadata plus the graph carry retrieval at the current corpus size.
* Prior work (seven tasks) is reversed. Accepted and recorded above.

## Pros and Cons of the Options

### Retire definitively; host plus escape hatch (chosen)

* Good, because the kit sheds its two heaviest unreachable subsystems and
  the spec stops demanding machinery nobody uses.
* Good, because the privacy posture simplifies to: the diff goes to the
  client you already signed into, or nowhere.
* Bad, because headless judging is gone; mitigated by the declarative floor
  and the operator escape hatch.

### Retire with a named re-entry condition

* Good, because it records when the question may return.
* Bad, because it keeps the argument alive without new evidence; the
  maintainer rejected it for exactly that reason. Supersession by a future
  ADR is the re-entry path and needs no reservation.

### Keep the vector layer and fix the recall gap

* Good, because the zero-overlap miss is real in principle.
* Bad, because at 36 records the fix buys reordering of a top-5 that
  metadata already gets right, at the price of a runtime, a store, a
  rebuild obligation and a per-prompt network path.

### Keep one local HTTP backend for headless judging

* Good, because CI could run the LLM pass.
* Bad, because it keeps ~200 lines plus tests alive for a pass whose
  authority tier at commit time is advisory; the declarative gates are the
  floor, and they run everywhere already.

### Do nothing

* Bad, because the spec keeps demanding what no shipped path delivers, which
  is the exact drift between record and reality this kit exists to prevent.

## Open Questions

None. The four choices this record rests on were made by the maintainer in
session on 2026-08-09: definitive retirement over a re-entry condition, host
plus operator escape hatch over host-only and over keeping ollama, tombstones
in the spec over deletion, and one superseding record over amendment in
place.

## Related Decisions

* ADR-001 - the declarative-only floor this decision degrades to on machines
  without an agent CLI.
* ADR-014 - source of the graph budget and of the original prohibition on
  embedding models in the retrieval path, whose substance this decision
  restores.
* ADR-025 - tracked configuration selects, only a machine introduces; stands
  and becomes structural.
* ADR-034 - the per-event network declaration; its one open declaration
  closes with the removal.

## References

* docs/plans/kiss-simplification-plan.md (execution order and task table)
* spec.md R6, R6.1, R11, R12, R16 (amended by this decision), R10, R18, R21
* backlog TASK-143 (this record), TASK-144, TASK-145, TASK-146 (removals),
  TASK-148 (setup consolidation this unblocks)
* Reversed prior work: TASK-79, TASK-85, TASK-87, TASK-94, TASK-107,
  TASK-109, TASK-135
