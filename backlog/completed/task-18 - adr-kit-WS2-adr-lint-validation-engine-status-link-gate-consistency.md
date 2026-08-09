---
id: TASK-18
title: 'adr-kit WS2: ''adr lint'' validation engine (status/link/gate consistency)'
status: Done
assignee:
  - Codex
created_date: '2026-07-06 19:54'
updated_date: '2026-07-06 20:13'
labels:
  - adr-kit
  - governance
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Replace human review of ADR consistency; make ADR-080 machine-checked. Rules: schema-valid frontmatter; superseded_by non-empty <=> status Superseded; supersedes/superseded_by reciprocity; binding+Accepted implies named gate exists in evaluate.py/tests or ADR is guideline-level; quality-gate scoring; verified_in resolves. --strict for CI + JSON output. Full plan: docs/plan/adr-kit-governance-plan.md. Repo: adr-kit.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Non-zero exit on missing frontmatter, status/link contradiction, broken reciprocity, or accepted-binding-ADR with absent gate
- [x] #2 ADR-080 gate rule resolves the named gate against the consuming repo
- [x] #3 --strict (CI) and JSON output modes
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Implementation plan for TASK-18:
1. Add adr-lint --strict as the CI/governance mode. In strict mode, enable schema validation by default and treat non-skipped findings as FAIL regardless of advisory legacy policy.
2. Extend lint consistency with frontmatter-aware rules: body status must match frontmatter status, Superseded requires superseded_by and non-Superseded must not set it, supersedes/superseded_by links must reciprocate, and referenced ADR ids must exist.
3. Add local evidence resolution for verified_in entries: relative file paths, file:symbol pointers, and commit:<sha> pointers resolve against --repo-root/current project.
4. Add accepted binding gate validation: Accepted + binding:true requires a non-empty gate whose name is found locally in the consuming repo (evaluate.py/tests/scripts/.github or repo text scan); binding:false remains the guideline/no-code-surface path.
5. Keep JSON output stable and include strict_mode/repo_root in machine output for CI callers.
6. Add focused tests for missing frontmatter, status/link contradictions, broken reciprocity, verified_in resolution, and gate existence.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Moved from OTGW-firmware TASK-1006 because this is adr-kit repo work.

Reconcile with TASK-422 (adr-kit v0.10 standalone adr-lint CLI for CI): this WS2 overlaps; extend 422 with the ADR-080 gate-existence rule and status<->superseded_by reciprocity rather than duplicate.

Implemented strict governance validation in adr-lint. Added --strict and --repo-root, strict-mode JSON fields, frontmatter-aware consistency checks, local verified_in resolution (path, path:symbol, commit:<sha>), reciprocal supersedes/superseded_by validation, and Accepted binding gate lookup against local consuming-repo files. Strict mode enables schema by default and makes non-skipped findings FAIL for CI.

Verification:
- python -m pytest tests/test_adr_lint_governance.py -q -> 6 passed
- python -m pytest tests/test_adr_migrate.py tests/test_adr_lint.py tests/test_adr_lint_supersession.py tests/test_adr_lint_governance.py tests/test_adr_policy.py tests/test_adr_context.py -q -> 62 passed
- python bin/adr-lint --strict --format json docs/adr -> pass=3 fail=0, gates schema/completeness/audit/consistency
- python bin/adr-lint --strict docs/adr -> human output clean

README CI guidance now uses python /tmp/adr-lint --strict docs/adr/ and explains strict-mode governance checks.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Promoted the TASK-17 schema foundation into a strict local governance mode for adr-lint. CI callers can now use --strict to require canonical frontmatter, status/link consistency, reciprocal supersession metadata, local evidence pointers, and binding-gate existence. JSON output reports strict_mode and repo_root for machines; README lint/CI docs now point at strict mode.

Tests: governance tests and the focused lint/migration/policy/context regression slice pass. Repo docs/adr passes strict lint cleanly.
<!-- SECTION:FINAL_SUMMARY:END -->
