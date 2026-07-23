---
id: TASK-52.8
title: Make the UserPromptSubmit hook timeout resilient
status: Done
assignee:
  - '@Codex'
created_date: '2026-07-23 17:58'
updated_date: '2026-07-23 18:05'
labels:
  - adr
  - hooks
  - windows
  - reliability
  - hotfix
milestone: Index-first ADR retrieval
dependencies: []
references:
  - TASK-52
  - hooks/hooks.json
  - codex/hooks/hooks.json
modified_files:
  - hooks/manifest.json
  - hooks/hooks.json
  - codex/hooks/hooks.json
  - copilot/hooks.json
  - scripts/client_generation_artifacts.py
  - tests/test_client_adapter_generation.py
  - docs/hook-performance.md
parent_task_id: TASK-52
priority: high
ordinal: 1500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Prevent intermittent UserPromptSubmit timeout warnings when ADR Kit starts its deterministic prompt-context hook on Windows or under cold filesystem and antivirus conditions. Preserve the bounded fail-open hook contract and keep normal prompt latency visible.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 UserPromptSubmit has a documented timeout budget that tolerates cold Windows process startup without masking genuinely slow retrieval.
- [x] #2 The hook remains deterministic, bounded, fail-open, model-free, and key-free.
- [x] #3 Root, Codex, Copilot, and generated client hook configurations remain synchronized.
- [x] #4 Contract tests reject a regression to the previous brittle timeout.
- [x] #5 The currently installed Codex plugin path is refreshed or patched and an exact hook invocation completes within the configured budget.
- [x] #6 Focused hook, client generation, packaging, and documentation contract tests pass.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Reproduce and measure the configured UserPromptSubmit paths on Windows. 2. Separate the client runner safety margin from the semantic latency budget in the canonical hook manifest. 3. Generate synchronized Claude, Codex, and Copilot hook configurations and enforce bounded metadata validation. 4. Patch the currently installed Codex 0.39.0 hook configuration. 5. Run focused contract tests, generation drift checks, and the exact installed invocation.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Diagnosis: the global KennisBank UserPromptSubmit hook is configured for 30 seconds and measured 2.75-3.47 seconds, so it was not the brittle path. ADR Kit 0.39.0 gave every hook only a one-second outer client-runner timeout. Although warm ADR prompt-hook samples were 85-129 ms, that budget was vulnerable to cold Windows process startup, filesystem, antivirus, or scheduler delays.

Implemented a canonical per-event `runner_timeout_sec` contract. UserPromptSubmit now receives a five-second client-runner safety margin; all other hooks retain the one-second default. Values are validated as non-boolean integers from 1 through 30. The separate semantic target remains 250 ms p95 with a 500 ms hard timeout, so slow retrieval remains visible.

Generated root, Codex, and Copilot hook configurations from the canonical manifest. Patched the installed Codex plugin cache at `C:\Users\rvdbr\.codex\plugins\cache\rvdbreemen-adr-kit-codex\adr-kit\0.39.0\hooks\hooks.json`; UserPromptSubmit is 5 seconds and SessionStart remains 1 second.

Verification: `python scripts/build-client-adapters.py --check --format json` returned clean with zero drift. Focused suite passed 52 tests. The exact installed Windows UserPromptSubmit invocation exited 0 in 223.5 ms under its five-second budget.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Raised only the ADR Kit UserPromptSubmit client-runner timeout from one to five seconds through canonical per-event metadata, leaving all other lifecycle hooks at one second and preserving the separate 250 ms p95 / 500 ms semantic performance contract. Added bounded timeout validation, synchronized generated Claude/Codex/Copilot configurations, documented the Windows cold-start rationale, and patched the installed Codex 0.39.0 plugin immediately. The generator drift check is clean, 52 focused hook/client/packaging/documentation tests pass, and the exact installed hook exits successfully in 223.5 ms. The global KennisBank hook was measured but not changed because its existing 30-second budget is healthy.
<!-- SECTION:FINAL_SUMMARY:END -->
