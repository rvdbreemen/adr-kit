---
id: TASK-52.6
title: Add retrieval probes and ADR selective-context health checks
status: Done
assignee:
  - Codex
created_date: '2026-07-23 17:44'
updated_date: '2026-07-23 19:24'
labels:
  - adr
  - quality
  - doctor
  - guardian
  - retrieval-probes
milestone: Index-first ADR retrieval
dependencies:
  - TASK-52.3
  - TASK-52.4
references:
  - TASK-52
  - bin/adr-doctor
  - bin/adr-status
  - bin/adr-guardian
documentation:
  - docs/adr/ADR-002-adr-guardian-session-start-staleness-detector.md
  - docs/adr/ADR-009-bound-heuristic-gates-to-findings-an-author-can-act-on.md
modified_files:
  - bin/adr_retrieval_health.py
  - bin/adr-context
  - bin/adr-lint
  - bin/adr_doctor_core.py
  - bin/adr-status
  - bin/adr-guardian
  - schemas/adr-context-probes.schema.json
  - schemas/adr-kit-config.schema.json
  - docs/adr/.adr-kit.json
  - docs/adr/adr-context-probes.json
  - tests/test_adr_retrieval_health.py
  - codex/bin/adr_retrieval_health.py
  - codex/bin/adr-context
  - codex/bin/adr-lint
  - codex/bin/adr_doctor_core.py
  - codex/bin/adr-status
  - codex/bin/adr-guardian
  - codex/schemas/adr-context-probes.schema.json
  - codex/schemas/adr-kit-config.schema.json
  - copilot/bin/adr_retrieval_health.py
  - copilot/bin/adr-context
  - copilot/bin/adr-lint
  - copilot/bin/adr_doctor_core.py
  - copilot/bin/adr-status
  - copilot/bin/adr-guardian
  - copilot/schemas/adr-context-probes.schema.json
  - copilot/schemas/adr-kit-config.schema.json
parent_task_id: TASK-52
priority: high
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make selective-context quality measurable at project level through deterministic expected-result probes, advisory metadata checks, and health reporting that helps teams enrich under-specified binding ADRs without forcing bulk migration.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Projects can define deterministic probes with expected top-k inclusions, exclusions, query paths, components, and symbols.
- [x] #2 Probe failures explain the query, expected decision, actual ranking, authority, and positive match evidence.
- [x] #3 Lint and doctor identify Accepted binding ADRs with insufficient selective-context metadata using actionable advisory findings by default.
- [x] #4 Guardian and status surfaces report retrieval health without auto-editing ADRs, running a model, or blocking normal sessions.
- [x] #5 Projects can opt into strict retrieval completeness after migration while legacy projects remain valid by default.
- [x] #6 Dogfood and representative large-corpus probes pass with historical decisions excluded from governing results.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Define a bounded project probe schema/config contract for task text, paths/components/symbols, expected top-k inclusions, and exclusions. 2. Build deterministic probe evaluation over the shared query engine with actionable actual-vs-expected evidence and no model/network use. 3. Add default-advisory metadata completeness findings for Accepted binding ADRs plus an explicit opt-in strict completeness mode that leaves legacy projects valid. 4. Surface retrieval health read-only through lint, doctor, status, and guardian without automatic ADR edits or session blocking. 5. Add dogfood and 169-record corpus probes, historical-exclusion checks, schema tests, and focused health/reporting regressions before finalization.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan pre-recorded under the approved epic drain. Implementation starts after TASK-52.4, and integrates with TASK-52.5 outputs where hook health evidence is relevant.

TASK-52.4 and TASK-52.5 are Done. Project-level retrieval probes and health reporting now start against the verified query and hook outcome contracts.

Added schema-v1 project retrieval probes with bounded task text, paths, components, symbols, topics, top-k includes, and exclusions. Evaluation runs directly over the loaded generated graph, never enables historical results, and reports ranks, authority, role, score, and positive field matches for every actual result.

Added Accepted-binding metadata completeness health. Default `advisory` mode does not invalidate legacy projects; `strict` is an explicit project opt-in and `off` is available. Lint emits actionable policy findings, doctor includes retrieval health/advisory counts, status includes retrieval health, and `adr-guardian retrieval-health` is read-only and always fail-open.

The dogfood project now carries two probes, both passing. Five configurable probes over the 169-record OTGW corpus pass 5/5 with no historical leakage. The full focused retrieval/status/doctor/guardian/config slice passed 157 tests with 2 opt-in performance tests skipped; the final health/adapter/package/config slice passed 33 tests and generated adapters have zero drift.

During live doctor verification, the doctor also reported existing Accepted ADR evidence drift for ADR-010 because this task intentionally updates its referenced client-capability test. That lifecycle evidence will be reconciled during TASK-52.7 release certification; retrieval health itself passes and remains independently reported.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Delivered deterministic project-level selective-context probes and health reporting. A new bounded schema and stdlib evaluator verify expected top-k inclusions/exclusions with detailed authority and match evidence. Accepted binding ADR metadata completeness is advisory by default, can be made strict after migration, and is surfaced through lint, doctor, status, and a read-only guardian command. Dogfood and 169-record OTGW probes pass without historical governing leakage, generated client artifacts are synchronized, and focused health/regression suites pass.
<!-- SECTION:FINAL_SUMMARY:END -->
