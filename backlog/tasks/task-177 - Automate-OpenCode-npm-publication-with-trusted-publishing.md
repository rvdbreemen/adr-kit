---
id: TASK-177
title: Automate OpenCode npm publication with trusted publishing
status: Done
assignee: []
created_date: '2026-08-17 20:35'
updated_date: '2026-08-17 22:00'
labels:
  - release
  - opencode
  - npm
  - automation
dependencies: []
references:
  - 'https://docs.npmjs.com/trusted-publishers'
  - 'https://docs.npmjs.com/cli/v11/commands/npm-trust'
  - 'https://docs.npmjs.com/creating-and-publishing-scoped-public-packages'
modified_files:
  - .github/workflows/publish-opencode-npm.yml
  - docs/RELEASING.md
  - docs/clients/opencode.md
  - README.md
  - CHANGELOG.md
  - C4-Documentation/c4-component-contracts-and-distribution.md
priority: high
type: chore
ordinal: 21000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add a manually dispatched GitHub Actions workflow that stages the native OpenCode npm package through npm Trusted Publishing/OIDC after release preflight checks. A maintainer reviews and approves the staged package on npm with 2FA before it becomes public. Document the one-time manual bootstrap required because npm trusted publisher relationships and staged publishing require an existing package.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The one-time bootstrap for @rvdbreemen/adr-kit-opencode@0.52.0 is documented and remains a deliberate manual action.
- [x] #2 The workflow validates the selected release tag, package version, release surfaces, generated adapters, ADR index, focused package tests, and npm dry-run before staging.
- [x] #3 The publish job uses npm Trusted Publishing with id-token: write and allow-stage-publish, with no long-lived npm token or GitHub environment approval.
- [x] #4 The workflow stages a public package version, generates trusted-publishing provenance when approved, and refuses already-published versions.
- [x] #5 Release documentation explains npm Trusted Publisher configuration, staged-package review, 2FA approval, and future manual dispatch.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add the staged-publication workflow. 2. Update the release runbook with npm bootstrap, trusted publisher, and staged approval setup. 3. Validate YAML and preflight commands. 4. Open a focused PR for the automation.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Bootstrap completed on 2026-08-17: @rvdbreemen/adr-kit-opencode@0.52.0 was manually published with npm 11.17.0 after 2FA setup. npm dist-tag reports latest=0.52.0, package access is public, and a fresh npm install --dry-run resolves 0.52.0. Manual publishing did not use OIDC provenance; future releases should use staged Trusted Publishing.

The v0.52.0 bootstrap is now live on npm. The workflow design uses npm staged publishing rather than direct publish: CI stages with OIDC, and the maintainer approves the staged package with 2FA.

Validation on 2026-08-17: workflow YAML parsed successfully and Prettier checks passed for the workflow; full C4 and release-document Markdownlint passed with 0 errors; version consistency, adapter drift, ADR index, strict ADR lint, npm registry verification, and 26 focused tests passed.

Review correction on 2026-08-17: npm staged publishing requires npm 11.15.0 or newer, so both workflow jobs pin npm 11.17.0. The staging command also explicitly requests public access.

A read-only npm trust list check was attempted, but npm required browser authentication and 2FA (EOTP); no trusted-publisher relationship was changed or confirmed.

Full pytest run on 2026-08-17 reached 1104 passed and 4 skipped, then failed in the pre-existing live Copilot installer test because the real %USERPROFILE%\\.copilot\\installed-plugins\\rvdbreemen-adr-kit-copilot directory was locked (WinError 5) by an editor. The focused OpenCode tests and all workflow/documentation checks remain green.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Merged PR #106 into main at a40eaeb. Added the manually dispatched npm staged-publishing workflow, pinned npm 11.17.0 for OIDC-compatible staging, documented the v0.52.0 bootstrap and one-time Trusted Publisher setup, and updated OpenCode distribution documentation. All required GitHub checks passed. The npm Trusted Publisher relationship remains an intentional one-time maintainer configuration after merge.
<!-- SECTION:FINAL_SUMMARY:END -->
