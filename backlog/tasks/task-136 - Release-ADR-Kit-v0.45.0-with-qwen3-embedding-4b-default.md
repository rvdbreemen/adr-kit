---
id: TASK-136
title: 'Release ADR Kit v0.45.0 with qwen3-embedding:4b default'
status: In Progress
assignee: []
created_date: '2026-08-04 21:51'
labels:
  - release embedding
dependencies: []
priority: high
ordinal: 108500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Prepare and publish adr-kit v0.45.0 from dev after the qwen3-embedding:4b default and current unreleased fixes are merged.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All version sites and CHANGELOG agree on v0.45.0
- [ ] #2 Release PR into main passes required CI checks
- [ ] #3 Main contains the verified release commit before tagging
- [ ] #4 The v0.45.0 tag and GitHub Release are published
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Bump version and notes; run release gates; open and merge main PR; verify main; tag and publish
<!-- SECTION:PLAN:END -->
