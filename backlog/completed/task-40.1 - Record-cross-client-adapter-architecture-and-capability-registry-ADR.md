---
id: TASK-40.1
title: Record three-client native architecture and certification ADR
status: Done
assignee:
  - Codex
created_date: '2026-07-19 17:50'
updated_date: '2026-07-19 19:27'
labels:
  - architecture
  - adr
  - capabilities
dependencies: []
documentation:
  - docs/research/cross-client-plugin-hooks-report.md
  - docs/adr/ADR-004-layered-adr-context-injection.md
  - docs/adr/ADR-006-prepare-platform-local-marketplaces-for-native-installs.md
  - docs/adr/ADR-007-json-adr-graph-index-for-agent-retrieval.md
  - >-
    docs/adr/ADR-008-resolve-the-enforcement-engine-from-a-version-ranked-root-set-including-the-checkout.md
modified_files:
  - >-
    docs/adr/ADR-010-certify-three-native-cli-clients-through-one-outcome-contract.md
  - docs/adr/ADR-INDEX.md
  - docs/adr/ADR-INDEX.json
  - docs/adr/README.md
  - schemas/client-capabilities.schema.json
  - tests/test_client_capabilities_schema.py
parent_task_id: TASK-40
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create a Proposed ADR before shared implementation. Define exactly Claude Code CLI, Codex CLI, and GitHub Copilot CLI as first-class scope; equal user outcomes with documented native degradations; minimal capability/certification metadata; canonical versus generated ownership; schema-validated hand-authored manifests; recorded client exceptions; global/project settings; update and repair authority; Windows-first certification; and the performance measurement contract. Reconcile automatic configured local-model judgment with ADR-001 while paid/cloud use remains opt-in. Wider support belongs to TASK-43 and is not decided here.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A new Proposed ADR follows the configured MADR profile and passes all ADR Kit quality gates without changing an Accepted ADR in place.
- [x] #2 The decision fixes active scope at Claude Code CLI, Codex CLI, and Copilot CLI and assigns every additional client or generic-support decision to future TASK-43.
- [x] #3 The outcome contract defines workflow discovery, task context, edit governance/backstop, MCP, pre-commit, lifecycle management, and doctor trust while allowing documented event-level differences.
- [x] #4 Canonical/generated/hand-authored ownership is explicit for skills, prompts, hooks, guides, MCP intent, manifests, settings, capabilities, and certification evidence.
- [x] #5 The minimal capability schema records only the three clients' IDs/surfaces, OS scope, required outcomes, event mappings, degradations, install/update/remove probes, settings, and certification references.
- [x] #6 The decision records Windows native release certification, macOS/Linux best-effort status, and an all-three-client release block.
- [x] #7 The decision specifies verified stable auto-update and rollback, confirmation before breaking migration, safe doctor repair versus --check/--fix authority, and user-owned state boundaries.
- [x] #8 The decision reconciles local-model judgment default-on behavior with ADR-001 and keeps paid/cloud judgment opt-in.
- [x] #9 The decision records latency budgets and requires a defined cold/warm/reference-corpus benchmark method before enforcement.
- [x] #10 ADR index artifacts regenerate deterministically and strict lint, related-link, and quality output are recorded.
- [x] #11 The ADR records engineering budgets: public/build entrypoints target <=300 physical lines, support modules target <=400, TASK-40 adds at most four directly invoked entrypoints, and exceptions require recorded rationale, ownership, and tests.
- [x] #12 The ADR records the zero-runtime-dependency baseline and requires a separate Proposed ADR before adding a runtime dependency, including development/runtime separation, license/security/update policy, exact-pin rationale, and removal path.
- [x] #13 The ADR defines release-candidate consolidation, at most one non-emergency stable release per calendar day, emergency override evidence, and ADR supersession before reversing a shipped policy/default.
- [x] #14 The ADR prohibits guessed local-model tags and defines explicit/unambiguous selection, degraded unavailable/ambiguous state, fast cached/config checks, and bounded deep live probes.
- [x] #15 The ADR defines deterministic-generation performance methodology and initial Windows-native targets: clean full three-client generation p50 <=1 s and p95 <=2 s with a 5 s hard timeout; warm unchanged validation/generation p50 <=150 ms and p95 <=500 ms with a 1 s hard timeout; plus a maximum 20% p95 regression from the approved baseline unless an explicit reviewed exception is linked. macOS/Linux results are recorded best-effort.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Size M. Review ADR-001/004/006/007/008/009 and the narrowed plan. Write one Proposed MADR decision focused on the three native CLI clients and shared ownership boundaries; keep the capability schema minimal. Validate all ADR gates and indexes. Stop if an Accepted decision must change: use a superseding Proposed ADR relationship. Do not design or commit generic/additional-client behavior from TASK-43.

Include deterministic-generation performance in the policy decision: fixed fixture/artifact set, Windows reference machine class, cold/warm cache definition, process startup inclusion, sample count, bytes/files read and written, and a reviewed procedure for changing budgets.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started implementation. The installed adr-kit MCP context tool failed because its launcher still targets removed cache version 0.34.0; using the current repository's deterministic adr-context engine as the safe equivalent. This is also preserved as evidence for the later Codex stale-launcher certification fixture.

Implemented ADR-010 as a Proposed MADR decision and added the versioned minimal three-client capability schema plus structural tests. Evidence: `python bin/adr-quality --format json ...ADR-010...` grade A with completeness/evidence/clarity/consistency all 1.0 (floating representation for evidence); strict lint passes all 10 repository ADRs with zero advisories; `adr-related ADR-010` resolves seven outbound decisions with no dangling links; `adr-index --check docs/adr` reports no drift; focused schema/index/packaging suite reports 23 passed, 1 skipped; whitespace and diff checks pass.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added Proposed ADR-010, which fixes current support at Claude Code CLI, Codex CLI, and GitHub Copilot CLI under one outcome contract with honest native degradations, Windows-first all-three certification, lifecycle and repair boundaries, explicit local-model policy, hook and generator latency budgets, dependency and release discipline, and artifact ownership. Added `schemas/client-capabilities.schema.json`, which can represent exactly those three surfaces and requires their outcomes, operating-system scope, event mappings, degradations, lifecycle probes, settings keys, and certification references. Added structural schema tests and regenerated all ADR indexes. All four ADR quality gates score 1.0; strict lint, relationship, index, packaging, schema, and whitespace verification pass.
<!-- SECTION:FINAL_SUMMARY:END -->
