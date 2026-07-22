---
id: TASK-50
title: 'Single source of truth for the release version: registry + bump writer'
status: In Progress
assignee:
  - '@claude'
created_date: '2026-07-22 20:13'
updated_date: '2026-07-22 20:13'
labels:
  - release
  - tooling
dependencies: []
priority: high
ordinal: 51500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Releasing 0.38.0 required hand-editing the version in 9 places across 4 discovery rounds (CHANGELOG, 3 plugin.json, 2 marketplace.json, 3 template stamps) plus README pins that no check covered. Root causes: no writer (generator validates but never propagates), the site list is duplicated across the generator check, check-release-version.py and 3 pytest asserts, the generator aborts on the first stale file, and template stamps are only caught by a 5-minute pytest run while README pins are caught by nothing. Introduce one declarative registry of version sites plus a bump writer, and have the checker, generator and tests all read that registry.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 packaging/version-sites.json declares every version-bearing file with a read/write strategy
- [ ] #2 scripts/bump-version.py X.Y.Z writes the version to every declared site in one command
- [ ] #3 check-release-version.py validates from the registry and covers template stamps and README pins
- [ ] #4 All stale sites are reported in one pass, not one-per-run
- [ ] #5 Release runbook and /release-adr-kit use bump-version.py
- [ ] #6 Test suite green; a release dry-run bumps cleanly with no hand-edits
<!-- AC:END -->
