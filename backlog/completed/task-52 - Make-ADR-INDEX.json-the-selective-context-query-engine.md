---
id: TASK-52
title: Make ADR-INDEX.json the selective-context query engine
status: Done
assignee:
  - '@Codex'
created_date: '2026-07-23 17:43'
updated_date: '2026-07-23 19:49'
labels:
  - adr
  - agent-retrieval
  - index
  - governance
  - epic
milestone: Index-first ADR retrieval
dependencies: []
references:
  - TASK-30
  - bin/adr-context
  - bin/adr-index
  - bin/adr-mcp
  - hooks/adr_hook_core.py
documentation:
  - docs/adr/ADR-004-layered-adr-context-injection.md
  - docs/adr/ADR-005-selectable-agent-friendly-adr-formats.md
  - docs/adr/ADR-007-json-adr-graph-index-for-agent-retrieval.md
  - schemas/adr-index.schema.json
  - >-
    docs/adr/ADR-014-use-the-generated-adr-graph-as-the-selective-context-query-engine.md
modified_files:
  - >-
    docs/adr/ADR-014-use-the-generated-adr-graph-as-the-selective-context-query-engine.md
  - schemas/adr-frontmatter.schema.json
  - schemas/adr-index.schema.json
  - schemas/adr-kit-config.schema.json
  - bin/adr_catalog.py
  - bin/adr_query.py
  - bin/adr-context
  - bin/adr-mcp
  - bin/adr_retrieval_health.py
  - bin/adr-lint
  - bin/adr-status
  - bin/adr-guardian
  - bin/adr_doctor_core.py
  - bin/adr-migrate
  - hooks/adr_hook_core.py
  - hooks/native/adr-hook.rs
  - clients/capabilities.json
  - clients/exceptions.json
  - clients/workflows.json
  - docs/adr/adr-context-probes.json
  - schemas/adr-context-probes.schema.json
  - docs/selective-context.md
  - README.md
  - INSTALL-AGENT.md
  - CHANGELOG.md
  - ROADMAP.md
  - tests/test_adr_query.py
  - tests/test_adr_retrieval_health.py
  - tests/test_adr_context.py
  - tests/test_adr_mcp.py
  - tests/test_hook_protocol.py
priority: high
ordinal: 53500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Turn the existing deterministic ADR graph into ADR Kit's actual runtime retrieval engine so agents receive fast, explainable, bounded, status-aware ADR context without reparsing every Markdown ADR. Markdown ADRs remain authoritative; the JSON graph remains generated, local, deterministic, stdlib-first, and shared across CLI, MCP, hooks, guardian, and review workflows. Preserve the fail-open context layers and fail-closed judge boundary defined by ADR-004 and build on ADR-005 and ADR-007.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A human-approved ADR defines the index-first retrieval contract, authority semantics, compatibility posture, fallback behavior, and rejected alternatives.
- [x] #2 Healthy ADR-INDEX.json data is the primary runtime source for task, prompt, edit, MCP, guardian, and review retrieval without reparsing every Markdown ADR.
- [x] #3 Accepted, Proposed, and historical ADRs are presented with distinct authority and historical ADRs are excluded from governing context by default.
- [x] #4 The generated graph exposes bounded selective-retrieval metadata while Markdown ADR files remain the sole decision authority.
- [x] #5 CLI, MCP, Python hooks, native hooks, Codex, Claude, and Copilot satisfy one deterministic retrieval outcome contract with documented degradations.
- [x] #6 Project-specific retrieval probes, health reporting, migration guidance, performance budgets, and regression coverage demonstrate retrieval quality and compatibility.
- [x] #7 All generated artifacts, client payloads, strict ADR checks, doctor checks, focused tests, and the full supported test suite pass before the epic is Done.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Goal: make generated ADR-INDEX.json the primary runtime query projection for selective agent context while keeping Markdown ADRs authoritative.

