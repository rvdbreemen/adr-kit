---
id: TASK-39
title: Remove KennisBank scope from ADR Kit plugin report
status: Done
assignee: []
created_date: '2026-07-19 17:36'
updated_date: '2026-07-19 17:59'
labels:
  - documentation
  - research
  - scope-correction
dependencies: []
documentation:
  - docs/research/cross-client-plugin-hooks-report.md
  - docs/plans/cross-client-plugin-implementation-plan.md
  - docs/reviews/cross-client-plugin-planning-findings.md
modified_files:
  - docs/research/cross-client-plugin-hooks-report.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Correct the cross-client ADR Kit plugin report so it covers ADR Kit only. Remove KennisBank-specific retrieval, memory, transcript archival, wiki mutation, latency, hard-exit, and lifecycle recommendations, then repair affected conclusions, matrices, phases, and source framing.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The report contains no KennisBank product architecture or KennisBank-specific behavior recommendations.
- [x] #2 ADR Kit hook analysis remains focused on ADR discovery, context injection, deterministic edit enforcement, packaging, installation, updates, and doctor behavior.
- [x] #3 Executive summary, admission gate, capability matrices, phases, optional controls, and conclusions are internally consistent after removal.
- [x] #4 Documentation verification passes and task notes identify what was removed.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Remove KennisBank-specific retrieval, transcript, wiki, hard-exit, and publication content; retain and rename the latency budgets as ADR Kit hook budgets; rewrite lifecycle guidance around ADR orientation, task ranking, edit enforcement, safe no-ops, packaging, install/update/rollback, and doctor; add the official Kilo/Kimi assessment; verify scope and ADR health.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Removed all KennisBank product architecture and behavior from the ADR Kit report. Preserved the latency table with ADR-specific operations and timeout fallbacks. Reclassified client gaps against ADR Kit outcomes rather than memory-capture needs. Added a primary-source Kilo Code review: plugins, skills, Markdown workflows, AGENTS.md, MCP, CLI/VS Code, update/uninstall, 26.4k stars, and current release evidence. Verification: no KennisBank/wiki/memory/distillation terms remain; git diff --check clean; strict ADR lint 9 PASS/0 FAIL; generated indexes current.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Corrected the cross-client research report to be ADR Kit-only. Removed KennisBank retrieval, transcript capture, wiki publication, hard-exit recovery, and memory pipeline material; retained the real latency budgets with ADR-specific SessionStart, prompt ranking, subagent propagation, edit-hook, and safe no-op meanings. Updated support analysis for ADR Kit's actual outcomes and added a complete official Kilo Code assessment plus Kimi documentation root. Repository ADR lint and index checks pass.
<!-- SECTION:FINAL_SUMMARY:END -->
