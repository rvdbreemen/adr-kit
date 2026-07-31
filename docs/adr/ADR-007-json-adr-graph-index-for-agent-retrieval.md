---
id: "ADR-007"
title: "JSON ADR Graph Index for Agent Retrieval"
status: "Accepted"
date: "2026-07-23"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-007 JSON ADR Graph Index for Agent Retrieval

## Status

Accepted, 2026-07-23.

## Status History

```yaml
status_history:
  - date: 2026-07-18
    status: Proposed
    changed_by: Codex
    reason: Initial proposal
    changed_via: adr-kit
  - date: 2026-07-18
    status: Accepted
    changed_by: Robert van den Breemen
    reason: Human approval for the v0.34.0 release; ADR-INDEX.json ships as a generated artifact
    changed_via: adr-kit lifecycle
  - date: 2026-07-23
    status: Accepted
    changed_by: Codex for Robert
    reason: "Amended by ADR-014: advance the generated graph enforcement gate from schema version 1 to schema version 2 while retaining ADR-007's graph foundation and Markdown-authority rules"
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

ADR Kit already exposes three complementary local views:

* `bin/adr-index --format json` emits a flat list containing an ADR id, status,
  enforcement scope, decision summary, and source path;
* `bin/adr-context` independently parses ADRs and ranks them using keywords,
  inferred domains, declared relationships, lifecycle status, and recency; and
* `bin/adr-related` independently builds inbound and outbound relationship
  views, including dangling references.

An agent must currently call multiple command-line interface (CLI) tools,
reconcile slightly different parsers, and then open files to recover basic
metadata such as format, title, binding state, and evidence pointers. The flat
JavaScript Object Notation (JSON) output also omits typed relationships, so it
cannot serve as an efficiently traversable decision graph.

ADR-004 requires a deterministic, bounded index for session and task context and
pins status and enforcement scope as shared canonical fields. ADR-005 requires
all engines to consume semantic roles rather than format-specific headings.
This decision must extend both without creating another hand-maintained source
of truth. Markdown ADR files remain authoritative.

## Decision Drivers

* Agents need a compact local catalog before spending tokens opening ADR prose.
* Retrieval results need enough metadata and source paths to explain why an ADR
  is relevant.
* Declared relationships and dangling targets must be traversable and lintable.
* Markdown Any Decision Records (MADR), Nygard, and canonical body profiles
  must produce the same semantic record shape.
* Generated artifacts must be deterministic, diff-friendly, stdlib-only, and
  usable on Windows, macOS, and Linux.
* Existing `adr-index`, `adr-context`, `adr-related`, Markdown index, MCP, and
  automation consumers need a compatible upgrade path.
* The index must not become a second authority for decision or enforcement text.

## Considered Options

* Generate a versioned JSON node-and-edge graph from the same semantic records
  used by the Markdown index.
* Enrich only the existing flat JSON list and leave relationships in
  `adr-related`.
* Use a database, embeddings, or a hosted vector service as the primary index.
* Keep the existing separate views unchanged.

## Decision Outcome

Chosen option: **generate a versioned JSON node-and-edge graph from one shared,
format-aware semantic record loader**, because this provides deterministic
agent discovery and relationship traversal without adding a service or a new
authoritative data store.

1. Markdown ADR files remain the source of truth. `docs/adr/ADR-INDEX.json` and
   `docs/adr/ADR-INDEX.md` are generated views and must never be hand-edited.
2. The graph document has an explicit `schema_version`, a stable `$schema`
   pointer, a sorted `adrs` array, and a sorted `relationships` array. It has no
   generation timestamp.
3. Each ADR node contains normalized identity, title, relative source path,
   detected or declared format, reconciled lifecycle status and date, a bounded
   plain-text decision summary, enforcement `path_globs`, and the invariant
   frontmatter fields `binding`, `gate`, `documents_shipped`, `verified_in`,
   `supersedes`, and `superseded_by`.
4. Each declared relationship is a directed edge with `source`, `target`,
   `type`, and `resolved`. Supported types are `related`, `supersedes`,
   `superseded-by`, and `amended-by`. Plain prose mentions are not graph edges
   because they are ambiguous and create noisy coupling.
5. `adr-index` generates Markdown and JSON from the same records. Decision
   summaries remain bounded to 120 characters. Its check mode validates both
   generated context artifacts as well as the existing README index.
6. `adr-context` uses the shared semantic records and enriches each ranked
   result with path, status, format, decision summary, scope, and declared
   related ids. Existing `adr_id`, `title`, `score`, and `signals` fields remain
   compatible. Relevance scores stay query-specific and are not persisted in
   the graph.
7. `adr-related` uses the same relationship extraction rules. Inbound links are
   derived by reversing the normalized edge set instead of being stored as
   duplicate source metadata.
8. Agents load or query the JSON graph to shortlist decisions, then open the
   referenced Markdown ADRs before applying constraints or citing rationale.
9. `schemas/adr-index.schema.json` versions and validates the contract. The
   schema and generator are copied into every shipped agent payload.

### Confirmation

Confirm the decision with:

* schema validation fixtures for valid and invalid graph documents;
* deterministic generation and stale/missing artifact checks;
* equivalent node output for MADR, Nygard, and canonical fixtures;
* explicit, reciprocal, and dangling relationship fixtures;
* backward-compatible and enriched `adr-context` result tests;
* synchronization checks for the root, Codex, and Copilot payloads;
* strict ADR lint, ADR doctor, focused regression tests, and the full supported
  test suite in continuous integration (CI).

## Consequences

### Positive

* Agents can filter, rank, and traverse ADRs with one compact local artifact.
* Retrieval explanations include actionable paths and lifecycle metadata.
* Index, context, and relationship tools no longer drift through independent
  parsing behavior.
* Dangling links become visible in a repository-wide graph.
* The solution remains file-based, key-free, portable, and inspectable.

### Negative

* The generated JSON adds a tracked artifact that can become stale. Check mode,
  doctor, CI, and lifecycle regeneration mitigate this.
* Richer output increases index size. Decision text remains a bounded summary,
  relationships are normalized once, and full prose stays out of the graph.
* Adding fields to `adr-context` may affect strict consumers. Existing fields
  and meanings are retained; new fields are additive.
* Heuristic relationship extraction can misclassify prose. Only declared
  relationship sections and lifecycle claims become graph edges; plain mentions
  remain retrieval signals only.
* A schema change requires an explicit `schema_version` increment and
  compatibility review.

## Pros and Cons of the Options

### Versioned generated graph

* Good, because agents receive a compact catalog and normalized relationship
  graph without a runtime dependency.
* Good, because one semantic loader can serve Markdown, JSON, retrieval, and
  relationship consumers.
* Good, because deterministic tracked output is reviewable in normal diffs.
* Bad, because another generated artifact must be kept synchronized.

### Enrich only the flat JSON list

* Good, because it is the smallest CLI change.
* Bad, because graph traversal and dangling-link discovery remain separate.
* Bad, because independent parsers continue to drift.

### Database, embeddings, or hosted vector service

* Good, because semantic search can improve on lexical retrieval for large ADR
  collections.
* Bad, because availability, credentials, platform setup, opaque ranking, and
  nondeterminism conflict with ADR Kit's local enforcement floor.
* Bad, because a service would be excessive for the repository-scale catalog.
  Embeddings may remain an optional consumer of the deterministic JSON index.

### Keep the existing views unchanged

* Good, because there is no migration cost.
* Bad, because agents keep reconciling incomplete and independently parsed
  outputs.
* Bad, because the existing JSON cannot represent the ADR relationship graph.

## Related Decisions

* **ADR-004**: this decision extends the layered context model with a richer
  machine-readable task-tier view while retaining its bounded Markdown
  session-tier index.
* **ADR-005**: the shared loader consumes semantic roles across the selectable
  MADR, Nygard, and canonical profiles.
* **ADR-002**: doctor and guardian checks remain local and fail-open outside the
  existing enforcement floor.

## References

* `bin/adr-index:158` - current flat context-record loader
* `bin/adr-context:160` - current independent retrieval metadata parser
* `bin/adr-related:145` - current independent relationship parser
* `bin/adr_format.py`
* `schemas/adr-frontmatter.schema.json`
* `docs/adr/ADR-004-layered-adr-context-injection.md`
* `docs/adr/ADR-005-selectable-agent-friendly-adr-formats.md`
* [JSON Schema Core 2020-12](https://json-schema.org/draft/2020-12/json-schema-core)

## Enforcement

```json
{
  "forbid_pattern": [],
  "forbid_import": [],
  "require_pattern": [
    {
      "pattern": "\"schema_version\"\\s*:\\s*2",
      "path_glob": "docs/adr/ADR-INDEX.json",
      "message": "The generated ADR graph must declare schema_version 2 per ADR-014."
    },
    {
      "pattern": "\"relationships\"\\s*:",
      "path_glob": "docs/adr/ADR-INDEX.json",
      "message": "The generated ADR index must expose the normalized relationship graph."
    }
  ],
  "llm_judge": false
}
```
