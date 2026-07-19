---
id: TASK-36
title: Quiet three-client integrations and publish patch release
status: Done
assignee:
  - Codex
created_date: '2026-07-19 10:55'
updated_date: '2026-07-19 11:35'
labels:
  - hooks
  - claude
  - codex
  - copilot
  - documentation
  - release
dependencies: []
documentation:
  - README.md
  - INSTALL.md
  - INSTALL-AGENT.md
  - CONTRIBUTING.md
modified_files:
  - .claude-plugin/hooks/session-start
  - .claude-plugin/marketplace.json
  - .claude-plugin/plugin.json
  - .githooks/pre-commit
  - .github/plugin/marketplace.json
  - CHANGELOG.md
  - CONTRIBUTING.md
  - INSTALL-AGENT.md
  - INSTALL.md
  - MIGRATING-FROM-ADR-SKILL.md
  - README.md
  - bin/adr-guardian
  - bin/adr-watch
  - codex
  - copilot
  - docs/research/2026-06-12-adr-landscape.md
  - instructions/adr.coding.md
  - skills/install-hooks/SKILL.md
  - templates
  - tests
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make ADR Kit's Claude Code, Codex, and GitHub Copilot integrations quiet on successful background activity while preserving model-only architectural context and actionable warnings/blocks. Standardize shipped skill descriptions in English, remove unsupported-client references from active product surfaces, update agent-first documentation for the three supported clients, add regression coverage, and publish the result as a patch release.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 All shipped ADR Kit skill descriptions are valid English metadata and synchronized across Claude Code, Codex, and Copilot payloads.
- [x] #2 Claude Code hook envelopes use model-only additionalContext with maximum supported output suppression; routine success status messages are removed while actionable warnings and blocking decisions remain visible.
- [x] #3 Codex and Copilot integrations remain silent on routine success and expose no unnecessary lifecycle output; MCP and skill behavior remains functional.
- [x] #4 Active README, install guides, manifests, instructions, and runtime compatibility code describe only Claude Code, Codex, and GitHub Copilot; unsupported-client product references are removed.
- [x] #5 Regression tests cover quiet hook envelopes, English skill descriptions, three-client documentation, synchronized payloads, and absence of unsupported-client references.
- [x] #6 Focused and complete repository validation pass on Windows, with existing cross-platform CI green.
- [x] #7 A patch version is merged to main through a pull request, tagged on the merged commit, and published as a GitHub Release with upgrade instructions.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Audit the canonical Claude Code skills and synchronized Codex/Copilot payloads for English metadata and current three-client integration contracts. 2. Update Claude Code hook JSON envelopes to add suppressOutput while retaining hookSpecificOutput.additionalContext, remove routine statusMessage fields, and remove obsolete unsupported-client output branches. Keep Codex/Copilot routine paths silent and validate MCP/skills. 3. Remove unsupported-client product references from active documentation, manifests, instructions, runtime compatibility code, and relevant historical documentation where it advertises support; update README/INSTALL/INSTALL-AGENT around Claude Code, Codex, and GitHub Copilot. 4. Add deterministic regression tests for English skill descriptions, quiet hook output, three-client documentation, synchronized distributions, and product-reference removal. 5. Run focused tests, sync generated client payloads, run the full suite and release checks. 6. Bump to the next patch version, push an agent branch, merge a green PR to main, tag the merged release commit, publish GitHub Release notes, and record final evidence in TASK-36.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented quiet Claude hook envelopes (`suppressOutput` plus model-only `additionalContext`), removed routine status messages and the obsolete client-specific branch, synchronized Codex/Copilot payloads, verified English metadata, updated README/install/docs for Claude Code, Codex, and Copilot, and removed obsolete product references. Focused and exact CI slices pass (145 focused; 77 passed/2 skipped CI slice; 55 passed/1 skipped compatibility slice). Full local suite reached 643 passed/4 skipped with one timing-only 500 ms assertion at 614 ms under concurrent load; the same test passed alone at 290 ms. Release/PR and remote CI remain pending.

Remote PR #18 was green across validate, Python 3.10/3.12 on Ubuntu/macOS/Windows, ADR enforcement, ADR index freshness, pytest, and lint smoke checks. Merged commit: 8d4177aff890308703dbd8accee5fb8cc3bc63d4. Release: https://github.com/rvdbreemen/adr-kit/releases/tag/v0.34.2.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Released ADR Kit v0.34.2. Claude Code hook context now uses `suppressOutput` without routine progress labels; Codex and GitHub Copilot CLI remain quiet through native skills/MCP; all 42 distributed skill descriptions are covered by English metadata checks; documentation leads with the three integrations and obsolete client references are removed. Focused tests, CI slices, all six Python/OS matrix jobs, packaging checks, ADR index freshness, and enforcement checks passed. PR #18 merged as 8d4177a; annotated tag v0.34.2 and the public GitHub Release were published with upgrade instructions.
<!-- SECTION:FINAL_SUMMARY:END -->
