---
id: TASK-160
title: >-
  Gate the Copilot PowerShell wrapper's native host behind ADR_KIT_NATIVE_HOOK
  like run-hook.cmd
status: Done
assignee:
  - '@claude'
created_date: '2026-08-09 15:24'
updated_date: '2026-08-09 15:33'
labels:
  - bug
  - copilot
  - hooks
dependencies: []
priority: medium
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
hooks/run-hook.cmd runs the native exe only when ADR_KIT_NATIVE_HOOK=1, with a comment that preferring it silently narrowed governance on Windows (returned 1 of 4 governing ADRs). The generated Copilot PowerShell wrapper (scripts/client_generation_artifacts.py:207) prefers the exe UNCONDITIONALLY whenever it exists, so Windows Copilot sessions default to the not-parity-certified host every other client gates. Pre-existing divergence made live by PR #85's dual-host string changes. Review finding NF5.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The PowerShell wrapper uses the native exe only when ADR_KIT_NATIVE_HOOK equals 1, falling back to Python otherwise, mirroring run-hook.cmd
- [x] #2 Adapters regenerated, --check clean; a test pins the gating in the generated artifact
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The generated Copilot PowerShell wrapper now runs the native exe only when ADR_KIT_NATIVE_HOOK=1, mirroring hooks/run-hook.cmd's opt-in and its rationale (host not parity-certified; preferring it silently narrowed governance on Windows). Adapters regenerated; a new test walks every powershell handler in copilot/hooks.json and demands the env gate wherever the exe is invoked - verified it runs against the real artifact, not skipped.
<!-- SECTION:FINAL_SUMMARY:END -->
