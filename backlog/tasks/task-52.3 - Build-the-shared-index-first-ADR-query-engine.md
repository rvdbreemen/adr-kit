---
id: TASK-52.3
title: Build the shared index-first ADR query engine
status: Done
assignee:
  - Codex
created_date: '2026-07-23 17:44'
updated_date: '2026-07-23 18:53'
labels:
  - adr
  - query-engine
  - agent-retrieval
  - performance
milestone: Index-first ADR retrieval
dependencies:
  - TASK-52.2
references:
  - TASK-52
  - bin/adr-context
  - hooks/adr_hook_core.py
documentation:
  - docs/adr/ADR-004-layered-adr-context-injection.md
  - docs/adr/ADR-007-json-adr-graph-index-for-agent-retrieval.md
modified_files:
  - bin/adr_query.py
  - bin/adr-context
  - codex/bin/adr_query.py
  - codex/bin/adr-context
  - copilot/bin/adr_query.py
  - copilot/bin/adr-context
  - tests/test_adr_context.py
  - tests/test_adr_query.py
parent_task_id: TASK-52
priority: high
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Provide one deterministic query component that loads the generated graph, applies lifecycle-aware fielded retrieval, expands declared relationships in a bounded way, explains every match, and uses the Markdown parser only as an explicit compatibility fallback.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A healthy supported ADR-INDEX.json is queried without opening every Markdown ADR during ranking.
- [x] #2 Path, symbol, component, topic, alias, title, and decision-contract evidence produce deterministic explainable matches with stable tie-breaking.
- [x] #3 Accepted decisions are governing, Proposed decisions are advisory, and Superseded, Rejected, and Deprecated decisions are historical and excluded by default.
- [x] #4 Recency and raw relationship count no longer act as primary relevance signals; declared relationships are added only as bounded supporting context.
- [x] #5 Missing, corrupt, unsupported, or stale indexes follow the approved warning, fallback, and strict-index policies without silent misinterpretation.
- [x] #6 End-to-end performance and retrieval-probe budgets pass on small and representative large ADR sets.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Introduce a stdlib shared query module with schema-v2 and one-window schema-v1 readers. 2. Load a healthy generated graph first and fall back visibly to the existing Markdown loader only for missing, stale, invalid, or unsupported indexes; add strict-index failure. 3. Apply approved field-priority ranking, authority separation, stable ADR-ID ties, explained matches, historical opt-in, successor redirection, and at-most-two one-hop supporting records. 4. Adapt `adr-context` without breaking existing result fields and add the literal `index-first-retrieval` verification anchor to the real gate path. 5. Add selectivity, lifecycle, fallback, probe, size, and 30-sample performance tests; finalize after TASK-52.2.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Detailed plan recorded before TASK-52.3 implementation. This task remains To Do until TASK-52.2 is complete.

TASK-52.2 completed with schema-v2 graph metadata and synchronized generated payloads. TASK-52.3 now starts on the previously approved plan.

Implemented the shared stdlib-only index-first query engine. Healthy schema-v2 graphs are ranked without opening numbered Markdown ADRs; schema-v1 is normalized for one compatibility window. The engine separates authority from relevance, explains positive field evidence, uses numeric ADR-ID tie-breaking, excludes historical states by default, redirects Superseded decisions, and adds at most two declared one-hop supporting ADRs.

Added visible compatibility fallback for missing, stale, invalid, or unsupported indexes and `--strict-index` fail-closed behavior. `bin/adr_query.py` now contains the executable `index-first-retrieval` gate anchor required by ADR-014. Generated Codex and Copilot adapters are synchronized.

Verification: 83 query/integration tests passed with 2 opt-in performance tests skipped in the normal slice; the explicit 30-sample performance run passed at p95 238.0 ms for 200 ADRs and 384.1 ms for 1,000 ADRs. Five representative 169-record OTGW probes achieved 5/5 top-1 and top-3 with zero historical leakage. A loaded combined performance run showed four timing-sensitive failures, but each exact failure passed in an isolated rerun (4 passed), so no deterministic functional regression was found. Adapter drift check, py_compile, strict ADR-014 lint, adr-doctor required checks, and git diff whitespace validation pass.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented ADR Kit's shared index-first selective-context query engine. The new stdlib module reads generated graph schema v2 directly, preserves one-window schema-v1 compatibility, ranks only positive retrieval evidence, labels lifecycle authority independently, explains matches, redirects superseded decisions, and bounds related context. `adr-context` now exposes strict-index, history, and fielded-query controls while preserving existing result fields and using visible Markdown fallback only for unhealthy indexes. Added synchronized Codex/Copilot artifacts and broad lifecycle, fallback, selectivity, OTGW-corpus, and performance coverage. Verification passed: 83 query/integration tests, explicit 30-sample p95 budgets (238.0 ms/200 ADRs; 384.1 ms/1,000 ADRs), 5/5 representative OTGW top-1/top-3 probes with zero historical leakage, clean generated-adapter check, strict ADR lint, and healthy required doctor checks.
<!-- SECTION:FINAL_SUMMARY:END -->
