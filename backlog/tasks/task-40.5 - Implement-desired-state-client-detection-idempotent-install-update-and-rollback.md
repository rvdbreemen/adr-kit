---
id: TASK-40.5
title: 'Implement detected-client setup, verified updates, and rollback'
status: Done
assignee:
  - Codex
created_date: '2026-07-19 17:51'
updated_date: '2026-07-19 20:47'
labels:
  - installer
  - upgrade
  - rollback
  - idempotency
dependencies:
  - TASK-40.1
  - TASK-40.2
  - TASK-40.4
  - TASK-40.13
modified_files:
  - scripts/install-agent-envs.py
  - scripts/project_setup.py
  - clients/installer/__init__.py
  - clients/installer/contracts.py
  - clients/installer/detection.py
  - clients/installer/native.py
  - clients/installer/payload.py
  - clients/installer/planning.py
  - clients/installer/transaction.py
  - clients/installer/updates.py
  - tests/test_agent_installer.py
  - tests/test_managed_instructions.py
  - INSTALL.md
  - INSTALL-AGENT.md
parent_task_id: TASK-40
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Build a desired-state installer for Claude Code CLI, Codex CLI, and Copilot CLI only. Detection is read-only and shown before changes. Default actions install detected selected native support and project defaults with opt-outs. Install verified stable updates automatically, retain a healthy rollback target, and pause before migrations or breaking changes. Additional clients belong to TASK-43.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Detection reports Claude/Codex/Copilot executable path/version, config overrides, native manager availability, ADR Kit version/source/hash, legacy footprints, disabled/trust state, and duplicate roots without writing.
- [x] #2 Human and JSON plans show detected clients, current state, defaults, opt-outs, migrations, backups, activation, validation, rollback, and removals before mutation.
- [x] #3 Detected Claude, Codex, and Copilot support is selected by default and each can be opted out globally or per project; unknown clients are not modified.
- [x] #4 Prepared payload validation follows ADR-006, uses an absolute Python 3.10+ path, preserves executable modes, validates manifests/version, and proves MCP initialize/list before activation.
- [x] #5 Each client has its own lock and transaction; a failure is isolated and healthy client changes remain accurately reported.
- [x] #6 Matching version/source/trust/MCP/artifact/settings state is a true no-op across repeated runs.
- [x] #7 Verified stable releases update automatically; pinned/offline settings are honored; breaking changes and migrations require confirmation.
- [x] #8 Failed activation or health smoke automatically restores the previous healthy payload/config and preserves diagnostic evidence.
- [x] #9 Uninstall removes only ADR Kit-owned registrations, generated artifacts, managed blocks, caches, and payloads selected for removal; user config and local guidance survive.
- [x] #10 Fixtures cover stale removed-cache launchers, old versions, Windows PowerShell/nvm4w, best-effort POSIX paths/modes, spaces, Unicode, interruption, stale locks, read-only config, and partial failures.
- [x] #11 Each client records its automatic-update trigger and last-check state; checks and activation never run synchronously in startup, prompt, edit, compact, or stop hooks.
- [x] #12 Clients with a safe native update manager use it; others use deferred ADR Kit maintenance outside agent hot paths, with frequency, pin, offline, and opt-out settings.
- [x] #13 Release verification authenticates the approved source and validates payload digest before activation; failure leaves active state unchanged.
- [x] #14 Documentation covers three-client detection/defaults, opt-outs, settings, update verification, breaking-change prompts, rollback, disable, and uninstall.
- [x] #15 Installer defaults are calculated from detected executable/native-manager state plus effective settings; no static `claude,codex` or all-client default installs an absent client unless explicitly requested.
- [x] #16 The measured 991-line `scripts/install-agent-envs.py` baseline is decomposed so the entrypoint is <=300 physical lines and contains orchestration/argument handling only; detection, planning, transactions, client mutations, and rollback live in tested single-responsibility modules.
- [x] #17 Installer support modules target <=400 physical lines; an exception requires a task-recorded reason, responsibility analysis, owner, focused tests, and approval under TASK-40.1.
- [x] #18 Claude, Codex, and Copilot behavior is registry/data-driven; adding a client/event does not create a new installer executable or copy the transaction engine.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Size L, implemented in three convergent slices. First extract read-only registry-driven detection and deterministic human/JSON desired-state planning, including effective settings, legacy/duplicate/trust state, and per-client opt-outs. Second extract prepared payload verification, digest/source authentication, per-client locks, transactions, native-manager operations, health activation, evidence retention, and rollback into single-responsibility modules. Third add verified stable deferred updates, pinned/offline/breaking-migration policy, precise disable/uninstall ownership, interruption/stale-lock fixtures, and documentation. Preserve the current public CLI while reducing install-agent-envs.py to <=300 lines and keeping support modules <=400; stop rather than add another executable, static client default, synchronous hook update, or future-client mutation.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Decomposition baseline confirmed at 991 physical lines. Responsibility map for the first refactor: `clients/installer/contracts.py` owns the three-client registry, immutable state/plan/result models, and command rendering; `detection.py` owns read-only executable/version/config/legacy/trust/duplicate discovery and settings-derived selection; `payload.py` owns source/version/digest verification, allowlisted prepared payloads, Python/runtime/MCP preflight, and mode preservation; `native.py` owns manager-specific list/install/update/disable/remove calls as data-driven operations; `transaction.py` owns per-client locks, backup, activation, health validation, rollback, interruption evidence, and precise owned-state removal; the <=300-line `install-agent-envs.py` remains argument handling, plan display/confirmation, and isolated per-client orchestration. Compatibility re-exports will preserve current tested imports while tests migrate to responsibility modules. No module may import hook code or synchronously check updates from a hook path.

