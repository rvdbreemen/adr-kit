---
id: TASK-21
title: >-
  adr-kit WS5: after-the-fact ADR fast path (documents-shipped ->
  evidence-backed auto-accept)
status: Done
assignee:
  - Codex
created_date: '2026-07-06 19:54'
updated_date: '2026-07-06 20:22'
labels:
  - adr-kit
  - governance
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
5 ADRs sat in Proposed for weeks though each documented already-shipped code. adr document scaffolds documents_shipped:true and requires a verified_in pointer. adr accept auto-accepts iff documents_shipped AND every verified_in resolves AND lint passes AND quality>=threshold, recording evidence in Status History. Guardrails: only documents_shipped eligible; forward-looking ADRs keep the human checkpoint; dangling pointer blocks; auto vs assist(confirm) strictness configurable. Full plan: docs/plan/adr-kit-governance-plan.md. Repo: adr-kit.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 adr document scaffolds documents_shipped:true and requires a verified_in pointer
- [x] #2 documents_shipped + resolving evidence + clean lint auto-accepts with an audit-trail Status History entry
- [x] #3 Broken pointer or documents_shipped:false does NOT auto-accept
- [x] #4 auto vs assist strictness configurable
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Implementation plan for TASK-21:
1. Extend bin/adr with a document subcommand for after-the-fact ADRs. It will set documents_shipped:true and require at least one --verified-in pointer, keeping the workflow local and explicit.
2. Extend accept with --auto plus configurable auto/assist mode and quality threshold. Auto acceptance will be allowed only for documents_shipped:true ADRs with verified_in pointers.
3. Reuse local CLIs for safety: adr-lint --strict must pass for the target file and adr-quality --format json must meet the configured/default threshold before an auto accept mutates anything.
4. Broken evidence pointers, documents_shipped:false, or low quality must block auto acceptance and leave the ADR unchanged.
5. Auto and confirmed-assist acceptance append Status History and refresh the generated index through the existing lifecycle path.
6. Add tests for document requiring verified_in, successful auto accept, broken-pointer block, documents_shipped:false block, and assist-mode no-mutation without confirmation.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Moved from OTGW-firmware TASK-1009 because this is adr-kit repo work.

Implemented after-the-fact ADR fast path in bin/adr. Added document subcommand that requires --verified-in and sets documents_shipped:true. Added accept --auto with local eligibility checks: documents_shipped:true, non-empty verified_in, adr-lint --strict pass against --repo-root, and adr-quality score >= configured/default threshold. Added --auto-mode auto|assist, --confirm for assist mutation, --quality-threshold, --config, and --repo-root.

Guardrails: documents_shipped:false blocks auto acceptance; broken verified_in pointers block before mutation; assist mode reports eligibility without mutating unless --confirm is used. Successful auto accept appends Status History and refreshes the generated index.

Verification:
- python -m pytest tests/test_adr_auto_accept.py -q -> 5 passed
- python -m pytest tests/test_adr_auto_accept.py tests/test_adr_lifecycle.py tests/test_adr_index.py tests/test_adr_migrate.py tests/test_adr_lint.py tests/test_adr_lint_supersession.py tests/test_adr_lint_governance.py tests/test_adr_policy.py tests/test_adr_context.py -q -> 75 passed
- python bin/adr-index --check docs/adr -> changed=False, duplicates=0
- python bin/adr-lint --strict docs/adr -> PASS strictly 3, FAIL 0
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added the local after-the-fact ADR acceptance path. bin/adr document now marks already-shipped ADRs with documents_shipped:true and required verified_in evidence. bin/adr accept --auto accepts only when the target has shipped evidence, strict lint passes, and adr-quality meets the threshold; unsafe cases leave the ADR untouched. Assist mode can report eligibility without mutation.

Tests: auto-accept tests and focused lifecycle/index/migration/lint/governance/policy/context regression slice pass; repo docs/adr index and strict lint remain clean.
<!-- SECTION:FINAL_SUMMARY:END -->
