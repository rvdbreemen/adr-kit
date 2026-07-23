---
id: TASK-52.7
title: Deliver migration guidance and release certification for index-first retrieval
status: Done
assignee:
  - Codex
created_date: '2026-07-23 17:44'
updated_date: '2026-07-23 19:49'
labels:
  - adr
  - migration
  - documentation
  - release
milestone: Index-first ADR retrieval
dependencies:
  - TASK-52.4
  - TASK-52.5
  - TASK-52.6
references:
  - TASK-52
  - scripts/sync-agent-plugins.py
  - scripts/build-client-adapters.py
documentation:
  - README.md
  - INSTALL-AGENT.md
  - ROADMAP.md
  - CHANGELOG.md
  - docs/client-support.md
modified_files:
  - bin/adr-migrate
  - docs/selective-context.md
  - README.md
  - INSTALL-AGENT.md
  - ROADMAP.md
  - CHANGELOG.md
  - docs/client-support.md
  - >-
    docs/adr/ADR-010-certify-three-native-cli-clients-through-one-outcome-contract.md
  - >-
    docs/adr/ADR-014-use-the-generated-adr-graph-as-the-selective-context-query-engine.md
  - skills/adr/SKILL.md
  - skills/context/SKILL.md
  - skills/grill/SKILL.md
  - skills/migrate/SKILL.md
  - clients/workflows.json
  - scripts/client_certification.py
  - tests/test_adr_retrieval_health.py
parent_task_id: TASK-52
priority: high
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Provide a safe compatibility and adoption path for existing ADR sets and certify the completed index-first retrieval capability across schemas, generated artifacts, client packages, documentation, performance, and full regression coverage.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A dry-run migration path suggests selective metadata and Decision Contract content without silently changing human decisions.
- [x] #2 Existing schema-v1 indexes, legacy context weights, and projects without retrieval metadata follow the approved compatibility and deprecation policy.
- [x] #3 Documentation explains authoring, index generation, querying, authority labels, fallback behavior, probes, migration, and client-specific context behavior.
- [x] #4 Schema validation, index freshness, strict ADR lint, doctor, generated payload synchronization, native-client certification, focused retrieval tests, performance gates, and the full supported suite pass.
- [x] #5 Release notes identify the schema and behavior changes, upgrade steps, compatibility window, risks, and rollback path.
- [x] #6 The epic is closed only after every child task has verified evidence and the accepted ADR matches the shipped behavior.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add a deterministic dry-run metadata/Decision Contract migration suggestion path that never rewrites human decisions without an explicit separate apply operation. 2. Document schema-v2 authoring, index generation, query controls, authority/fallback behavior, probes, strict completeness, client-specific hooks, schema-v1/legacy-weight compatibility, deprecation timing, upgrade, risk, and rollback. 3. Synchronize skills, templates, schemas, client payloads, roadmap/changelog/release notes, and release evidence. 4. Run migration and documentation tests, schema/index/strict-lint/doctor checks, generated-adapter and native-client certification, focused retrieval/performance gates, then the full supported test suite. 5. Reconcile ADR-014 against shipped behavior, finalize TASK-52.7, verify all eight children Done, check every epic acceptance criterion, and close TASK-52 only on green evidence.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan pre-recorded under the approved epic drain. TASK-52.7 is the final certification task and starts only after TASK-52.4, TASK-52.5, and TASK-52.6 are Done.

TASK-52.4, TASK-52.5, and TASK-52.6 are Done. Final migration, documentation, lifecycle evidence reconciliation, and full release certification now begin.

Completed the dry-run-only retrieval suggestion workflow, schema-v1 and legacy-weight compatibility/deprecation guidance, selective-context authoring/query/probe/rollback documentation, human-reviewed grilling metadata contract, generated three-client workflow/support updates, and ADR evidence reconciliation. Final evidence on 2026-07-23: retrieval performance p95 204.4 ms at 200 ADRs and 297.9 ms at 1,000 ADRs; focused grill/docs gates 30 passed; broader retrieval/client/docs slice 154 passed plus expected skips; full supported suite 867 passed, 10 skipped in 369.82 s. Strict lint: 14/14 PASS, 0 advisory/fail; probes: 2/2 pass; index and generated adapters current; doctor has 0 ADR findings and detects healthy Claude 2.1.218, Codex 0.145.0, and Copilot 1.0.71 native packages. Release version registry and git diff checks pass. The separate clean-commit native release-candidate workflow remains an optional publication gate and was not fabricated from this dirty implementation tree.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Delivered the final adoption and certification layer for index-first ADR retrieval. Existing projects get a visible schema-v1/Markdown fallback and one-minor-release legacy scoring compatibility; new metadata is suggested only through an explicit dry-run and requires human approval. Documentation now covers authoring, Decision Contracts, query controls, authority, lifecycle behavior, probes, migration, risks, rollback, and client degradations. Canonical skills and generated Claude/Codex/Copilot payloads are synchronized, ADR-010 was lifecycle-revalidated after its evidence changed, ADR-014 now points to shipped verification anchors, and all focused, performance, health, packaging, and full regression gates pass.
<!-- SECTION:FINAL_SUMMARY:END -->
