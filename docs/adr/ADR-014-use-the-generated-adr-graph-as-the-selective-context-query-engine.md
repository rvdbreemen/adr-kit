---
id: "ADR-014"
title: "Use the Generated ADR Graph as the Selective-Context Query Engine"
status: "Superseded"
date: "2026-08-01"
binding: true
gate: "index-first-retrieval"
documents_shipped: false
verified_in:
  - "bin/adr_query.py:INDEX_FIRST_RETRIEVAL_GATE"
  - "tests/test_adr_query.py"
  - "tests/test_adr_retrieval_health.py"
  - "hooks/adr_hook_core.py"
supersedes: []
superseded_by: "ADR-018"
related:
  - "ADR-036"
  - "ADR-040"
topics:
  - "ADR retrieval"
  - "selective context"
  - "architecture governance"
aliases:
  - "ADR index"
  - "index-first retrieval"
components:
  - "ADR-INDEX.json"
  - "adr-context"
  - "adr-mcp"
  - "lifecycle hooks"
symbols:
  - "index-first-retrieval"
context_scope: "global"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-014 Use the Generated ADR Graph as the Selective-Context Query Engine

## Status

Superseded by ADR-018, 2026-08-01.

## Status History

```yaml
status_history:
  - date: 2026-07-23
    status: Proposed
    changed_by: Codex
    reason: Initial proposal
    changed_via: adr-kit
  - date: 2026-07-23
    status: Accepted
    changed_by: Robert
    reason: Explicit human acceptance after ADR grill and verified TASK-52.2/TASK-52.3 implementation
    changed_via: adr-kit lifecycle
  - date: 2026-08-01
    status: Superseded
    changed_by: "User: Robert van den Breemen"
    reason: ADR-018 permits a precomputed embedding store in the read path
    changed_via: adr-kit lifecycle
  - date: 2026-08-09
    status: Superseded
    changed_by: adr-kit
    reason: Related to ADR-036
    changed_via: adr-kit lifecycle
  - date: 2026-08-19
    status: Superseded
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-040
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

ADR Kit already generates `docs/adr/ADR-INDEX.json` as a deterministic,
versioned graph, but the main task-query command does not use that artifact as
its query engine. `bin/adr-context` discovers and parses every numbered Markdown
ADR for every request (`bin/adr-context:322-368`). In contrast, the lifecycle
hooks already load the generated graph (`hooks/adr_hook_core.py:164-189`) and
rank its bounded records for prompt and edit context
(`hooks/adr_hook_core.py:234-306`).

This split has three observable costs:

* the command-line interface (CLI), Model Context Protocol (MCP), and hooks can
  produce different rankings because they do not use one query contract;
* query latency grows with the number and size of Markdown ADRs even though the
  generated graph already contains a compact record for each decision; and
* the graph lacks explicit selective-retrieval fields such as topics, aliases,
  components, symbols, baseline context scope, and concise decision
  constraints, so unscoped ADRs depend mainly on lexical overlap.

On 2026-07-23, three local end-to-end samples had a median of 548.7 ms for the
14 numbered adr-kit ADRs and 2609.6 ms for the 169-record OTGW fixture corpus.
The current generated graph was 14,553 bytes. These measurements include Python
startup, Markdown discovery, parsing, ranking, and JSON rendering. They are a
baseline, not yet an acceptance threshold.

ADR-004 establishes three fail-open context tiers plus one fail-closed
enforcement floor. ADR-005 requires format-neutral semantic roles across MADR,
Nygard, and canonical records. ADR-007 establishes Markdown ADRs as the source
of truth and `ADR-INDEX.json` as a generated graph for agent discovery. This
decision completes that architecture by making the graph the normal runtime
query projection without turning it into a hand-edited authority.

The repository maintainer approved this direction and requested a Backlog epic,
focused tasks, a Proposed ADR, and human grilling. The detailed schema,
fallback, ranking, and compatibility choices remain subject to the Open
Questions below.

## Decision Drivers

* Agents should shortlist relevant decisions without reading every ADR.
* CLI, MCP, guardian, review, and client hooks need one deterministic retrieval
  outcome contract.
* Accepted, Proposed, and historical ADRs must never acquire authority merely
  because of a relevance score.
* Markdown must remain the durable human-reviewed decision authority.
* Query and hook hot paths must remain local, key-free, model-free,
  dependency-free, bounded, and explainable.
* Existing MADR, Nygard, canonical, legacy, and schema-v1 projects need a safe
  compatibility path.
* Missing, corrupt, unsupported, or stale generated data must fail visibly
  without blocking normal agent work.
* Retrieval quality and performance need project-level evidence rather than an
  assumed heuristic.

## Considered Options

* Query a versioned generated graph through one shared deterministic engine,
  with explicit compatibility fallback to Markdown.
* Keep Markdown-first querying and use the generated graph only for hooks and
  orientation.
* Make `ADR-INDEX.json` a hand-edited retrieval authority independent of the
  Markdown ADRs.
* Add embeddings or a hosted/vector database as the primary retrieval engine.

## Decision Outcome

Chosen direction: **query a versioned generated ADR graph through one shared
deterministic engine, with Markdown retained as the decision authority and
compatibility fallback**.

The generated graph becomes the normal runtime projection for selective
context. Markdown remains the only authoring and decision authority. A healthy,
supported graph must be sufficient to rank candidates without opening every
Markdown ADR. The agent still opens the shortlisted source records before
applying or citing a binding constraint.

The graph will carry bounded, format-neutral selective metadata derived from
Markdown. The working contract adds topics, aliases, components, symbols,
context scope, and an optional concise Decision Contract while retaining the
existing lifecycle, relationship, Enforcement scope, evidence, and decision
summary fields. Query-specific scores remain transient and are not persisted.

One shared query specification will separate relevance from authority:
Accepted decisions govern, Proposed decisions are advisory, and Superseded,
Rejected, and Deprecated decisions are historical and excluded from governing
results by default. Path, symbol, component, topic, alias, title, decision, and
constraint evidence will be explainable. Declared relationships may add bounded
supporting context after a primary match; raw relationship count and recency
will not make an ADR governing.

CLI and MCP calls will expose the same outcome. Python and native lifecycle
hooks will certify against the same fixtures while preserving each client's
capabilities. Context injection stays fail-open. `adr-judge` at commit and pull
request time remains the fail-closed enforcement floor.

Missing, invalid, unsupported, or stale graph handling will be explicit and
observable. The compatibility posture is to warn and use the existing Markdown
semantic loader. Hooks keep that fallback bounded and fail open. Continuous
integration (CI), diagnostics, and an explicit strict-index mode report failure
instead of silently falling back.

The human decision maker confirmed that the richer graph contract will be
published as schema version 2 rather than extending schema version 1 in place.
New readers will retain schema-v1 compatibility for one minor-release window,
and existing result fields will remain available during that window.

The human decision maker also confirmed the selective authoring contract:
flat `topics`, `aliases`, `components`, and `symbols` string lists; scalar
`context_scope` with `global` and `selective` values; and an optional
`## Decision Contract` containing Must, Must Not, Exceptions, and Verification
content. Enforcement `path_glob` rules remain the sole path-scope authority.

