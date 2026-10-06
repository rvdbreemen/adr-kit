---
id: TASK-218
title: Release v0.59.1 to the three marketplaces
status: Done
assignee: []
created_date: '2026-10-05 21:31'
updated_date: '2026-10-06 05:05'
labels:
  - chore
  - release
dependencies: []
priority: high
ordinal: 62000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Patch release carrying the #155 pre-commit hook fix (TASK-216, PR #179). Why a patch: on every supported setup (a Python 3.10+ on PATH, the documented floor in README.md:46) the only observable differences are the two reported bugs going away; _version_ge picks the same winner as sort -V | tail -1 for x.y.z manifest versions, ties included. Below the floor (a machine whose only Python is 3.9 or older) the hook now takes its existing, tested non-blocking path ('Python 3 not found ... Skipping ADR check') instead of running adr-judge on an unsupported interpreter, which the reporter observed failing outright. That case is stated as an upgrade note in the 0.59.1 section.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 CHANGELOG ## [0.59.1] holds the #155 entries plus the below-3.10 upgrade note; [Unreleased] is empty
- [x] #2 Full local suite green, or CI relied on with the reason recorded
- [x] #3 Tag v0.59.1 resolves to origin/main; GitHub Release published
- [x] #4 Sync-back PR merged into dev
- [x] #5 Per-client versions read back as 0.59.1
- [x] #6 npm dist-tags.latest names 0.59.1
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
v0.59.1 is released as a patch: the #155 pre-commit hook fixes (TASK-216). Patch because on every supported setup (Python 3.10+, the documented floor) the only observable change is the two bugs going away; the below-3.10 case is stated as an upgrade note. Full local suite run in two foreground halves after freeing memory: 960+1005 passed, 4+8 skipped (1965/12), then the driver with --skip-tests; its other gates (version consistency, adapter drift, adr-lint --strict, adr-index --check) passed. Release PR #181 merged into main; tag v0.59.1 resolves to 9bfe58d, equal to origin/main, created by release-publish.yml (run 37381420173, success). Release page https://github.com/rvdbreemen/adr-kit/releases/tag/v0.59.1 (not draft, not prerelease, published 2026-10-05T22:19:08Z), body is the 0.59.1 CHANGELOG section. Sync-back PR #182 merged. All three clients report 0.59.1. npm dist-tags.latest is 0.59.1, approved by the maintainer. Driver reports 'v0.59.1 is released and every surface agrees.' A first driver run was killed by Claude Code's low-memory reaper during verify; nothing had been pushed, and the resumed run continued the prepared release.
<!-- SECTION:FINAL_SUMMARY:END -->
