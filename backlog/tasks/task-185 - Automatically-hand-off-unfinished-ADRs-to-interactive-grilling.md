---
id: TASK-185
title: Automatically hand off unfinished ADRs to interactive grilling
status: Done
assignee: []
created_date: '2026-08-20 05:40'
updated_date: '2026-08-20 19:04'
labels:
  - adr-grilling
  - automation
  - readiness
  - hooks
  - clients
dependencies: []
references:
  - >-
    docs/adr/ADR-011-adopt-deterministic-readiness-and-human-gated-grilling-across-the-adr-lifecycle.md
  - docs/adr/ADR-002-adr-guardian-session-start-staleness-detector.md
  - >-
    docs/adr/ADR-024-ask-for-a-missing-adr-at-the-pull-request-moment-inside-the-guard.md
documentation:
  - docs/adr-grilling.md
  - docs/feature-adr-grilling/03-solution-design.md
modified_files:
  - hooks/adr_hook_core.py
  - hooks/native/adr-hook.rs
  - schemas/adr-kit-config.schema.json
  - clients/workflows.json
  - skills/grill/SKILL.md
  - instructions/ADR-guide.md
  - docs/adr-grilling.md
  - docs/clients/opencode.md
  - opencode/plugin.ts
  - tests/test_adr_auto_grill.py
  - tests/test_opencode_plugin.py
  - >-
    docs/adr/ADR-041-automatically-hand-off-unfinished-proposed-adrs-to-interactive-grilling.md
  - templates/adr-kit-guide.md
priority: high
type: enhancement
ordinal: 29000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
When deterministic ADR readiness detects an unfinished or unclear Proposed ADR during an interactive agent session, automatically hand the highest-priority candidate to the native ADR grilling workflow. Detection stays local and deterministic; the grill asks the human one question at a time and lifecycle acceptance remains explicitly human-gated. Do not start interviews from unattended hooks, pre-commit, CI, or background processes.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A Proposed ADR with unresolved Open Questions or readiness classification needs-human-input is automatically handed to grilling on the next user-visible interaction.
- [x] #2 A Proposed ADR that is ready-for-confirmation, shipped but still Proposed, explicitly linked to changed implementation, or below the existing 0.70 quality threshold is eligible for automatic grilling with a deterministic reason.
- [x] #3 Mechanical readiness failures are repaired or reported before human grilling; Accepted ADRs are never edited and only explicit revalidation may route them to grilling.
- [x] #4 Only one automatic grill starts per session and recursive re-entry is suppressed; the active grill continues through its one-question-at-a-time protocol.
- [x] #5 Pre-commit, CI, PreToolUse, PostToolUse, and unattended SessionStart paths remain advisory and fail-open; they never start an interactive interview.
- [x] #6 Automatic detection adds no model or network call; client invocation failures fail open and leave the exact native grill command visible.
- [x] #7 The grill never accepts an ADR automatically; acceptance still requires an explicit same-session confirmation and adr accept --confirm.
- [x] #8 Claude, Codex, Copilot, and the separately documented OpenCode surface have focused integration coverage, with generated adapters remaining deterministic.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 The Proposed successor ADR, backlog task notes, and implementation evidence are recorded.
- [x] #2 Strict ADR lint, focused tests, generated-adapter checks, and ADR judgment pass.
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Create a Proposed successor decision for the current advisory-only automation boundary. 2. Define deterministic auto-grill eligibility from readiness and the existing Proposed queue. 3. Dispatch one candidate per interactive session through the canonical client workflow surfaces, with OpenCode kept as a separate native adapter. 4. Add re-entry, opt-out, mechanical-fix, immutable-ADR, and fail-open safeguards. 5. Add focused readiness, queue, hook, workflow, client, and lifecycle tests; regenerate generated client artifacts. 6. Run strict ADR lint, full relevant tests, and ADR diff judgment.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented deterministic automatic grilling handoff. The shared hook core reads the bounded Proposed queue at UserPromptSubmit, selects the first needs-human-input, ready-for-confirmation, or supersession-required item, skips mechanical fixes, emits one AUTO_GRILL_PENDING instruction with the client-native command, suppresses one-session re-entry through temp state, and honors grill.auto_start:false plus ADR_KIT_AUTO_GRILL_DISABLE=1. SessionStart, PreToolUse, PostToolUse, pre-commit, CI, and background paths remain advisory and fail-open. Added canonical workflow/skill/guide/docs updates, generated Codex/Copilot adapters, rebuilt the opt-in native Windows host, and normalized OpenCode's command surface to /adr-kit-grill. ADR-041 remains Proposed with one human confirmation question; it was not accepted.

Follow-up 2026-08-20: the upgrade flow now materializes grill.auto_start=true when the project has no explicit value, while preserving grill.auto_start=false opt-outs. Settings exposes the default and regression coverage passes.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
TASK-185 implementation complete. Verification: python -m pytest -q -> 1805 passed, 13 skipped; focused automatic-grill, hook, native, OpenCode, adapter, and graph slice -> 84 passed; python scripts/build-client-adapters.py --check -> changed=0; python bin/adr-lint --strict docs/adr -> 40 strict passes, 1 advisory Proposed record; MCP strict ADR lint -> verdict ok; adr-judge over the working diff -> 0 violations. Human follow-up remains /adr-kit:grill ADR-041 and explicit acceptance if the proposed automation boundary is approved.

ADR-041 was subsequently accepted by Robert van den Breemen. Upgrade-default follow-up verified with tests/test_adr_settings.py (14 passed) and generated adapter parity (changed=0).
<!-- SECTION:FINAL_SUMMARY:END -->