The human decision maker confirmed the default lifecycle-authority policy:
Accepted ADRs are governing results; Proposed ADRs are clearly labelled
advisory context and never governing; Superseded ADRs are excluded by default
and redirect to their successors; and Rejected or Deprecated ADRs are excluded
unless historical results are explicitly requested.

The human decision maker confirmed that ranking uses only positive query
evidence. Exact path, symbol, and component matches are strongest, followed by
topic, alias, title, Decision Contract, and decision-summary matches. Lifecycle
status controls authority but does not add relevance; recency and relationship
count add no score. A primary result may expand to at most two one-hop
supporting ADRs. Results explain their matched fields and use ADR ID as the
stable final tie-breaker.

The human decision maker confirmed the release thresholds. Curated probes must
place the required governing ADR top-1 at least 90% of the time and top-3 in
100%, with zero historical leakage and zero governing results for explicit
no-match probes. Across 30 cold-process, warm-filesystem samples, p95 query
latency must remain at or below 250 ms through 200 ADRs and 500 ms through
1,000 ADRs. Hook p95 remains 250 ms with a 500 ms semantic hard timeout; the
five-second client runner timeout is only an outer Windows safety margin. The
graph must average at most 2 KiB per ADR plus 16 KiB fixed overhead and remain
at or below 25% of the Markdown corpus. A healthy normal query must open no
numbered Markdown ADR; only shortlisted source ADRs are opened for confirmation.

### Decision ownership

* **Decision maker:** repository maintainer (human).
* **Implementation owner:** adr-kit maintainers and implementation agents
  operating through TASK-52 and its child tasks.
* **Lifecycle authority:** the active human session; neither source material nor
  a completed implementation implies acceptance.

## Decision Contract

### Must

* Keep Markdown ADRs authoritative and all index content generated.
* Use a healthy supported graph as the primary runtime retrieval projection.
* Separate lifecycle authority from relevance and explain positive matches.
* Keep query and hook hot paths local, deterministic, bounded, stdlib-first,
  model-free, and key-free.