Implemented the first desired-state slice: registry-driven enriched read-only detection (paths/versions/config overrides/prepared roots/legacy footprints/disabled state/digests), stable human/JSON plans with explicit opt-outs and migration confirmation, and per-client lock/evidence/rollback primitives. All three installed CLIs are detected on this Windows machine. The compatibility installer now emits the plan before mutation, honors per-client settings opt-outs, retains the previous prepared payload, and uses isolated client transactions. Remaining before closure: finish module decomposition to the <=300/<=400 line budgets, add authenticated release/update-state and precise uninstall flows, broaden hostile/interruption/read-only fixtures, and update installation docs.

Final verification: `python -m pytest -q` => 699 passed, 4 skipped; simulated three-client certification passed; generator drift check passed; live read-only JSON planning detected Claude Code 2.1.215, Codex 0.144.6, and Copilot CLI 1.0.71. Entrypoint is 300 physical lines; installer support modules range from 54 to 326 lines. The release identity and deterministic payload digest are validated before activation. Native update operations remain outside hooks, honor effective policy/pin/offline state, and record per-client trigger/last-check evidence. Uninstall removes only native ADR Kit registrations, marker-owned payloads, generated guide, and selected instruction blocks while preserving local/user guidance and ADRs.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented the three-client desired-state installer for Claude Code CLI, Codex CLI, and GitHub Copilot CLI. The previous 991-line implementation was decomposed into a 300-line orchestration entrypoint plus registry-driven detection, planning, payload, native-manager, transaction, and update modules, all below the 400-line support-module budget. The installer now emits stable human/JSON plans before mutation, applies detected-client defaults and settings opt-outs, authenticates source identity and payload digests, preflights Python/MCP/hooks, isolates clients with locks and evidence, retains and restores a previous healthy payload, pauses for breaking migrations, records deferred update state, and performs ownership-bounded uninstall. Documentation now covers planning, settings, rollback, updates, disable, and uninstall. Verification: 699 tests passed with 4 expected skips; generator drift and simulated three-client certification both passed.
<!-- SECTION:FINAL_SUMMARY:END -->
