---
id: TASK-53
title: Release adr-kit v0.40.0 with index-first selective context
status: In Progress
assignee:
  - '@Codex'
created_date: '2026-07-23 19:53'
updated_date: '2026-07-23 20:11'
labels:
  - release
  - marketplace
  - index-first-retrieval
dependencies: []
references:
  - TASK-52
  - docs/RELEASING.md
  - .claude/commands/release-adr-kit.md
  - ADR-012
  - ADR-014
documentation:
  - CHANGELOG.md
  - README.md
  - docs/RELEASING.md
modified_files:
  - CHANGELOG.md
  - README.md
  - .claude-plugin/plugin.json
  - codex/.codex-plugin/plugin.json
  - copilot/plugin.json
  - .claude-plugin/marketplace.json
  - .github/plugin/marketplace.json
  - templates/adr-kit-guide.md
  - templates/cc-settings/guardian-hook-entry.json
  - templates/githooks/pre-commit
priority: high
ordinal: 54500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Bump the completed TASK-52 implementation to v0.40.0, prepare release-quality notes, run the repository release gates, publish a protected-branch PR, and after maintainer merge tag and verify the GitHub Release plus local three-client prepared installation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 All declared version sites and generated client adapters consistently report 0.40.0.
- [x] #2 The 0.40.0 CHANGELOG section provides user-facing release notes, upgrade guidance, compatibility behavior, risks, and rollback guidance.
- [x] #3 Release gates pass: version registry, generated adapters, strict ADR lint, generated index freshness, git diff check, and the full supported pytest suite.
- [ ] #4 A release branch is committed and pushed, a PR to protected main is opened, and final-head CI is green without bypassing branch protection.
- [ ] #5 After maintainer merge, main is pulled and verified, tag v0.40.0 is pushed, and the tag-triggered GitHub Release workflow completes successfully.
- [ ] #6 The local prepared-directory marketplace is advanced and Claude, Codex, and Copilot installations are individually verified at 0.40.0.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Create the release branch from the current TASK-52 worktree. 2. Run scripts/bump-version.py 0.40.0 and regenerate client adapters. 3. Turn the Unreleased TASK-52 notes into the dated v0.40.0 release section and verify README usage. 4. Run every local release gate and full regression suite. 5. Commit and push the release branch, open a PR, monitor final-head CI, and hand off at the protected-main maintainer checkpoint. 6. After maintainer merge, verify main, push v0.40.0, monitor the release workflow, then update and verify all three local prepared client installations.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Prepared v0.40.0 on branch release/v0.40.0-index-first-retrieval. scripts/bump-version.py updated all 10 declared version sites and generated client adapters are synchronized. CHANGELOG release notes cover schema-v2 retrieval, authority-aware lifecycle behavior, probes, safe migration, UserPromptSubmit timeout resilience, upgrade steps, one-minor compatibility, risks, and rollback. Local release evidence on 2026-07-23: check-release-version PASS; adapter drift 0; strict ADR lint 14/14 PASS with 0 advisory/fail; ADR index current; git diff check PASS; focused release-contract suite 48 passed; full supported suite 867 passed, 10 skipped in 369.89 seconds.

The first release commit attempt was correctly blocked by ADR-007's stale declarative schema-v1 gate. Resolved without bypass: ADR-007 was lifecycle-revalidated as explicitly amended by human-Accepted ADR-014, its enforcement now requires schema v2, and the generated graph exposes ADR-007 --amended-by--> ADR-014. Strict lint, index freshness, doctor (0 ADR findings), version/adapters checks, and the final full suite pass. Final post-amendment full suite: 867 passed, 10 skipped in 392.89 seconds.
<!-- SECTION:NOTES:END -->
