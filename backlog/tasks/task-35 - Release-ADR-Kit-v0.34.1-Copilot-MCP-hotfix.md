---
id: TASK-35
title: Release ADR Kit v0.34.1 Copilot MCP hotfix
status: In Progress
assignee:
  - Codex
created_date: '2026-07-19 07:47'
updated_date: '2026-07-19 07:54'
labels:
  - release
  - copilot
  - hotfix
dependencies:
  - TASK-34
documentation:
  - CONTRIBUTING.md
  - CHANGELOG.md
modified_files:
  - CHANGELOG.md
  - .claude-plugin/plugin.json
  - .claude-plugin/marketplace.json
  - .github/plugin/marketplace.json
  - .githooks/pre-commit
  - codex/.codex-plugin/plugin.json
  - codex/templates/adr-kit-guide.md
  - codex/templates/cc-settings/guardian-hook-entry.json
  - codex/templates/githooks/pre-commit
  - copilot/plugin.json
  - copilot/templates/adr-kit-guide.md
  - copilot/templates/cc-settings/guardian-hook-entry.json
  - copilot/templates/githooks/pre-commit
  - templates/adr-kit-guide.md
  - templates/cc-settings/guardian-hook-entry.json
  - templates/githooks/pre-commit
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Publish the merged Copilot MCP executable-path correction as ADR Kit v0.34.1 using the repository release procedure: changelog, synchronized version stamps, validation, release PR, annotated tag, and GitHub Release.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 CHANGELOG records the Copilot MCP path/root correction under v0.34.1.
- [x] #2 All client manifests, marketplaces, guide, and wrapper stamps report 0.34.1.
- [x] #3 Release validation and synchronized payload checks pass.
- [ ] #4 The release changes are merged to main through a green GitHub pull request.
- [ ] #5 Annotated tag v0.34.1 and a GitHub Release with user-facing recovery notes are published.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Record the Copilot MCP path/root correction under Unreleased and run `python bin/bump-version 0.34.1`. 2. Synchronize Codex and Copilot payloads and run the documented release validation. 3. Commit and push `agent/release-v0.34.1`, open a release PR, wait for all required GitHub checks, and merge it. 4. Create annotated tag `v0.34.1` on the merged release commit and publish GitHub Release notes with the update/reload recovery path. 5. Record the release URLs and final evidence, then mark TASK-35 Done.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Prepared v0.34.1 with a focused Copilot MCP fix entry in CHANGELOG. `bin/bump-version` synchronized every client manifest, marketplace, guide, and wrapper stamp, and `sync-agent-plugins.py` propagated the canonical templates. Release validation: full suite 641 passed, 4 skipped; adr-doctor passed; generated ADR index checks passed; payload synchronization check and git diff check passed. Live Copilot handshake evidence remains recorded in TASK-34.
<!-- SECTION:NOTES:END -->