Architecture:
1. Record and grill a Proposed ADR extending ADR-004, ADR-005, and ADR-007.
2. Establish retrieval-quality, historical-leakage, index-size, and end-to-end performance baselines.
3. Introduce a versioned retrieval metadata contract: flat authoring fields for topics, aliases, components, symbols, and context scope, plus an optional bounded Decision Contract body section.
4. Generate schema-v2 graph nodes deterministically across MADR, Nygard, canonical, and legacy formats without duplicating lifecycle or Enforcement scope authority.
5. Build one stdlib index loader and deterministic field-aware query engine with lifecycle authority separation, explainable matches, bounded relationship expansion, stable ordering, and explicit stale/missing-index fallback.
6. Integrate the outcome with adr-context and MCP while keeping compatible result fields and adding optional paths, components, symbols, lifecycle filters, and historical intent.
7. Align Python/native session, prompt, pre-edit, post-edit, subagent, and compaction hooks across Claude, Codex, and Copilot capability boundaries.
8. Add project retrieval probes, advisory metadata health checks, doctor/status/guardian reporting, opt-in strict completeness, and dry-run migration suggestions.
9. Update skills, templates, config/schema documentation, install/upgrade guidance, client support matrix, changelog, and release evidence.
10. Certify schema validation, generated index freshness, strict ADR lint, doctor, payload sync, native-client parity, retrieval probes, performance budgets, focused tests, and the full supported suite.

Global constraints:
- Local, deterministic, stdlib-first, key-free default path.
- No hosted service, database, embeddings, or model in query/hook hot paths.
- Context hooks remain fail-open; adr-judge remains the fail-closed enforcement floor.
- Accepted ADRs govern; Proposed ADRs are advisory; historical ADRs are opt-in.
- Healthy index queries must not parse every Markdown ADR.
- Markdown source records must be opened before applying a shortlisted constraint.
- Human grilling and explicit same-session confirmation remain authoritative for ADR acceptance.

Drain authorization received on 2026-07-23: execute all remaining subtasks sequentially without further handoff pauses. Sequence remains TASK-52.4 (CLI/MCP contract), TASK-52.5 (cross-client hooks), TASK-52.6 (probes/health), TASK-52.7 (migration/docs/release certification), then reconcile every epic acceptance criterion and close TASK-52 only after the full supported suite passes.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
User approved the proposed index-first direction on 2026-07-23 and explicitly authorized creating the epic/tasks plus drafting and grilling the ADR. This does not authorize ADR acceptance or feature implementation before the grill reaches an explicit acceptance decision. TASK-30 remains Done as the graph-index foundation; TASK-52 is the follow-on runtime retrieval initiative.

Created ADR-014 as Proposed and populated it from repository facts. Current readiness is needs-human-input with seven Open Questions, no mechanical findings, no blocking implementation link, and strict lint passes with one advisory. Baseline on 2026-07-23: 14 ADRs median 548.7 ms across three CLI samples; 169-record corpus median 2609.6 ms; generated graph 14,553 bytes before the content refresh.

On 2026-07-23 the user explicitly authorized implementing TASK-52.2 and TASK-52.3 to create and verify the real `index-first-retrieval` named gate before final ADR acceptance. Sequence: finish schema-v2 graph metadata and compatibility in TASK-52.2, then build the shared index-first engine and verification anchor in TASK-52.3, then return to TASK-52.1 for explicit final `yes` and lifecycle transition. This resolves the otherwise circular acceptance dependency without weakening the gate.

User explicitly requested draining all TASK-52 subtasks. Existing scope and dependency order are approved; no new tasks or acceptance criteria will be created without separate approval.

Drain completed on 2026-07-23. All eight children TASK-52.1 through TASK-52.8 are Done; no TASK-52 child remains To Do or In Progress. ADR-014 is human-Accepted and reconciled with shipped verification anchors. Final tree evidence: schema-v2 index is current; strict lint passes all 14 ADRs with 0 advisory/fail; doctor has 0 ADR findings and all three installed native client packages are healthy; 2/2 project retrieval probes pass with zero metadata findings; generated adapters have zero drift; release version surfaces agree at 0.39.0; git diff check passes; retrieval cold-process p95 is 204.4 ms for 200 ADRs and 297.9 ms for 1,000 ADRs; full supported suite is 867 passed, 10 skipped in 369.82 s.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Completed the index-first ADR retrieval epic end to end. ADR-INDEX.json schema v2 is now the shared, local, deterministic query projection for CLI, MCP, lifecycle hooks, and health workflows while Markdown remains authoritative. Authority-aware ranking, bounded metadata and Decision Contracts, visible fallback, strict mode, cross-client lifecycle behavior, retrieval probes, health reporting, dry-run migration suggestions, documentation, and release compatibility are implemented and verified. Human grilling and acceptance remain authoritative, hooks fail open, and deterministic enforcement remains fail closed. All eight child tasks and every epic acceptance criterion are complete.
<!-- SECTION:FINAL_SUMMARY:END -->
