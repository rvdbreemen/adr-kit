---
id: TASK-40.7
title: Coordinate native normalization and three-client certification
status: In Progress
assignee:
  - Codex
created_date: '2026-07-19 17:51'
updated_date: '2026-07-19 23:17'
labels:
  - claude
  - codex
  - copilot
  - regression
dependencies:
  - TASK-40.2
  - TASK-40.3
  - TASK-40.4
  - TASK-40.5
  - TASK-40.6
  - TASK-40.13
modified_files:
  - .claude-plugin/
  - hooks/
  - codex/
  - copilot/
  - clients/
  - packaging/
  - tests/fixtures/claude/
  - tests/fixtures/codex/
  - tests/fixtures/copilot/
  - tests/certification/
  - docs/clients/
  - README.md
  - INSTALL.md
parent_task_id: TASK-40
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Coordinate first-class native delivery for Claude Code CLI, Codex CLI, and Copilot CLI after the shared canonical, settings, installer, doctor, hook, and certification foundations exist. The three child tasks own client-specific normalization and certification independently. This parent owns cross-client consistency, regression compatibility, aggregate documentation, and completion only after all children pass.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 All existing public skills, commands/prompts, and MCP tool names remain discoverable or have explicitly approved migration aliases across Claude, Codex, and Copilot.
- [x] #2 The child tasks use one canonical semantic workflow and shared settings/install/update/rollback/doctor contracts without client-specific ADR engine forks.
- [x] #3 Native event differences and permitted degradations are recorded in the capability registry and support documentation; exact event-name parity is not claimed.
- [x] #4 Copilot PreToolUse limitations, Codex trust/review and stale-cache behavior, and Claude plugin lifecycle behavior are represented honestly in one outcome matrix.
- [x] #5 Windows and POSIX wrappers preserve fail-open semantics and absolute prepared-payload resolution.
- [x] #6 Shared fixtures cover generated drift, version skew, old layouts, settings precedence, missing optional hooks, and user-owned config preservation.
- [x] #7 No client logic outside Claude, Codex, and Copilot enters TASK-40 packages.
- [x] #8 TASK-40.7.1, TASK-40.7.2, and TASK-40.7.3 each provide passing independent Windows native certification and documented best-effort macOS/Linux status.
- [ ] #9 The aggregate support matrix contains only the three clients and the all-three release gate passes.
- [x] #10 The complete ADR Kit regression suite passes after all three child tasks complete.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Program container, not a separately blocking implementation task. Begin after TASK-40.2/.3/.4/.5/.6/.13 foundations. Execute the three child tasks independently; route shared defects back to the owning foundation task rather than copying fixes. Reconcile public names, outcome/degradation documentation, and aggregate regression evidence after each child. Mark this parent Done only after all three children and the all-three release gate pass.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started after all shared foundations completed. Native documentation was revalidated on 2026-07-19 before changing layouts: Claude components live at plugin root, Codex plugin hooks default to `hooks/hooks.json`, and Copilot uses root `plugin.json`/`hooks.json` with lower-camel events and separate bash/PowerShell commands.

All three native child certifications are complete and independently evidenced on Windows. Aggregate release promotion remains deliberately open at AC #9: the current working tree is not a clean commit-bound release candidate, so ADR-010 stays Proposed and the all-three release gate must not be bypassed. Atomic generation was retained while meeting the Windows performance gate.

All three native child tasks are Done with independent Windows smoke records, macOS/Linux not-run reasons, native package fixtures, and exact prepared payload SHA-256 7c81f71393fcdf89641d633568e6df340270ea57e72f4f6d7c5d570c0a212635. Aggregate regression: 740 passed, 6 skipped. Criterion #9 remains intentionally unchecked: the support matrix is limited to the three clients, but the release-candidate gate cannot pass until these working-tree changes are committed and native evidence is regenerated against that exact clean commit.

Final atomic-write evidence supersedes earlier generator measurements: clean p50 880.576 ms / p95 1039.0 ms; warm p50 61.078 ms / p95 88.265 ms; zero warm rewrites; payload SHA-256 7c81f71393fcdf89641d633568e6df340270ea57e72f4f6d7c5d570c0a212635.

Temporary candidate packaging preflight passed without touching the real index: all native hook launchers are 100755, git diff --check is clean, and tests/test_packaging_contract.py reports 3 passed / 1 platform skip. Current payload SHA-256 is 1bae71baf4b4b460064408235dd083e33fc5f2c2e6371095da82330b6b3dd7b9.

Aggregate certification hardening 2026-07-20: native observations now have a deterministic assembler into the release schema, and release-candidate CI consumes a separately pinned evidence commit to avoid candidate/evidence hash self-reference. The certified three-client matrix and gate receipt are generated only after validation and uploaded as retained artifacts; the candidate's conservative simulated matrix is not falsely promoted.

Current final working-tree evidence: 746 passed, 6 skipped; generator clean p50/p95 713.408/735.485 ms, warm p50/p95 34.965/60.974 ms, zero warm writes; prepared payload SHA-256 6a7fc1bddcf64bd25b6b9e90d7a1d93aae180b2a0d9ae2fad6d658c0ef8e673a; prepared MCP and Claude hook smoke pass. AC #9 remains open because the all-three gate correctly rejects dirty records and requires a maintainer-authorized commit followed by clean commit-bound native reruns.
<!-- SECTION:NOTES:END -->
