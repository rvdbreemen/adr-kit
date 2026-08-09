---
id: TASK-50
title: 'Single source of truth for the release version: registry + bump writer'
status: Done
assignee:
  - '@claude'
created_date: '2026-07-22 20:13'
updated_date: '2026-07-22 22:04'
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
- [x] #1 packaging/version-sites.json declares every version-bearing file with a read/write strategy
- [x] #2 scripts/bump-version.py X.Y.Z writes the version to every declared site in one command
- [x] #3 check-release-version.py validates from the registry and covers template stamps and README pins
- [x] #4 All stale sites are reported in one pass, not one-per-run
- [x] #5 Release runbook and /release-adr-kit use bump-version.py
- [x] #6 Test suite green; a release dry-run bumps cleanly with no hand-edits
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Made the release version a declared, written value. packaging/version-sites.json declares every version-bearing file (JSON pointer or regex) plus the negative invariant that the Codex local marketplace inherits its version; scripts/version_sites.py is the shared implementation read by the bump writer, the release gate, the client-adapter generator and the tests; scripts/bump-version.py writes them all in one command. The gate now also covers the three template stamps and the README pins, and every stale site is reported in one pass. Dogfooded on 0.39.0: 10 sites plus the CHANGELOG heading written by one command, zero hand-edits, where 0.38.0 needed nine hand-edits across four discovery rounds. ADR-013 (Accepted) amends ADR-012. Shipped in v0.39.0; all three clients verified on 0.39.0.
<!-- SECTION:FINAL_SUMMARY:END -->
