---
id: TASK-133
title: Fix Codex JSON hook Windows override key
status: Done
assignee: []
created_date: '2026-08-04 19:36'
updated_date: '2026-08-04 19:39'
labels:
  - codex
  - hooks
  - windows
  - bug
dependencies: []
references:
  - 'https://github.com/rvdbreemen/adr-kit/pull/61'
  - 'https://learn.chatgpt.com/docs/hooks'
documentation:
  - docs/clients/codex.md
  - scripts/build-client-adapters.py
  - hooks/manifest.json
modified_files:
  - scripts/client_generation_artifacts.py
  - codex/hooks/hooks.json
  - tests/test_client_adapter_generation.py
  - docs/clients/codex.md
priority: high
ordinal: 107500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The generated Codex plugin hook file uses the wrong JSON property for its Windows command override. Current ADR Kit output and the existing generator test use `command_windows`, but the current Codex hook contract reads `commandWindows` in JSON; the snake_case spelling is only valid in TOML. As a result, Windows Codex can ignore the intended override and continue to execute the non-Windows command path. Keep the scope limited to ADR Kit's canonical generator, generated Codex hook artifact, and regression coverage.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The canonical Codex hook generator emits `commandWindows` for JSON hook handlers and does not emit `command_windows`.
- [x] #2 The checked-in generated `codex/hooks/hooks.json` matches the canonical generator and contains the Windows override for every Codex handler.
- [x] #3 Generator regression tests fail on the old snake_case key and pass for the documented Codex JSON shape.
- [x] #4 The focused generator, hook protocol, and native package checks pass without changing Claude or Copilot hook schemas.
- [x] #5 The change documents that changed Codex hook definitions still require review/trust in Codex.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Compare the generated Codex hook JSON with the current official Codex hook contract. 2. Correct the canonical Windows override property and regenerate the Codex payload. 3. Add a regression assertion covering every generated Codex handler and the forbidden snake_case property. 4. Document the JSON/TOML spelling distinction and preserve Codex trust-review guidance. 5. Run focused client/hook/package tests, generator drift validation, and the read-only ADR audit.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Root cause confirmed in ADR Kit: scripts/client_generation_artifacts.py emitted command_windows in JSON. Current Codex documentation defines commandWindows for JSON; command_windows is only the TOML spelling.

PR #61 changes the Windows command string and timeout but retains the invalid command_windows JSON key, so merging it alone would not resolve this failure.

Changed the canonical generator, regenerated codex/hooks/hooks.json, strengthened tests across all Codex handlers, and documented the contract. Existing unrelated worktree changes were preserved.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed the Codex Windows hook contract in ADR Kit. The canonical generator now emits JSON's commandWindows property, the checked-in Codex hook payload was regenerated, and the regression test rejects command_windows across every generated handler. Codex trust-review behavior remains documented and unchanged. Verification passed: 40 focused client/hook/package tests, build-client-adapters.py --check with zero drift, git diff --check, and the whole-codebase ADR audit with 29 ADRs and no Accepted-ADR violations.
<!-- SECTION:FINAL_SUMMARY:END -->
