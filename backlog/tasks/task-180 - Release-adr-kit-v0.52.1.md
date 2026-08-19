---
id: TASK-180
title: Release adr-kit v0.52.1
status: In Progress
assignee: []
created_date: '2026-08-18 18:20'
updated_date: '2026-08-18 22:00'
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
  - opencode/plugin.ts
  - package.json
  - templates/adr-kit-guide.md
  - templates/cc-settings/guardian-hook-entry.json
  - templates/githooks/pre-commit
  - tests/test_opencode_plugin.py
priority: high
type: chore
ordinal: 24000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Publish the OpenCode reference-shape fix as adr-kit v0.52.1 through the protected GitHub release workflow and stage @rvdbreemen/adr-kit-opencode for npm approval.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All declared version sites and generated adapters agree on v0.52.1.
- [ ] #2 The documented release gates pass on the release branch.
- [ ] #3 The GitHub release workflow creates the v0.52.1 release and stages the npm package for approval.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Finalize v0.52.1 release notes and version sites. 2. Run the documented release gates. 3. Open the release PR into main and, after maintainer merge, tag the exact merged commit to trigger GitHub Release and npm staging.
<!-- SECTION:PLAN:END -->
