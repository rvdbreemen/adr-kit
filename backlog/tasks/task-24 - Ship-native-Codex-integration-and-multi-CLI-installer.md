---
id: TASK-24
title: Ship native Codex integration and multi-CLI installer
status: In Progress
assignee: []
created_date: '2026-07-18 11:30'
updated_date: '2026-07-18 12:13'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement a first-class, additive Codex integration for ADR-kit and a cross-platform installer that detects actual Claude Code, Codex, and standalone GitHub Copilot CLI executables and installs the correct native integration for every detected client. Preserve the existing Claude Code plugin contract. After all automated and live validation passes, update documentation and release metadata, merge, tag, and publish the release.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Valid separate .codex-plugin manifest, Codex-native skills, and key-free MCP integration use shared ADR-kit engines without Claude cache paths
- [x] #2 Existing Claude Code plugin behavior and manifests remain compatible and pass regression tests
- [x] #3 Installer detects real Claude Code, Codex, and standalone GitHub Copilot CLI executables and installs every detected client idempotently
- [x] #4 Installer tests cover dry-run, explicit selection, missing clients, repeat runs, paths with spaces, and Windows executable resolution
- [x] #5 README and installation documentation explain native commands, detection, explicit selection, upgrade, and validation
- [x] #6 Official Codex plugin validator plus a live Codex process discover ADR-kit skills and MCP tools
- [x] #7 Claude Code and Copilot integrations receive live smoke validation without overwriting unmanaged configuration
- [x] #8 Focused tests, full test suite, manifests, ADR gates, and install smokes all pass before merge
- [ ] #9 Version, changelog, release notes, PR, merge, tag, and GitHub release are completed only after validation
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Snapshot the existing Claude manifests and behavior and add no-regression coverage.
2. Scaffold a separate Codex plugin, Codex-native skills, and MCP configuration that reuse the shared bin engines.
3. Implement a stdlib-first cross-platform installer with actual CLI detection, client-specific installation, validation, and safe config merging.
4. Add automated installer/plugin tests and live smoke tests for every detected local CLI.
5. Update README, installation docs, changelog, version metadata, and release text.
6. Commit on a feature branch, push, open a PR, wait for all checks, merge, tag, and publish the GitHub release.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan approved by the user's explicit implementation, testing, merge, and release instructions on 2026-07-18. Release is gated on all automated and live client validations passing.

Implementation and validation are complete for the separate Codex and Copilot distributions without changing the Claude Code plugin contract. Claude Code 2.1.214, Codex 0.144.5, and Copilot CLI 1.0.70 were detected by verified version signatures and each passed an isolated clean-home native plugin install plus plugin/MCP discovery.

Final release-gate evidence: full pytest suite 524 passed, 3 skipped in 137.12s; focused cross-client regressions 44 passed, 1 platform skip; official Codex plugin validator PASS; Git Bash hook resolution from isolated Codex and Copilot caches PASS; Markdown lint 0 issues; strict ADR lint 4 PASS/0 advisory/0 fail; adr-index clean; adr-doctor 0 findings; payload drift, JSON syntax, version lockstep, and git diff checks PASS. PR, merge, tag, and GitHub release remain pending.
<!-- SECTION:NOTES:END -->
