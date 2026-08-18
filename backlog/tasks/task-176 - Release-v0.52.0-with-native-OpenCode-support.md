---
id: TASK-176
title: Release v0.52.0 with native OpenCode support
status: Done
assignee: []
created_date: '2026-08-16 21:53'
updated_date: '2026-08-18 05:38'
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
- [x] #5 Release branch and PR are prepared without bypassing protected-branch maintainer controls.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Create the release branch. 2. Bump the canonical version and update release notes. 3. Refresh README and C4 documentation using the installed C4 architecture workflow guidance. 4. Run release gates and resolve failures. 5. Open the release PR and hand off protected-branch merge/tag actions.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Release completed on 2026-08-17: PR #102 merged into main at d6442b03f8bc2157c3639a56f4ce13fdd4bf5e52; tag v0.52.0 points to that merge commit; release-publish workflow run 32000229247 passed all gates and created https://github.com/rvdbreemen/adr-kit/releases/tag/v0.52.0. The main-to-dev sync branch is pushed and PR #103 is open at https://github.com/rvdbreemen/adr-kit/pull/103; its current CI checks are all green. npm publication remains separate and has not been performed.

Correction recorded on 2026-08-18: @rvdbreemen/adr-kit-opencode@0.52.0 was subsequently published to npm manually with 2FA. PR #106 integrated future npm staging into release-publish.yml through OIDC, with final maintainer approval still required.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-08-16 22:54
---
Release preparation is validation-complete on release/v0.52.0. Protected-branch merge/tag actions and separate npm publication remain.
---

created: 2026-08-17 05:57
---
Opened release PR #102: https://github.com/rvdbreemen/adr-kit/pull/102. The requested commit, push, and PR preparation are complete; protected-branch merge and tagging remain.
---

created: 2026-08-17 06:14
---
Release publication verified: tag v0.52.0, workflow 32000229247, and GitHub Release are complete. Sync PR #103 is green and awaiting maintainer merge; npm remains a separate unpublished operation.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Released v0.52.0 with native OpenCode support. PR #102 was merged, tag v0.52.0 was pushed, the GitHub Release was created successfully, and the documented sync PR #103 is open to bring the release back into dev.
<!-- SECTION:FINAL_SUMMARY:END -->
