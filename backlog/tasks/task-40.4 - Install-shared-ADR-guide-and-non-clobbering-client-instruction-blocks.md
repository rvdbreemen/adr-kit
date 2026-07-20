---
id: TASK-40.4
title: 'Deliver generated ADR guide, managed instructions, and settings'
status: Done
assignee:
  - Codex
created_date: '2026-07-19 17:50'
updated_date: '2026-07-19 19:46'
labels:
  - instructions
  - settings
  - setup
  - migration
dependencies:
  - TASK-40.1
modified_files:
  - instructions/ADR-guide.md
  - codex/instructions/ADR-guide.md
  - copilot/instructions/ADR-guide.md
  - scripts/adr_settings.py
  - scripts/settings.py
  - scripts/project_setup.py
  - scripts/setup-project.py
  - tests/test_settings.py
  - tests/test_managed_instructions.py
  - tests/test_documentation_contracts.py
  - README.md
  - INSTALL.md
  - INSTALL-AGENT.md
parent_task_id: TASK-40
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Deliver the first user-visible three-client foundation: generated `.adr-kit/ADR-guide.md`, optional user-owned `.adr-kit/ADR-guide.local.md`, marker-owned pointers in `AGENTS.md`, `CLAUDE.md`, and Copilot instructions, and an `adr-kit:settings` workflow with global defaults and per-project overrides. The generated guide is replaced after backup; custom guidance remains outside markers or in the local guide. Project setup installs pre-commit by default and exposes opt-outs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Project setup writes the versioned generated `.adr-kit/ADR-guide.md` and backs up an existing generated guide before replacement.
- [x] #2 The generated guide references `.adr-kit/ADR-guide.local.md` when present and never overwrites that user-owned file.
- [x] #3 `AGENTS.md`, `CLAUDE.md`, and `.github/copilot-instructions.md` receive short independent ADR Kit marker blocks for Codex, Claude, and Copilot behavior; unrelated bytes are preserved.
- [x] #4 Setup creates, appends, or replaces only valid owned blocks and refuses duplicate, nested, reversed, or malformed markers without writing.
- [x] #5 Singular `AGENT.md` is neither created nor treated as the portable standard.
- [x] #6 `adr-kit:settings` supports global defaults with per-project overrides and shows the effective source/value for every setting.
- [x] #7 Settings cover pre-commit, update policy, Claude/Codex/Copilot opt-outs, local/cloud judgment, doctor repair policy, and offline/pinned behavior.
- [x] #8 Project setup installs deterministic pre-commit by default and settings can disable or re-enable it idempotently.
- [x] #9 Dry-run provides a unified diff; writes are atomic; backup, BOM, newline, Unicode, permission, and concurrent-lock behavior have fixtures.
- [x] #10 Legacy guide/marker layouts for the three clients migrate once with explicit actions and a second run is a no-op.
- [x] #11 Settings include automatic-update trigger/frequency and a doctor --check/no-repair policy for unattended and CI behavior.
- [x] #12 Effective judgment settings enable an already configured local provider automatically only in the documented judgment workflow; paid/cloud providers remain disabled until explicit opt-in and no judgment runs in hook hot paths.
- [x] #13 Documentation explains ownership, customization, settings precedence, backup/restore, and three-client migration.
- [x] #14 No provider or model tag is compiled as a fallback default. Selection precedence is project setting, global setting, then unambiguous compatible local discovery; zero or multiple candidates require an explicit user choice.
- [x] #15 Settings validation confirms the configured provider/model identity exists before enabling automatic local judgment; unavailable or ambiguous selection is stored and displayed as degraded/unconfigured, never healthy.
- [x] #16 A skipped optional judgment emits a bounded actionable reason and remains visible in settings/doctor output while deterministic ADR checks continue; it is never a silent successful judgment.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Size M. Implement settings resolution and guide ownership first, then managed AGENTS.md/CLAUDE.md/Copilot markers, then three-client setup integration. Preserve bytes outside owned regions. Earliest useful slice is read-only effective settings plus dry-run guide/marker plan. Stop on malformed ownership and do not add future-client instruction formats.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementation started after TASK-40.1 completed. The existing Codex setup skill currently writes `.agents/adr-kit-guide.md` and explicitly avoids CLAUDE.md; TASK-40.4 will migrate the managed contract to generated `.adr-kit/ADR-guide.md` plus independent marker-owned pointers for the three selected clients while preserving unrelated bytes.

Implemented versioned `.adr-kit/ADR-guide.md` generation, content-addressed backups, user-owned local-guide preservation, independent Codex/Claude/Copilot marker blocks, malformed-marker refusal, legacy guide/stub migration, atomic writes, setup locking, dry-run unified diffs, and safe ADR Kit-owned pre-commit enable/disable. Added global/project settings resolution with source reporting, validated update/client/doctor/judgment settings, bounded Ollama identity discovery without model invocation, and explicit unavailable/ambiguous/degraded judgment states. Public entrypoints remain thin (`settings.py` 108 lines, `setup-project.py` 96); support modules remain below 400 lines (`adr_settings.py` 352, `project_setup.py` 337). Verification: 62 relevant tests passed with 1 platform skip; deterministic payload sync check passed; strict lint/index/diff checks passed; full suite passed 668 tests with 4 skips in 205.40 seconds. A prior full-suite-only status timing miss (583 ms versus 500 ms) passed three isolated reruns and the final full suite without changing its threshold.

Implemented the generated `.adr-kit/ADR-guide.md` workflow, three independent marker-owned instruction blocks, content-addressed guide/legacy backups, atomic writes, dry-run diffs, setup locking, legacy migration, and safe ADR Kit-owned pre-commit enable/disable. Added validated global/project settings with effective source reporting, update/client/doctor/judgment controls, no model fallback tag, bounded Ollama identity discovery, and actionable inactive/degraded/ambiguous model states. Entrypoints remain thin (`settings.py` 108 lines, `setup-project.py` 96); support modules remain under the 400-line target (`adr_settings.py` 352, `project_setup.py` 337). Verification: focused shared suite 62 passed/1 skipped; full repository suite 668 passed/4 skipped in 205.40s; strict lint passes 10 ADRs; ADR indexes and synchronized client payloads are current; diff/whitespace checks pass.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Delivered the first three-client project setup foundation. ADR Kit now generates `.adr-kit/ADR-guide.md`, preserves `.adr-kit/ADR-guide.local.md`, owns short independent blocks in AGENTS.md, CLAUDE.md, and Copilot instructions, migrates legacy guide/stub layouts once with backups, and refuses malformed ownership before writing. Added a stdlib-only settings CLI with global defaults, per-project overrides, effective source reporting, pre-commit/update/client/doctor/judgment policy, explicit local-model validation, and no guessed model. Setup provides atomic idempotent writes, unified dry-run diffs, concurrent locking, preservation of BOM/newlines/Unicode/modes, and safe pre-commit enable/disable without replacing user hooks. Documentation and synchronized Codex/Copilot payloads are updated. The full suite passes: 668 passed, 4 skipped.
<!-- SECTION:FINAL_SUMMARY:END -->