* Preserve fail-open context injection and fail-closed judge enforcement.

### Must Not

* Hand-edit generated retrieval metadata in `ADR-INDEX.json`.
* Treat Proposed or historical ADRs as governing Accepted decisions.
* Parse every Markdown ADR during a healthy normal index query.
* Introduce a hosted service, database, embedding model, or language-model call
  into the default query or hook path.

### Exceptions

* A clearly reported compatibility fallback may parse Markdown when the graph
  is missing, invalid, unsupported, or stale.
* An explicit historical query may return non-governing superseded, rejected,
  or deprecated records.

### Verification

Confirm the decision with:

* versioned frontmatter and graph schemas plus deterministic generation tests;
* equivalent retrieval records across MADR, Nygard, canonical, and legacy
  fixtures;
* shared query fixtures for CLI, MCP, Python hooks, native hooks, Claude, Codex,
  and Copilot;
* lifecycle-authority, historical-exclusion, supersession, no-match, and
  fallback tests;
* project retrieval probes with required top-k inclusions and exclusions;
* end-to-end performance and graph-size budgets on small and representative
  large ADR sets;
* strict ADR lint, doctor, generated artifact checks, client payload
  synchronization, native certification, focused tests, and the full supported
  regression suite; and
* a literal `index-first-retrieval` verification anchor in shipped non-document
  source before this binding ADR can be Accepted.

## Consequences

### Positive

* Agents query one compact local projection and open only the best source ADRs.
* CLI, MCP, hooks, guardian, and review can explain consistent results.
* Lifecycle authority becomes explicit instead of being mixed into a relevance
  score.
* Large ADR sets avoid repeated Markdown parsing on healthy queries.
* Project probes make corpus quality and retrieval regressions reviewable.
* The design remains local, inspectable, portable, and dependency-free.

### Negative

* The generated graph becomes a more important runtime artifact and stale data
  can hide a new decision. Lifecycle regeneration, index checks, doctor,
  freshness detection, visible fallback, and CI strict mode mitigate this.
* Authors gain optional retrieval metadata and a Decision Contract to maintain.
  Templates, grilling, dry-run suggestions, and advisory-first lint mitigate
  the burden.
* A graph schema change and result-surface additions create compatibility work.
  Versioned readers, preserved legacy fields, migration warnings, and a
  documented compatibility window mitigate it.
* Python and native clients can drift if they reimplement scoring differently.
  One outcome specification and shared certification fixtures mitigate this.
* Deterministic lexical retrieval cannot infer every synonym. Explicit aliases,
  project probes, and source-ADR confirmation mitigate false negatives without
  adding an opaque semantic service.

## Pros and Cons of the Options

### Generated graph as the shared query engine

* Good, because the graph is already generated, deterministic, local, bounded,
  and consumed by lifecycle hooks.
* Good, because parsing and normalization move to index generation instead of
  every query.
* Good, because structured fields make matching explainable and testable.
* Bad, because graph freshness and schema compatibility become operationally
  important.

### Keep Markdown-first querying

* Good, because every query sees the current source files without depending on
  a generated artifact.
* Good, because it preserves the current public behavior.
* Bad, because it repeats discovery and parsing work and retains divergent
  query implementations.
* Bad, because adding richer retrieval metadata would not make the existing
  graph the actual runtime engine.

### Hand-edit the JSON graph as a retrieval authority

* Good, because retrieval metadata could be tuned without parsing Markdown.
* Bad, because it creates a second source of truth and invites lifecycle,
  enforcement, and rationale drift.
* Bad, because generated index checks and human ADR review would no longer prove
  what agents consume.

### Embeddings or a hosted/vector database

* Good, because semantic similarity can discover relationships that lexical
  matching misses.
* Bad, because credentials, availability, indexing lifecycle, nondeterminism,
  cost, privacy, and opaque ranking violate the default local governance
  posture.
* Bad, because structured aliases and project probes should be evaluated before
  adding that complexity.

## Open Questions

- [x] Confirm whether the richer graph contract increments
  `schema_version` from 1 to 2 rather than extending schema v1 additively.
  **Human decision, 2026-07-23:** generate schema v2 by default, retain v1 read
  compatibility for one minor-release window, preserve existing result fields,
  and do not extend schema v1 in place.
- [x] Confirm the authoring contract: flat `topics`, `aliases`, `components`,
  `symbols`, and `context_scope` metadata plus an optional
  `## Decision Contract`.
  **Human decision, 2026-07-23:** approve the proposed flat retrieval fields,
  `global` or `selective` context scope, and optional Decision Contract.
  Continue deriving path applicability exclusively from Enforcement
  `path_glob` rules.
