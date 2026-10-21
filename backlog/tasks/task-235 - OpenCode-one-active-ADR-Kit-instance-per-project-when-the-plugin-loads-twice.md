---
id: TASK-235
title: 'OpenCode: one active ADR Kit instance per project when the plugin loads twice'
status: Done
assignee: []
created_date: '2026-10-12 04:47'
updated_date: '2026-10-12 05:03'
labels:
  - opencode bug
dependencies: []
priority: medium
ordinal: 78000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A global npm entry plus a project entry (file:// or local path) load two plugin instances; OpenCode dedupes only by npm package name. Measured on 2026-10-12 in the adr-kit checkout: two hook processes per prompt, skills path and kit ADR-guide listed twice, and the first-loaded (global npm) instance owns the adr-kit MCP server and /adr-kit-* commands, so the working tree is not dogfooded. Fix: a process-wide registry per project directory; the last-loaded instance wins (mirrors OpenCode's own local-over-global dedupe), all others no-op config and hooks. Versions <= 0.60.0 carry no guard, so a mixed pair still double-loads until both sides have it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Two instances for one directory: only the last-loaded registers config and runs hooks
- [x] #2 Disposing the active instance hands over to the remaining one
- [x] #3 Instances for different directories stay independent
- [x] #4 docs/clients/opencode.md documents the behaviour
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
plugin.ts keeps a process-wide registry per project directory (Symbol.for); the last-loaded copy is active and the rest no-op config and hooks; dispose hands over. Reproduced first: in the adr-kit checkout with the global npm entry, opencode debug config listed two skills paths and the npm copy owned MCP and commands; a two-instance harness counted two hook spawns per prompt. New bun test fails without the guard and passes with it. Full suite in four parts green; two guardian-entry tests fail only when PowerShell's PATH puts WSL bash first, also on clean dev.
<!-- SECTION:FINAL_SUMMARY:END -->
