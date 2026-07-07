---
id: TASK-20
title: >-
  adr-kit WS4: lifecycle commands (propose/accept/supersede/reject)
  mutate+reciprocate+reindex
status: Done
assignee:
  - Codex
created_date: '2026-07-06 19:54'
updated_date: '2026-07-06 20:19'
labels:
  - adr-kit
  - governance
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Humans should never hand-edit a status line, a reciprocal link, or the index. Each command mutates frontmatter + reciprocals + Status History then runs adr index: propose, accept [--by], supersede <old> --by <new> (stamps both files), reject --reason (terminal, kept as trail). Full plan: docs/plan/adr-kit-governance-plan.md. Repo: adr-kit.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 adr supersede 160 --by 164 reproduces the two-file edit + index update done by hand this session
- [x] #2 No lifecycle command leaves the index stale (adr index --check green afterward)
- [x] #3 Each command appends a Status History entry
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Implementation plan for TASK-20:
1. Add a stdlib-only bin/adr lifecycle entrypoint with subcommands propose, accept, supersede, and reject. Keep it local and file-based.
2. Reuse bin/adr_schema.py to parse/render frontmatter and update lifecycle fields; add/repair frontmatter if needed before mutation.
3. Update the body Status section plus append-only Status History for every lifecycle mutation. For supersede, stamp both old and successor ADRs: old gets Superseded + superseded_by, successor gets supersedes reciprocal + history entry.
4. After each command, run bin/adr-index for the ADR directory so README is not left stale; tests will assert adr-index --check is green.
5. Add focused tests for supersede reciprocal edits/history/index freshness and basic accept/reject/propose status-history behavior.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Moved from OTGW-firmware TASK-1008 because this is adr-kit repo work.

Implemented bin/adr lifecycle entrypoint with propose, accept, reject, and supersede commands. Commands normalize/add frontmatter, update the body Status section, append Status History, and run bin/adr-index afterward. Supersede stamps both files: the old ADR gets status Superseded + superseded_by, and the successor receives the reciprocal supersedes entry plus a history entry.

Verification:
- python -m pytest tests/test_adr_lifecycle.py -q -> 4 passed
- python -m pytest tests/test_adr_lifecycle.py tests/test_adr_index.py tests/test_adr_migrate.py tests/test_adr_lint.py tests/test_adr_lint_supersession.py tests/test_adr_lint_governance.py tests/test_adr_policy.py tests/test_adr_context.py -q -> 70 passed
- python bin/adr-index --check docs/adr -> changed=False, duplicates=0
- python bin/adr-lint --strict docs/adr -> PASS strictly 3, FAIL 0
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added local lifecycle commands through bin/adr. propose/accept/reject update status and append history; supersede mutates both old and successor ADRs with reciprocal metadata and history entries. Every command refreshes the generated index so --check remains clean. README now documents the lifecycle command surface.

Tests: lifecycle tests and the focused index/migration/lint/governance/policy/context regression slice pass; repo docs/adr index and strict lint remain clean.
<!-- SECTION:FINAL_SUMMARY:END -->
