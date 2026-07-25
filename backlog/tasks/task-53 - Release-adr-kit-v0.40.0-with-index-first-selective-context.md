---
id: TASK-53
title: Release adr-kit v0.40.0 with index-first selective context
status: Done
assignee:
  - '@Codex'
created_date: '2026-07-23 19:53'
updated_date: '2026-07-23 20:57'
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
  - docs/adr/ADR-007-generated-adr-index-and-relationship-graph.md
  - docs/adr/ADR-INDEX.json
  - tests/test_adr_retrieval_health.py
  - .github/workflows/validate.yml
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
- [x] #4 A release branch is committed and pushed, a PR to protected main is opened, and final-head CI is green without bypassing branch protection.
- [x] #5 After maintainer merge, main is pulled and verified, tag v0.40.0 is pushed, and the tag-triggered GitHub Release workflow completes successfully.
- [x] #6 The local prepared-directory marketplace is advanced and Claude, Codex, and Copilot installations are individually verified at 0.40.0.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Create the release branch from the current TASK-52 worktree. 2. Run scripts/bump-version.py 0.40.0 and regenerate client adapters. 3. Turn the Unreleased TASK-52 notes into the dated v0.40.0 release section and verify README usage. 4. Run every local release gate and full regression suite. 5. Commit and push the release branch, open a PR, monitor final-head CI, and hand off at the protected-main maintainer checkpoint. 6. After maintainer merge, verify main, push v0.40.0, monitor the release workflow, then update and verify all three local prepared client installations.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Prepared v0.40.0 on branch release/v0.40.0-index-first-retrieval. scripts/bump-version.py updated all 10 declared version sites and generated client adapters are synchronized. CHANGELOG release notes cover schema-v2 retrieval, authority-aware lifecycle behavior, probes, safe migration, UserPromptSubmit timeout resilience, upgrade steps, one-minor compatibility, risks, and rollback. Local release evidence on 2026-07-23: check-release-version PASS; adapter drift 0; strict ADR lint 14/14 PASS with 0 advisory/fail; ADR index current; git diff check PASS; focused release-contract suite 48 passed; full supported suite 867 passed, 10 skipped in 369.89 seconds.

The first release commit attempt was correctly blocked by ADR-007's stale declarative schema-v1 gate. Resolved without bypass: ADR-007 was lifecycle-revalidated as explicitly amended by human-Accepted ADR-014, its enforcement now requires schema v2, and the generated graph exposes ADR-007 --amended-by--> ADR-014. Strict lint, index freshness, doctor (0 ADR findings), version/adapters checks, and the final full suite pass. Final post-amendment full suite: 867 passed, 10 skipped in 392.89 seconds.

PR #36 CI diagnosis: all six Python compatibility jobs failed during collection because tests/test_adr_retrieval_health.py imported the undeclared jsonschema package while matrix jobs intentionally install only pytest. Approved focused fix removes that dependency from Python tests, exercises the production stdlib load_probes validator, and adds complete draft-2020-12 probe validation to the existing AJV validate job. The probe schema and dogfood probe document are now explicit required release files.

Approved CI correction verification: retrieval-health module 8 passed locally and 8 passed again in a fresh virtual environment with only pytest installed; the exact AJV draft-2020 command validates docs/adr/adr-context-probes.json; release version registry, generated adapters, strict ADR lint (14/14), index freshness, and git diff checks all pass; full regression suite 867 passed, 10 skipped in 428.72 seconds.

PR #36 final-head CI for commit 423dfcd is green: declarative ADR enforcement, adr-readiness, generated-index freshness, lint smoke, validate/AJV, pytest, and the six Python 3.10/3.12 compatibility jobs across Ubuntu, macOS, and Windows all passed. Branch protection was not bypassed.

Maintainer merged PR #36 as 9dddfbee1fe1a9436e6d0354eadb9bcb2eca0a14. Post-merge main workflows passed, tag v0.40.0 points to that merge, release-publish run 30042881197 passed, and GitHub Release https://github.com/rvdbreemen/adr-kit/releases/tag/v0.40.0 is published (not draft or prerelease).

Prepared marketplace C:/Users/rvdbr/AppData/Local/adr-kit/marketplaces/0.40.0 passed MCP and Claude hook validation. Claude reports adr-kit 0.40.0 enabled; Copilot reports v0.40.0 installed. Codex remains at 0.39.0 because this active Codex process holds its plugin cache open, so native removal failed with Windows os error 32. AC #6 remains open until Codex is restarted, the Codex-only installer is rerun, and codex plugin list confirms 0.40.0.

Final local verification succeeded after stopping only the stale ADR Kit MCP child process owned by the active Codex process. The supported Codex-only installer then removed 0.39.0, registered prepared marketplace 0.40.0, installed the plugin, and passed validation. Independent final lists confirm Claude 0.40.0 enabled, Codex 0.40.0 installed/enabled, and Copilot v0.40.0 installed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Released adr-kit v0.40.0 from protected main. PR #36 merged with all CI green; tag v0.40.0 and release-publish run 30042881197 succeeded; the public GitHub Release is live. The CI-only jsonschema collection failure was fixed dependency-free by using the stdlib probe loader in Python tests and AJV for complete probe-schema validation. The local prepared marketplace was advanced and Claude, Codex, and Copilot were each verified at 0.40.0.
<!-- SECTION:FINAL_SUMMARY:END -->
