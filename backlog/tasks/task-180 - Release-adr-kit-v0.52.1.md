---
id: TASK-180
title: Release adr-kit v0.52.2
status: In Progress
assignee: []
created_date: '2026-08-18 18:20'
updated_date: '2026-08-19 05:38'
labels:
  - release
  - github
  - npm
dependencies: []
references:
  - docs/RELEASING.md
  - 'https://github.com/rvdbreemen/adr-kit/actions/workflows/release-publish.yml'
modified_files:
  - .claude-plugin/marketplace.json
  - .claude-plugin/plugin.json
  - .githooks/pre-commit
  - .github/plugin/marketplace.json
  - CHANGELOG.md
  - README.md
  - codex/.codex-plugin/plugin.json
  - codex/templates/adr-kit-guide.md
  - codex/templates/cc-settings/guardian-hook-entry.json
  - codex/templates/githooks/pre-commit
  - copilot/plugin.json
  - copilot/templates/adr-kit-guide.md
  - copilot/templates/cc-settings/guardian-hook-entry.json
  - copilot/templates/githooks/pre-commit
  - docs/clients/opencode.md
  - package.json
  - templates/adr-kit-guide.md
  - templates/cc-settings/guardian-hook-entry.json
  - templates/githooks/pre-commit
  - tests/certification/simulated-pass.json
priority: high
type: chore
ordinal: 24000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Publish the OpenCode reference-shape fix and refreshed certification evidence as adr-kit v0.52.2 through the protected GitHub release workflow, then stage @rvdbreemen/adr-kit-opencode for npm approval. The previously pushed v0.52.1 tag remains unchanged and unpublished because its workflow correctly stopped on stale evidence.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All declared version sites and generated adapters agree on v0.52.2.
- [ ] #2 The documented release gates pass on the release branch.
- [ ] #3 The GitHub release workflow creates the v0.52.2 release and stages the npm package for approval.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Refresh the stale certification fixture and finalize v0.52.2 release notes and version sites. 2. Run the documented release gates. 3. Open the release PR into main and, after maintainer merge, tag the exact merged commit to trigger GitHub Release and npm staging.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
The first v0.52.1 tag workflow stopped before publication because CI correctly detected the simulated certification fixture contract_date 2026-07-19 as stale on 2026-08-19. The tag is retained unchanged; refresh the fixture and publish the next coherent patch v0.52.2 instead of force-moving history.
<!-- SECTION:NOTES:END -->
