---
id: TASK-52.2
title: Extend the generated ADR graph with selective retrieval metadata
status: Done
assignee:
  - Codex
created_date: '2026-07-23 17:44'
updated_date: '2026-07-23 18:44'
labels:
  - adr
  - index
  - schema
  - metadata
milestone: Index-first ADR retrieval
dependencies:
  - TASK-52.1
references:
  - TASK-52
  - schemas/adr-index.schema.json
  - bin/adr_catalog.py
  - bin/adr-index
documentation:
  - docs/adr/ADR-005-selectable-agent-friendly-adr-formats.md
  - docs/adr/ADR-007-json-adr-graph-index-for-agent-retrieval.md
modified_files:
  - bin/adr_format.py
  - bin/adr_schema.py
  - bin/adr_catalog.py
  - schemas/adr-frontmatter.schema.json
  - schemas/adr-index.schema.json
  - templates/adr-template.md
  - templates/adr-template.madr.md
  - templates/adr-template.nygard.md
  - templates/adr-template.canonical.md
  - >-
    docs/adr/ADR-014-use-the-generated-adr-graph-as-the-selective-context-query-engine.md
  - docs/adr/ADR-INDEX.json
  - codex/
  - copilot/
  - tests/test_adr_index.py
  - tests/test_selectable_formats.py
  - tests/test_otgw_corpus.py
parent_task_id: TASK-52
priority: high
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Evolve the generated graph contract so it contains bounded, format-neutral metadata that supports precise task, path, component, symbol, and baseline-context selection without becoming a second source of truth. Existing ADRs remain valid and all metadata is derived deterministically from Markdown.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The graph schema has an explicit versioned contract for topics, aliases, components, symbols, context scope, and bounded decision constraints.
- [x] #2 MADR, Nygard, canonical, and legacy records produce the same semantic retrieval shape from their authoritative Markdown sources.
- [x] #3 Existing lifecycle, enforcement scope, relationship, and compatibility fields retain their meanings and generated ordering remains deterministic and timestamp-free.
- [x] #4 Legacy ADRs without retrieval metadata remain valid while new templates make selective metadata and a concise Decision Contract discoverable.
- [x] #5 Schema, profile, round-trip, malformed-input, determinism, index-size, and stale-artifact tests pass.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Inspect the existing semantic record, frontmatter, format-profile, graph generator, and JSON schemas. 2. Extend the authoritative Markdown contract with optional flat `topics`, `aliases`, `components`, `symbols`, and scalar `context_scope`; parse an optional bounded Decision Contract across supported profiles. 3. Generate deterministic schema-v2 graph nodes while preserving lifecycle, scope, relationship, result-field, and schema-v1 reader compatibility. 4. Update all three templates and JSON schemas without invalidating legacy records. 5. Add schema/profile/malformed/determinism/size/staleness regression coverage, regenerate artifacts, and finalize TASK-52.2 before TASK-52.3.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan approved by the user through the final grill implementation authorization on 2026-07-23. TASK-52.2 is starting before TASK-52.1 closes solely because the binding ADR requires the real TASK-52.2/.3 named gate before acceptance; the ADR remains Proposed.

Implemented graph schema v2 with required deterministic `topics`, `aliases`, `components`, `symbols`, `context_scope`, and bounded structured `decision_contract` fields on every node. Flat optional frontmatter remains backward-compatible; absent fields project empty lists and `selective`. Retrieval lists are limited to 32 unique 120-character values; Decision Contract roles are limited to 20 unique 240-character values.

Added the optional Decision Contract semantic role uniformly across MADR, Nygard, and canonical formats and published it in all templates. Existing lifecycle metadata, Enforcement `path_globs`, relationship edges, context JSON result fields, ordering, and timestamp-free generation are unchanged.

Verification: 63 focused index/profile/OTGW/documentation tests pass; generated client adapters report zero drift. The regenerated repository graph is schema v2 with 14 ADRs, 21,082 bytes, and 14.58% of its Markdown corpus, satisfying the approved size gates. `git diff --check` reports no whitespace errors.

Post-finalization live query inspection found that wrapped Decision Contract list items retained only their first physical Markdown line. Reopened within the existing bounded-contract acceptance scope to join continuation lines before applying the 240-character bound.

Corrected Decision Contract projection to join indented continuation lines before de-duplication and the 240-character bound. Added a wrapped-item regression test, regenerated repository and client graphs/code, and reran the 63-test schema/profile/corpus/documentation slice successfully.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Introduced the versioned schema-v2 selective-retrieval projection while keeping Markdown authoritative and legacy ADRs valid. Optional flat frontmatter now supports topics, aliases, components, symbols, and context scope; all graph nodes expose a stable retrieval shape plus a bounded structured Decision Contract. MADR, Nygard, canonical, and generated Codex/Copilot payloads are synchronized. Existing lifecycle, enforcement, relationship, compatibility-result, ordering, and freshness semantics remain intact. Verification passed 63 focused tests, a clean client-generation drift check, and the graph-size budget (21,082 bytes, 14.58% of source Markdown).

Follow-up hardening preserves complete wrapped Markdown list semantics in bounded Decision Contract items; the regenerated payloads and 63 focused tests remain green.
<!-- SECTION:FINAL_SUMMARY:END -->
