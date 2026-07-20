---
id: TASK-42
title: 'Narrow active ADR Kit client scope to Claude, Codex, and Copilot'
status: Done
assignee:
  - Codex
created_date: '2026-07-19 19:00'
updated_date: '2026-07-19 19:07'
labels:
  - planning
  - scope
  - cross-client
dependencies: []
documentation:
  - docs/plans/cross-client-plugin-implementation-plan.md
  - docs/reviews/cross-client-plugin-planning-findings.md
  - docs/research/cross-client-plugin-hooks-report.md
modified_files:
  - docs/research/cross-client-plugin-hooks-report.md
  - docs/plans/cross-client-plugin-implementation-plan.md
  - docs/reviews/cross-client-plugin-planning-findings.md
priority: high
ordinal: 42000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Revise the approved implementation program so active TASK-40 scope contains only Claude Code CLI, Codex CLI, and GitHub Copilot CLI. Move generic portability and every additional client or IDE surface to separate future TASK-43. Preserve only shared skills, prompts, instructions, MCP, hooks, installer, doctor, and certification work required by the three active clients. Do not start implementation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 TASK-40 names only Claude Code CLI, Codex CLI, and Copilot CLI as active client scope.
- [x] #2 TASK-40.8 and TASK-40.9 are archived with explicit transfer to TASK-43 and no active TASK-40 work order depends on them.
- [x] #3 Retained TASK-40 work orders contain no deliverable, test cadence, installer default, doctor claim, or release requirement for any client beyond Claude, Codex, and Copilot.
- [x] #4 Shared artifacts remain in TASK-40 only when they directly serve Claude, Codex, or Copilot.
- [x] #5 TASK-43 preserves generic portability and all wider client support as a low-priority future epic with an explicit activation/revalidation gate and no dependency on TASK-40.
- [x] #6 The durable plan separates current three-client implementation from future TASK-43 and assigns no future client to the current release promise.
- [x] #7 The findings document records the scope correction and transfer to TASK-43.
- [x] #8 The active TASK-40 dependency graph is acyclic and contains no dependency on an archived or future-expansion task.
- [x] #9 Strict ADR lint, ADR index check, whitespace checks, and scope scans pass.
- [x] #10 TASK-40 and retained implementation tasks remain To Do; TASK-43 remains future To Do; no implementation work starts.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Create future TASK-43 to preserve generic and all wider client support behind explicit later activation. 2. Remove active generic/future-client commitments from the durable plan. 3. Revise TASK-40 and every retained work order so artifacts and lifecycle behavior serve only Claude, Codex, and Copilot. 4. Add transfer comments to TASK-40.8/.9 and archive them. 5. Append the scope correction to the findings. 6. Audit the current graph and run ADR/index/whitespace/scope verification. 7. Finalize TASK-42 without starting implementation.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Created low-priority future TASK-43 to preserve generic portability and every client/surface beyond Claude, Codex, and Copilot behind explicit activation and evidence refresh. Rewrote TASK-40, TASK-40.1/.2/.3/.4/.5/.7/.13 and the durable plan so current artifacts, installer, doctor, hooks, certification, documentation, and release gating serve only the three selected CLIs. Archived TASK-40.8/.9 with transfer comments; TASK-40.10/.11/.12/.14 were already archived. Updated the broad research report to state that wider classifications are future evidence, not current implementation authority, and recorded the final correction in the findings. Verification passed: TASK-40 has 12 active work orders, an acyclic graph, and internal dependencies only; active titles and modified-file metadata contain no future-client work; strict ADR lint passed 9/9 with zero findings; ADR index changed=False; git diff --check and trailing-whitespace checks passed. No implementation started.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Narrowed the current ADR Kit program to Claude Code CLI, Codex CLI, and GitHub Copilot CLI only. Removed generic and additional-client work from TASK-40, archived TASK-40.8/.9, and created independent low-priority TASK-43 to preserve the complete wider roadmap for later explicit activation and revalidation. Rewrote the implementation plan, findings, research disposition, epic, and retained work orders so no future client affects current installation, doctor, hooks, certification, documentation, or release gating. All graph and repository checks pass; TASK-40 remains To Do.
<!-- SECTION:FINAL_SUMMARY:END -->
