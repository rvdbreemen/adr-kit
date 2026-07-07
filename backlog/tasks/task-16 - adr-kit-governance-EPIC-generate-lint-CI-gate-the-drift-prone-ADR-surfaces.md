---
id: TASK-16
title: >-
  adr-kit governance (EPIC): generate + lint + CI-gate the drift-prone ADR
  surfaces
status: Done
assignee:
  - Codex
created_date: '2026-07-06 19:54'
updated_date: '2026-07-06 20:34'
labels:
  - adr-kit
  - governance
  - epic
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Umbrella for the adr-kit governance improvements from the 2026-07-04 ADR audit. Principle: derive the drift-prone surfaces (status lines, supersession links, README index, gate compliance) instead of hand-maintaining them. Full plan: docs/plan/adr-kit-governance-plan.md. Tracks WS1 schema+migrate, WS2 lint, WS3 index, WS4 lifecycle commands, WS5 after-the-fact fast path, WS6 CI+hooks, WS7 skill auto-trigger + doctor. Phased: A foundation (WS1/2 warn-only) -> B generation (WS3/4) -> C flow (WS5) -> D enforcement (WS6 blocking) -> E autonomy (WS7).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Goal: improve adr-kit for agent use and higher-quality local recall by turning ADR metadata into local, machine-checkable memory.

Drain sequence:
1. TASK-17: add canonical ADR frontmatter schema, a local frontmatter parser/validator, and an idempotent adr-migrate CLI that adds metadata without changing ADR body text. Wire adr-lint to reuse the schema validator behind an opt-in schema gate.
2. TASK-18: promote schema/status/link/gate consistency into adr-lint strict validation, including consuming-repo gate resolution.
3. TASK-19: generate/check README ADR indexes from parsed ADR metadata so recall surfaces stop drifting.
4. TASK-20: add lifecycle commands that mutate status/frontmatter/history/reciprocal links and refresh the index atomically.
5. TASK-21: add local evidence-backed fast-path acceptance for already-shipped ADRs using documents_shipped and verified_in.
6. TASK-22: add adr doctor and skill hooks so agents run local health checks before/after ADR work.

Execution notes: keep all behavior stdlib-only and local; no hosted service and no default LLM dependency. Treat structured metadata as the recall substrate for adr-context, doctor, and later memory quality improvements.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Moved from OTGW-firmware TASK-1004 because this is adr-kit repo work.

Reconciliation: adr-kit already has overlapping roadmap tasks (TASK-417..424, 749). WS1~TASK-424, WS2/WS6~TASK-422. Net-new from this audit: WS3 index generator, WS4 atomic lifecycle commands, WS5 documents-shipped auto-accept, WS7 doctor+skill-hook. Repo-local proof of WS2/WS3/WS6 landed via scripts/adr_governance.py (OTGW-firmware).

Proof landed for WS2/WS3/WS6 (repo-local): scripts/adr_governance.py + CI workflow + unit tests; live docs/adr tree now lint-clean and fully indexed (164 ADRs, 0 missing, 0 dup). The governance tool found and closed 24 index gaps beyond the audit window (ADR-91..120). WS1/WS4/WS5/WS7 remain adr-kit-repo work (reconcile with TASK-422/424).

Closed after draining child tasks TASK-17 through TASK-22 in adr-kit.

Delivered local, machine-checkable ADR governance and recall surfaces:
- TASK-17: canonical frontmatter schema, adr_schema helpers, adr-migrate, and schema lint gate.
- TASK-18: adr-lint --strict with frontmatter/status/supersession/evidence/gate consistency checks.
- TASK-19: generated docs/adr/README.md index with adr-index --check.
- TASK-20: bin/adr lifecycle commands for propose/accept/reject/supersede with append-only history, reciprocal supersession, and index refresh.
- TASK-21: documents_shipped + verified_in fast path and guarded local auto-accept.
- TASK-22: adr-doctor start/end workflow with strict lint, index health, staleness classes, and local audit trigger on material drift.

Goal constraints preserved: stdlib-only local tooling, no hosted service, and no default LLM dependency. Structured ADR frontmatter and generated index output now provide the local recall substrate for agents.

Final focused verification:
- python -m pytest tests/test_adr_doctor.py tests/test_adr_auto_accept.py tests/test_adr_lifecycle.py tests/test_adr_index.py tests/test_adr_migrate.py tests/test_adr_lint.py tests/test_adr_lint_supersession.py tests/test_adr_lint_governance.py tests/test_adr_policy.py tests/test_adr_context.py -q -> 80 passed
- python bin/adr-doctor --fix-index docs/adr -> index_ok=True lint_ok=True findings=0
- python bin/adr-doctor --fix-index --format json docs/adr -> index_ok=true, lint_ok=true, findings=0, audit.triggered=false
- python bin/adr-index --check docs/adr -> ADRs=3, duplicates=0, changed=False
- python bin/adr-lint --strict docs/adr -> PASS strictly 3, FAIL 0

Post-close global suite note: python -m pytest -q was run after focused verification. Result: 481 passed, 2 skipped, 5 failed in 127.57s. The failures are all in tests/test_python_check.py and exercise Windows bash.EXE/PATH/pre-commit hook behavior; they are outside the TASK-16..22 ADR governance surfaces. The focused TASK-16..22 regression slice remains clean at 80 passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Done. The epic is closed after completing TASK-17 through TASK-22: adr-kit now has local canonical ADR metadata, migration, strict validation, generated indexes, lifecycle mutation commands, evidence-backed auto-accept, and doctor-driven agent start/end health checks for better local memory recall.
<!-- SECTION:FINAL_SUMMARY:END -->
