---
id: TASK-162
title: Release v0.48.0 to the three marketplaces
status: In Progress
assignee:
  - '@claude'
created_date: '2026-08-09 15:49'
updated_date: '2026-08-09 15:49'
labels:
  - release
dependencies: []
priority: high
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Ships 22 commits since v0.47.0: the ADR-036 KISS simplification (vector layer retired, judge reduced to the host backend, eight config keys refused by name, health family folded behind adr-audit, one setup entry point), ADR-037 per-ADR judge verdicts in the guardian, the R5 prompt-injection rephrasing (candidates the model selects from), the upgrade-path work (whole-set cost picture in adr-migrate, backend and cadence steps in the upgrade skill), and eleven review findings fixed. Minor rather than patch: a config carrying a retired key now fails validation loudly instead of being ignored, which is an upgrade step for existing projects.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 bump-version.py moved every version site and the client trees were regenerated
- [ ] #2 CHANGELOG has a release-quality 0.48.0 section naming the upgrade step for retired config keys
- [ ] #3 All five local gates pass
- [ ] #4 PR into main is green and handed to the maintainer
- [ ] #5 Tag pushed, release-publish.yml green, GitHub Release created
- [ ] #6 Release merged back into dev
- [ ] #7 Local prepared-directory marketplace advanced and the three clients report 0.48.0
<!-- AC:END -->
