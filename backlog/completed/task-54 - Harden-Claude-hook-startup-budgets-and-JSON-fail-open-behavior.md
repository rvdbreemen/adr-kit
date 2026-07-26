---
id: TASK-54
title: Harden Claude hook startup budgets and JSON fail-open behavior
status: Done
assignee: []
created_date: '2026-07-23 21:24'
updated_date: '2026-07-23 21:55'
labels:
  - hooks
  - claude-code
  - windows
  - reliability
dependencies: []
modified_files:
  - hooks/manifest.json
  - hooks/hooks.json
  - codex/hooks/hooks.json
  - copilot/hooks.json
  - tests/test_client_adapter_generation.py
priority: high
ordinal: 55500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Investigate and fix the live Claude hook regressions reported on Windows: ADR Kit SessionStart timing out at the configured 1-second ceiling, invalid SessionStart JSON from the combined hook stack, and UserPromptSubmit failures caused by downstream retrieval overruns. Scope adr-kit changes to owned hook configuration/wrappers and add regression coverage; track external KennisBank/security-guidance changes separately.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ADR Kit SessionStart and other Python/native-backed Claude hooks have a realistic explicit timeout budget on Windows.
- [x] #2 ADR Kit hook stdout remains either empty or exactly one valid Claude hook JSON object, with stderr isolated and all internal failures failing open.
- [x] #3 Regression tests cover configured timeout floors and JSON/fail-open behavior.
- [x] #4 Live ADR Kit SessionStart and UserPromptSubmit probes finish within configured budgets and return exit code 0.
- [x] #5 External hook owners and fixes are documented without mixing their implementation into the adr-kit scope.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Live Claude 2.1.218 debug evidence showed ADR Kit's SessionStart hook emitted valid JSON but was cancelled under its 1-second configured ceiling during concurrent Windows startup. Manual wrapper runtime was 345 ms; the live loaded path crossed the ceiling under startup load. The canonical hook manifest now sets runner_timeout_sec=5 for SessionStart and regenerates Claude, Codex, and Copilot adapters. Installed Claude 0.40.0 copies were patched to the same 5-second value. Focused hook/adapter/packaging verification passed (35 passed, 1 skipped), client adapter drift check passed, strict ADR lint and index checks ran before the later full-suite terminal timeout. External KennisBank UserPromptSubmit overruns were fixed and tracked separately in its own TASK-37/commit 8b6a2b7; security-guidance async output was verified as valid by Claude's live hook parser and was not modified. The complete pytest run exceeded the 240-second command window and ended with an output-stream OSError, so only the focused regression slice is claimed green.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Raised the canonical ADR Kit SessionStart runner ceiling from 1 to 5 seconds across generated client adapters, added three-client regression assertions, patched the live Claude 0.40.0 install, and verified the hook's JSON/exit-0 contract. Kept KennisBank remediation in its own repository and task.
<!-- SECTION:FINAL_SUMMARY:END -->
