---
id: TASK-46
title: Complete public ADR Grilling user documentation
status: Done
assignee: []
created_date: '2026-07-20 23:11'
updated_date: '2026-07-21 05:39'
labels:
  - documentation
  - adr-grilling
  - follow-up
milestone: ADR Grilling
dependencies:
  - TASK-45
documentation:
  - README.md
  - INSTALL.md
  - docs/feature-adr-grilling/README.md
  - docs/feature-adr-grilling/07-final-certification.md
  - docs/adr-grilling.md
  - CHANGELOG.md
  - docs/clients/claude.md
  - docs/clients/codex.md
  - docs/clients/copilot.md
  - .github/release-notes-0.37.0.md
modified_files:
  - docs/adr-grilling.md
  - README.md
  - INSTALL.md
  - CHANGELOG.md
  - docs/feature-adr-grilling/README.md
  - docs/clients/claude.md
  - docs/clients/codex.md
  - docs/clients/copilot.md
  - packaging/public-artifacts.json
  - .github/release-notes-0.37.0.md
priority: high
ordinal: 47500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Audit and update the public ADR Kit documentation after TASK-45 so engineers can discover and use grill, readiness, guardian queue, CI readiness, Proposed-to-Accepted lifecycle, and the auto-to-assist migration without relying on the internal implementation dossier.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Public command documentation includes runnable examples for grill, readiness, guardian queue, and CI readiness.
- [x] #2 The Proposed-to-Accepted workflow and human confirmation boundary are explicit.
- [x] #3 Upgrade and compatibility guidance documents the implicit auto-to-assist default change and explicit auto opt-in.
- [x] #4 All updated Markdown and documentation contract tests pass.
- [x] #5 A versioned ADR Grilling release message summarizes user value, compatibility, upgrade impact, verification evidence, and installation guidance.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Audit the published user documentation, derive the next minor release message from the accepted ADR Grilling contracts and measured evidence, mark candidate-only claims honestly, and validate Markdown plus documentation and release allowlist contracts.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added `docs/adr-grilling.md` as the public workflow guide with runnable examples for subject creation, PR/range and source reconstruction, resumable Proposed ADRs, readiness CLI/MCP, guardian cache, explicit accept/reject/supersede outcomes, shipped-code assist mode, and local/GitHub CI readiness.

Corrected INSTALL from the old four-tool MCP list to the complete five-tool contract including `adr_readiness`; added grill discovery and cross-links from README, INSTALL, CHANGELOG, the feature dossier, and all three native client pages. Added the guide to the public release allowlist.

Validated CLI syntax directly with `adr new --help`, `adr accept --help`, `adr reject --help`, `adr supersede --help`, `adr document --help`, `adr-readiness --help`, `adr-readiness-ci --help`, and guardian refresh help. Corrected the supersede example to require `--by`.

Validation: markdownlint-cli2 checked 16 public Markdown files with 0 issues; documentation/release-allowlist/packaging suite passed 21 tests with 3 environment-dependent skips; the broader first slice passed 30 with 3 skips; client generation remained changed=0/written=0; scoped `git diff --check` passed.

Reopened for the requested versioned release-message follow-up. The message will target proposed minor version v0.37.0 without bumping manifests or publishing a release.

Prepared .github/release-notes-0.37.0.md using the repository versioned release-note convention. The draft covers user value, 15-workflow client parity, readiness, guardian and CI behavior, the human acceptance boundary, runnable onboarding, auto-to-assist compatibility, performance, and supporting documentation.

Release readiness caveat: GitHub Actions run 29801952516 failed the same two packaging-mode tests in all six Python and OS jobs because nine new direct entrypoints were committed as Git mode 100644 instead of 100755. The draft is visibly marked release candidate and must not be published until that separate repository fix and a green matrix.

Validation: markdownlint-cli2 passed 5 release and public documentation files with 0 issues; tests/test_documentation_contracts.py plus tests/test_release_allowlist.py passed 20 tests; git diff --check passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Completed the public ADR Grilling documentation and prepared the proposed v0.37.0 release message. The message is grounded in implemented behavior and local certification evidence, includes upgrade and compatibility guidance, and is explicitly marked as a release candidate because the pushed cross-platform matrix exposed missing executable Git modes on the new entrypoints. No manifest version was bumped and no GitHub release was published.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Modified files, validation commands, and results are recorded in Backlog.
<!-- DOD:END -->
