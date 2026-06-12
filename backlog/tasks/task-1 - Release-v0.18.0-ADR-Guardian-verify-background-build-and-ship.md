---
id: TASK-1
title: 'Release v0.18.0: ADR Guardian (verify background build and ship)'
status: Done
assignee:
  - '@claude'
created_date: '2026-05-31 13:19'
updated_date: '2026-05-31 13:26'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Verify the background-built guardian and release it. Components: bin/adr-guardian (check/stamp/state), skills/guardian, SessionStart hook (plugin-level + project settings.json paths), guardian config block, gitignored .adr-kit-state.json, ADR-002. This is the prerequisite for v0.21.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 pytest suite green
- [x] #2 bin/adr-lint docs/adr/ clean
- [x] #3 Guardian SessionStart detector verified: cwd-guard no-ops in non-ADR projects, two-tier cadence (drift daily / LLM bi-weekly), never spawns background LLM
- [x] #4 Both hook-install paths work (plugin-level + project settings.json) and uninstall is clean
- [x] #5 ADR-002 flipped Proposed to Accepted after user sign-off
- [x] #6 Committed to main, tagged v0.18.0, GitHub release published (user sign-off)
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shipped v0.18.0 ADR Guardian. bin/adr-guardian (check/stamp/state), /adr-kit:guardian sweep, SessionStart hook (plugin-level + project-scoped), guardian config block, gitignored state, ADR-002 (Accepted). Verified fresh: 270 pytest pass, adr-lint 0 FAIL, cwd-guard silent off-project, emits CC hookSpecificOutput block on fresh project, throttle works, exit 0 always. Commit 948a0d1, tag v0.18.0, GitHub release published as latest. Note: plugin-level hook path verified live; project-scoped is a documented settings.json fragment.
<!-- SECTION:FINAL_SUMMARY:END -->
