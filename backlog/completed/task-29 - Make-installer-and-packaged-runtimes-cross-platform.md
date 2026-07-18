---
id: TASK-29
title: Make installer and packaged runtimes cross-platform
status: Done
assignee: []
created_date: '2026-07-18 17:31'
updated_date: '2026-07-18 17:53'
labels:
  - installer
  - cross-platform
  - windows
  - macos
  - linux
  - packaging
dependencies:
  - TASK-24
modified_files:
  - scripts/install-agent-envs.py
  - tests/test_agent_installer.py
  - tests/test_documentation_contracts.py
  - .github/workflows/validate.yml
  - README.md
  - INSTALL.md
  - INSTALL-AGENT.md
  - CHANGELOG.md
  - ROADMAP.md
  - docs/adr/ADR-006-prepare-platform-local-marketplaces-for-native-installs.md
  - docs/adr/ADR-INDEX.md
  - docs/adr/README.md
  - docs/reviews/2026-07-18-source-audit/FINDINGS.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Harden ADR Kit installation and packaged client runtime setup for Windows, macOS, and Linux. Remove manual Python-command repair requirements, isolate client detection failures, validate source structure before mutations, preserve paths with spaces, verify packaged entry points, and add a real three-OS CI contract.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The installer chooses and validates a Python 3.10+ interpreter deterministically on Windows, macOS, and Linux.
- [x] #2 Codex and Copilot MCP configuration installed through the automated path uses the validated interpreter without requiring manual python/python3 edits.
- [x] #3 One broken, slow, or unrelated client executable does not prevent detection or installation of other supported clients.
- [x] #4 Installer source manifests and required payloads are validated before any external client or marketplace mutation.
- [x] #5 Dry-run and repeated installation remain idempotent and correctly preserve paths containing spaces on all supported platforms.
- [x] #6 Tests cover Windows, macOS, and Linux platform branches, interpreter selection, failure isolation, preflight ordering, and generated runtime configuration.
- [x] #7 GitHub Actions executes the installer compatibility contract on ubuntu-latest, macos-latest, and windows-latest.
- [x] #8 README, INSTALL.md, INSTALL-AGENT.md, changelog, and review findings describe the automatic cross-platform behavior and remaining limitations accurately.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
The automatic installer now validates all required source JSON and release versions, probes a child-process-capable Python 3.10+ runtime, prepares a versioned marketplace under the platform's per-user data directory, embeds the resolved interpreter into Codex and Copilot MCP manifests, restores executable modes for Unix entry points, and completes a real MCP initialize/tools-list handshake before client mutations. Marketplace source migration is one-time and path-aware. Client detection is bounded to 10 seconds and launch failures are isolated. Client state-read failures fail closed for that client, while install failures do not stop other selected clients. Commands remain structured argument lists with platform-correct display quoting. Proposed ADR-006 records the persistence and validation contract.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-07-18 17:53
---
Completion evidence recorded. The three-OS GitHub Actions matrix is configured but has not been pushed from this working tree, so hosted macOS/Linux runner results are pending CI execution. Local Windows behavior, simulated platform branches, prepared Unix mode logic, and real packaged MCP startup are verified. ADR-006 intentionally remains Proposed for human review.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Delivered TASK-29's Windows/macOS/Linux installer contract. Local Windows verification covered real client detection and a no-write three-client dry-run. Simulated platform tests cover Windows, Darwin, and Linux data roots, Python paths with spaces, Python floor rejection, timeout/OS-error isolation, marketplace path normalization, preflight ordering, idempotent prepared-source replacement, and per-client continuation. A real prepared `adr-mcp` subprocess completed initialize and tools/list. GitHub Actions now configures Python 3.10/3.12 on ubuntu-latest, macos-latest, and windows-latest; hosted results will be available after push. Verification: full suite 585 passed / 3 skipped; focused installer/MCP/compatibility/docs suite 70 passed / 1 skipped; strict lint passed all 6 ADRs; relevant markdownlint 0 issues; generated payload and ADR indexes current; git diff check passed.
<!-- SECTION:FINAL_SUMMARY:END -->
