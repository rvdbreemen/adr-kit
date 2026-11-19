---
id: TASK-245
title: Release adr-kit v0.61.1
status: In Progress
assignee: []
created_date: '2026-11-19T07:28:00Z'
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
- [ ] #1 Prepare the v0.61.1 version sites and release notes and pass release verification.
- [ ] #2 Land the protected release PR and verify the workflow-created tag and GitHub Release at the main merge commit.
- [ ] #3 Verify npm staging and final latest version after the maintainer's npm approval.
- [ ] #4 Merge the release back into dev and verify branch sync.
<!-- AC:END -->
