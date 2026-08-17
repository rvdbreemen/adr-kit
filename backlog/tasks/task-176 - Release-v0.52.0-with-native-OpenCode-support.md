---
id: TASK-176
title: Release v0.52.0 with native OpenCode support
status: In Progress
assignee: []
created_date: '2026-08-16 21:53'
updated_date: '2026-08-16 22:54'
labels:
  - release
  - opencode
  - documentation
dependencies: []
priority: high
type: chore
ordinal: 20000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Release the accepted native OpenCode integration as v0.52.0. Update the README, C4 architecture documentation, and changelog with an accurate support announcement. Keep OpenCode separate from the certified Claude Code, Codex, and GitHub Copilot CLI registry and release gate. Run the complete release gates before opening the release PR.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Version 0.52.0 is consistent across every declared version site.
- [x] #2 README and CHANGELOG announce native OpenCode support with its support boundary and installation path.
- [x] #3 Relevant C4 context, container, component, distribution, and quality documentation describes OpenCode without claiming three-client certification.
- [x] #4 All release gates and focused OpenCode tests pass, or any environmental blocker is recorded explicitly.
- [ ] #5 Release branch and PR are prepared without bypassing protected-branch maintainer controls.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Create the release branch. 2. Bump the canonical version and update release notes. 3. Refresh README and C4 documentation using the installed C4 architecture workflow guidance. 4. Run release gates and resolve failures. 5. Open the release PR and hand off protected-branch merge/tag actions.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Final validation on 2026-08-17: version gate passed for 0.52.0; generated adapters changed=0; strict ADR lint passed for 39 ADRs; ADR index unchanged; full C4-Documentation Markdownlint passed with 0 errors; README, CHANGELOG, client, and release documentation lint passed with 0 errors; focused OpenCode/version tests passed 26; deterministic judge checked 19 ADRs with 0 violations and 0 advisories; earlier isolated full suite passed 1795 with 13 skipped; dependency-hidden suite passed 1792 with 16 skipped. The branch is validation-complete, but no PR, merge, tag, GitHub Release, or npm publication has been performed. npm view still returns E404 for @rvdbreemen/adr-kit-opencode.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-08-16 22:54
---
Release preparation is validation-complete on release/v0.52.0. Protected-branch merge/tag actions and separate npm publication remain.
---
<!-- COMMENTS:END -->
