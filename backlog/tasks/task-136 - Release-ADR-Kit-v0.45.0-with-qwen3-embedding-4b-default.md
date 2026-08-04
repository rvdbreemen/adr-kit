---
id: TASK-136
title: 'Release ADR Kit v0.45.0 with qwen3-embedding:4b default'
status: Done
assignee: []
created_date: '2026-08-04 21:51'
updated_date: '2026-08-04 22:08'
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
- [x] #1 All version sites and CHANGELOG agree on v0.45.0
- [x] #2 Release PR into main passes required CI checks
- [x] #3 Main contains the verified release commit before tagging
- [x] #4 The v0.45.0 tag and GitHub Release are published
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Bump version and notes; run release gates; open and merge main PR; verify main; tag and publish
<!-- SECTION:PLAN:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Codex
created: 2026-08-04 22:08
---
Release verified on main commit 1aa3e42; tag v0.45.0 and GitHub Release are published.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Released adr-kit v0.45.0. The qwen3-embedding:4b default and explicit nomic fallback shipped on main; PR #64 merged, tag v0.45.0 and GitHub Release published, and the tag workflow passed all release gates including unit tests.
<!-- SECTION:FINAL_SUMMARY:END -->