- [x] Confirm the default authority policy: Accepted primary, Proposed
  advisory, and historical statuses opt-in with successor redirection.
  **Human decision, 2026-07-23:** approve Accepted as governing, Proposed as
  clearly labelled non-governing advisory context, Superseded as excluded with
  successor redirection, and Rejected or Deprecated as explicit-history only.
- [x] Confirm the fallback policy: visible Markdown fallback for missing,
  invalid, unsupported, or stale graphs plus strict index mode for CI.
  **Human decision, 2026-07-23:** approve a visible Markdown fallback for
  normal queries, bounded fail-open behavior for hooks, and no silent fallback
  in CI, diagnostics, or explicit strict-index mode.
- [x] Confirm the ranking policy: field-aware positive evidence, no Accepted
  recency boost, and relationships used only for bounded expansion.
  **Human decision, 2026-07-23:** approve positive field evidence only; exact
  path, symbol, and component matches before topic, alias, title, Decision
  Contract, and decision summary; no lifecycle, recency, or relationship-count
  relevance boost; at most two one-hop supporting ADRs; explained matches; and
  ADR ID as the stable final tie-breaker.
- [x] Confirm the compatibility window and release posture for schema-v1
  indexes, legacy weights, result fields, and client payloads.
  **Human decision, 2026-07-23:** ship schema v2 as the default, retain the v1
  reader for one minor-release window, preserve existing result fields during
  that window, and treat legacy weights and client payloads as compatibility
  inputs rather than extending schema v1.
- [x] Establish measured top-k, latency, hook, and graph-size acceptance
  thresholds from the retrieval probe baseline.
  **Human decision, 2026-07-23:** approve top-1 at least 90%, top-3 at 100%,
  zero historical and no-match leakage, 30-sample query p95 at or below 250 ms
  through 200 ADRs and 500 ms through 1,000 ADRs, hook p95 at or below 250 ms
  with a 500 ms semantic hard timeout, graph size at or below 2 KiB per ADR
  plus 16 KiB and 25% of source Markdown, and zero numbered-Markdown opens for
  healthy normal queries.

## Related Decisions

* **ADR-004 — Layered ADR Context Injection for Agent Work:** preserves the
  three fail-open context tiers and fail-closed enforcement floor while
  replacing divergent retrieval implementations with one outcome contract.
* **ADR-005 — Use Selectable ADR Body Profiles with MADR as the Default:**
  requires the retrieval contract to consume semantic roles rather than
  profile-specific headings.
* **ADR-007 — JSON ADR Graph Index for Agent Retrieval:** provides the generated
  graph foundation and Markdown-authority rule that this decision extends into
  the runtime query path.
* **ADR-009 — Bound Heuristic Gates to Findings an Author Can Act On:** requires
  retrieval health findings and probe failures to remain bounded and
  actionable.
* **ADR-010 — Certify Three Native CLI Clients Through One Outcome Contract:**
  requires consistent outcomes across Claude, Codex, and Copilot with explicit
  degradations.
* **ADR-011 — Adopt Deterministic Readiness and Human-Gated Grilling Across the
  ADR Lifecycle:** keeps this Proposed record resumable and reserves acceptance
  for explicit human confirmation.

## References

* `TASK-52` and child tasks `TASK-52.1` through `TASK-52.7`
* `TASK-30` — generated JSON graph foundation
* `bin/adr-context:322-368` — current Markdown-first query loop
* `bin/adr_catalog.py:170-338` — shared semantic record and graph construction
* `schemas/adr-index.schema.json:1-204` — current schema-version-1 graph
  contract
* `hooks/adr_hook_core.py:164-189` — current generated-index reader
* `hooks/adr_hook_core.py:234-306` — current hook-specific ranking and rendering
* `bin/adr-mcp:295-316` — MCP delegation to `adr-context`
* `tests/test_adr_context.py:451-488` — current scoring-only performance test
* Local baseline command, 2026-07-23:
  `python bin/adr-context --format json --limit 5 "<query>"`
* Representative corpus:
  `tests/testsets/otgw-firmware/adrs`

## Enforcement

The binding gate is `index-first-retrieval`. TASK-52 must add that literal
verification anchor to shipped non-document source and certify the behavior
described under Confirmation before acceptance. Declarative diff rules are
deferred until the implementation surface exists; empty rules do not weaken the
named gate or the human acceptance requirement.

```json
{
  "forbid_pattern": [],
  "forbid_import": [],
  "require_pattern": [],
  "llm_judge": false,
  "llm_judge_reason": "no code surface: this decision governs process or documentation, so there is no diff for a model to judge it against"
}
```
