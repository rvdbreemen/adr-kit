---
id: TASK-40.6
title: Build fast/deep ADR Kit doctor with bounded repair
status: Done
assignee:
  - '@Codex'
created_date: '2026-07-19 17:51'
updated_date: '2026-07-19 21:08'
labels:
  - doctor
  - diagnostics
  - health
dependencies:
  - TASK-40.1
  - TASK-40.5
  - TASK-40.13
modified_files:
  - bin/adr-doctor
  - bin/adr_doctor_core.py
  - bin/adr_doctor_checks.py
  - bin/adr_doctor_models.py
  - bin/adr_doctor_probes.py
  - scripts/project_setup.py
  - schemas/doctor-output.schema.json
  - tests/test_adr_doctor.py
  - tests/test_client_doctor.py
  - tests/test_managed_instructions.py
  - TROUBLESHOOTING.md
  - README.md
  - codex/bin/adr-doctor
  - codex/bin/adr_doctor_core.py
  - codex/bin/adr_doctor_checks.py
  - codex/bin/adr_doctor_models.py
  - codex/bin/adr_doctor_probes.py
  - codex/schemas/doctor-output.schema.json
  - copilot/bin/adr-doctor
  - copilot/bin/adr_doctor_core.py
  - copilot/bin/adr_doctor_checks.py
  - copilot/bin/adr_doctor_models.py
  - copilot/bin/adr_doctor_probes.py
  - copilot/schemas/doctor-output.schema.json
parent_task_id: TASK-40
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extend `adr-doctor` across common ADR Kit state and the three native clients. Default doctor is fast and local. `--deep` provides the bounded native/MCP probe framework; hook and latency probe integration is completed by TASK-40.3 after the hook core exists. Both modes automatically repair only safe deterministic ADR Kit-owned issues unless `--check` disables repair; `--fix` additionally permits backups, configuration rewrites, managed-block replacement, and native plugin re-registration. User-owned state remains outside all automatic repair.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Human output gives a concise overall and per-client status; versioned JSON provides stable status, evidence, repair, degradation, and action fields.
- [x] #2 Fast mode avoids login, model invocation, native agent turns, and long benchmarks while checking paths, versions, ranked roots, generated drift, settings, indexes, guide/markers, registrations, and obvious MCP/hook wiring.
- [x] #3 Deep mode provides bounded native list/debug and MCP initialize/list/call probes plus a versioned extension contract that TASK-40.3 can use for hook fixtures and latency samples without changing doctor output semantics.
- [x] #4 Both modes may automatically repair only enumerated safe deterministic ADR Kit-owned state, report every repair, and remain idempotent; `--check` performs the same diagnosis without repair and returns automation-friendly status.
- [x] #5 `--fix` creates backups before config rewrites, managed-block replacement, or plugin re-registration and reports rollback/recovery instructions.
- [x] #6 No mode changes unrelated keys, content outside markers, `.adr-kit/ADR-guide.local.md`, arbitrary user files, secrets, or non-ADR Kit plugin state.
- [x] #7 Doctor follows launchers and resolved commands to their actual target; a current manifest pointing at a removed old cache is FAIL and has a regression fixture.
- [x] #8 Client failures are isolated and statuses distinguish healthy, repaired, degraded, disabled, trust/review pending, stale, unsupported, and failed.
- [x] #9 The deep-probe contract carries benchmark method ID, cold/warm state, sample count, p50/p95/max, reference fixture, and budget fields even before hook measurements are populated.
- [x] #10 Documented native degradations are advisory only when allowed by the registry; missing required first-class outcomes are failures.
- [x] #11 Actions identify exact owned file/command/version and safe repair choice without exposing tokens or full user config.
- [x] #12 Tests snapshot user-owned/config state before and after --check, automatic-safe-repair, and --fix scenarios.
- [x] #13 The measured 282-line `bin/adr-doctor` entrypoint stays <=300 physical lines; new client, model, repair, and deep-probe logic is implemented in single-responsibility tested modules targeting <=400 lines.
- [x] #14 Fast doctor validates model settings and cached/recent reachability evidence without invoking a model; deep doctor performs a bounded live provider/model identity and minimal health probe.
- [x] #15 Missing provider, nonexistent model tag, ambiguous discovery, unreachable backend, and rejected probe are distinct degraded states with exact settings/repair actions; optional judgment never disappears behind a healthy summary.
- [x] #16 Fast health isolation remains independent from sweep, index rebuild, certification, or other broad maintenance work.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Size L. First reproduce and diagnose the actual current-manifest-to-removed-cache launcher class on Windows, then add fast common checks, JSON schema, and `--check`. Enumerate safe automatic repairs in code and documentation before enabling them. Add --fix transactional rewrites and the bounded deep native/MCP extension contract. TASK-40.3 later plugs hook/latency probes into that contract. Stop and report when ownership is uncertain.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Starting after TASK-40.5 completed and the full suite passed. The approved plan remains current: preserve the <=300-line adr-doctor entrypoint, extract versioned models/checks, implement fast local diagnostics and bounded safe repair first, then add deep native/MCP/model probes and the TASK-40.3 extension contract.

Completed fast/deep doctor implementation. Fast mode performs local ADR/index, generated adapter, settings, guide/marker, native identity, MCP launcher, and cached model-health checks without login/model turns. Default mode repairs only enumerated owned generated drift; --check is read-only; --fix uses project_setup backups before managed guide/instruction changes. Deep mode adds bounded native plugin-list, MCP initialize/tools-list/adr_status, and Ollama identity/show probes plus the versioned latency extension for TASK-40.3. Live Windows evidence: MCP deep probe healthy; local judgment reported ambiguous-discovery; Claude native listing reported trust-pending; Codex and Copilot registration probes healthy. Full verification: 709 passed, 4 skipped; generator check, strict ADR lint, and ADR index check passed. Entrypoint is 80 lines and support modules are 152-316 lines except the preserved 281-line ADR core, all below 400.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Built the versioned cross-client ADR Kit doctor while preserving legacy ADR health output. The 282-line command was decomposed into an 80-line CLI, a preserved ADR core, isolated client checks, output models, and bounded deep probes. Human/JSON reports now expose overall/per-client states, evidence, repairs, degradations, exact actions, and a versioned hook-latency extension. Default mode safely repairs only ADR Kit-owned generated drift, --check is strictly read-only, and --fix backs up managed guidance before rewrite. Stale removed-cache launchers are detected by resolved target, client failures are isolated, MCP initialize/list/call is exercised, and local-model states distinguish missing configuration/provider, nonexistent tags, ambiguous discovery, unreachable backends, and rejected probes. Added troubleshooting documentation and regression fixtures. Verification: 709 passed, 4 skipped; generation, strict lint, and index gates passed.
<!-- SECTION:FINAL_SUMMARY:END -->
