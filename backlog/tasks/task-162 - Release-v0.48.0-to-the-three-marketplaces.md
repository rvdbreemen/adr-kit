---
id: TASK-162
title: Release v0.48.0 to the three marketplaces
status: In Progress
assignee:
  - '@claude'
created_date: '2026-08-09 15:49'
updated_date: '2026-08-09 16:06'
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
- [x] #1 bump-version.py moved every version site and the client trees were regenerated
- [x] #2 CHANGELOG has a release-quality 0.48.0 section naming the upgrade step for retired config keys
- [x] #3 All five local gates pass
- [ ] #4 PR into main is green and handed to the maintainer
- [ ] #5 Tag pushed, release-publish.yml green, GitHub Release created
- [ ] #6 Release merged back into dev
- [ ] #7 Local prepared-directory marketplace advanced and the three clients report 0.48.0
<!-- AC:END -->



## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-08-09: gates 1-5 all green locally. check-release-version --expect v0.48.0 (all publish surfaces agree), build-client-adapters --check (changed=0), adr-lint --strict (37 PASS strictly, 0 FAIL), adr-index --check (changed: False), pytest -q (1764 passed, 12 skipped, exit 0, 617s). Commit 7722627 on release/v0.48.0, pushed. PR #89 open into main: https://github.com/rvdbreemen/adr-kit/pull/89 - awaiting CI, then the maintainer merges (main is protected, enforce_admins).

Note for the tag step: the pre-commit judge ran declarative-only on this machine because judge.backend is 'host' with no host-client recorded in .adr-kit.local.json. Per ADR-025 that is a machine fact, not repository config; it does not affect the release, but this machine cannot run the LLM pass until `bin/adr-judge --set-backend host --host-client claude-code-cli` is run here.
<!-- SECTION:NOTES:END -->
