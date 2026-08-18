---
id: TASK-178
title: Integrate OpenCode npm staging into release workflow
status: In Progress
assignee: []
created_date: '2026-08-18 05:34'
updated_date: '2026-08-18 05:43'
labels:
  - release opencode npm automation
dependencies: []
modified_files:
  - .github/workflows/release-publish.yml
  - .github/workflows/publish-opencode-npm.yml
  - docs/RELEASING.md
  - docs/clients/opencode.md
  - README.md
  - CHANGELOG.md
  - C4-Documentation/c4-component-contracts-and-distribution.md
  - C4-Documentation/c4-context.md
  - C4-Documentation/c4-container.md
  - CONTRIBUTING.md
  - .claude/commands/release-adr-kit.md
  - >-
    docs/adr/ADR-012-release-to-the-three-coding-agent-marketplaces-from-the-public-repository.md
  - backlog/tasks/task-176 - Release-v0.52.0-with-native-OpenCode-support.md
priority: high
type: chore
ordinal: 22000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make the canonical release workflow invoke the OpenCode npm staged-publication flow after the GitHub Release is created, while keeping npm Trusted Publishing and maintainer 2FA approval as the final publication boundary. Update all release documentation and Trusted Publisher instructions to describe the integrated flow.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 release-publish.yml calls the OpenCode npm staging workflow after GitHub Release creation for both tag pushes and manual release dispatch.
- [ ] #2 The reusable npm workflow keeps preflight gates, refuses already-published versions, uses npm Trusted Publishing with npm 11.17.0, and stages a public package without a long-lived token.
- [ ] #3 Documentation identifies release-publish.yml as the Trusted Publisher workflow and explains the one-time npm setup and final staged-package 2FA approval.
- [ ] #4 The workflow remains outside the certified three-client capability and native certification gate.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Convert the OpenCode npm workflow into a reusable workflow callable by release-publish.yml. 2. Add the reusable staging job to the canonical release workflow with id-token: write. 3. Update runbooks, client docs, README, changelog, and C4 distribution documentation. 4. Validate workflow structure, release gates, Markdown, tests, and branch sync.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
TASK-177 delivered a standalone workflow, but the repository default branch is dev and the canonical release flow did not invoke it. This follow-up integrates the staging flow into release-publish.yml.

Integrated the reusable OpenCode npm staging workflow into release-publish.yml. The canonical release workflow now stages the package after creating the GitHub Release for both tag pushes and manual dispatch; Trusted Publisher configuration must reference release-publish.yml.

Corrected TASK-176 historical release notes to record the later v0.52.0 npm bootstrap and integrated staging flow.

Validation on 2026-08-18: reusable workflow structure parsed successfully; Prettier passed for both workflows; Markdownlint passed with 0 errors across all changed documentation; release-version, adapter, ADR index, strict ADR lint, and branch-sync checks passed; 48 documentation/version/OpenCode tests passed.
<!-- SECTION:NOTES:END -->
