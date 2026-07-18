---
id: TASK-24
title: Ship native Codex integration and multi-CLI installer
status: Done
assignee: []
created_date: '2026-07-18 11:30'
updated_date: '2026-07-18 12:18'
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
- [x] #9 Version, changelog, release notes, PR, merge, tag, and GitHub release are completed only after validation
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
Implementation, validation, merge, and release completed on 2026-07-18. Claude Code 2.1.214, Codex 0.144.5, and Copilot CLI 1.0.70 each passed isolated native installation and plugin/MCP discovery. The separate Codex and Copilot payloads do not change the Claude Code manifest, skills, agent, or three-hook contract. Final local suite: 524 passed, 3 skipped. All five PR checks and all three post-merge main workflows passed. Merge commit: d2542d3fe6367f7bc0a7cd9af9ee6f3944c18775. Release tag and URL: v0.33.0, https://github.com/rvdbreemen/adr-kit/releases/tag/v0.33.0.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Released ADR Kit v0.33.0. Added separate native Codex and standalone Copilot CLI distributions, verified multi-CLI detection/installation, workspace-aware MCP tools, and cross-client hook cache resolution while preserving the Claude Code plugin contract. Validation: 524 passed, 3 skipped locally; all PR and post-merge GitHub checks passed. PR: https://github.com/rvdbreemen/adr-kit/pull/14. Release: https://github.com/rvdbreemen/adr-kit/releases/tag/v0.33.0.
<!-- SECTION:FINAL_SUMMARY:END -->
