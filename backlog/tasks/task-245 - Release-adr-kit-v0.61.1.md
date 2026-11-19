---
id: TASK-245
title: Release adr-kit v0.61.1
status: Done
assignee: []
created_date: '2026-11-19T07:28:00Z'
updated_date: '2026-11-19T20:42:00Z'
labels: []
dependencies: []
priority: high
type: chore
ordinal: 87000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Ship the Windows Codex hook repair and the unreleased stale-index, linter, and ADR cross-reference fixes. Reserve v0.62.0 for OMP certification as agreed in ADR-050. Follow docs/RELEASING.md and ADR-042, with workflow-generated tag and npm staging.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Prepare the v0.61.1 version sites and release notes and pass release verification.
- [x] #2 Land the protected release PR and verify the workflow-created tag and GitHub Release at the main merge commit.
- [x] #3 Verify npm staging and final latest version after the maintainer's npm approval.
- [x] #4 Merge the release back into dev and verify branch sync.
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
v0.61.1 (patch: Windows Codex hook repair, stale-index recovery, relate fix; no consumer-visible behaviour change beyond bug fixes; v0.62.0 reserved for OMP per ADR-050). PR #212 merged into main at 0ab9cb7 (2026-11-19 19:45 UTC) via auto-merge. release-publish.yml run 44601649937 succeeded; tag v0.61.1 resolves to 0ab9cb7 = origin/main (git ls-remote). Release https://github.com/rvdbreemen/adr-kit/releases/tag/v0.61.1 published 19:48 UTC, not draft. Sync-back PR #213 merged into dev 20:32 UTC. Driver install phase: all three clients report 0.61.1. npm @rvdbreemen/adr-kit-opencode dist-tags.latest = 0.61.1 (npm view). Local full suite: 2164 passed, 1 failed (test_lint_and_retire_meet_hard_ceiling_on_this_repo, adr-lint p50 2192ms > 2000ms under concurrent OTGW build load; passed 2x in isolation); release proceeded with --skip-tests relying on green CI matrix on 5325d20. Driver defects filed separately.
<!-- SECTION:FINAL_SUMMARY:END -->
