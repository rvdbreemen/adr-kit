---
id: TASK-78
title: 'Build /adr-kit:settings as the one place every knob lives'
status: Done
assignee: []
created_date: '2026-08-01 10:33'
updated_date: '2026-08-02 01:14'
labels:
  - spec-gap
  - R13
  - settings
dependencies: []
modified_files:
  - bin/adr-settings
  - skills/settings/SKILL.md
  - clients/workflows.json
  - scripts/client_generation_model.py
  - scripts/client_generation_artifacts.py
  - skills/judge/SKILL.md
  - tests/test_adr_settings.py
  - CHANGELOG.md
  - codex/
  - copilot/
priority: high
ordinal: 83500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
spec.md R13. There is no settings command. Fifteen skills ship — adr, context, grill, guardian, init, install-hooks, judge, lint, migrate, related, retire, review, setup, supersede, upgrade — and `skills/judge/SKILL.md:19` documents the deliberate decision that the settings surface "lives here rather than under a separate /adr-kit:settings".

That decision is now outvoted by what has accumulated around it. Today a user changes settings in three disjoint places: `/adr-kit:judge settings` for the LLM backend, `/adr-kit:install-hooks` for hook installation, and hand-editing `docs/adr/.adr-kit.json` for everything else. Two concrete failures follow:

- **judge-by-default can be switched on but not off.** `apply_backend_setting` only does `judge_block.setdefault("llm_enabled", True)`, and no shipped flag writes `false`. The documented per-commit escape (`ADR_KIT_NO_LLM=1`) is separately clobbered by the hook's own env prefix.
- **The signer of TASK-77 has nowhere to live** without this command.

Scope: show the effective value and its provenance (project / machine-local / default / env), then change it. At minimum: LLM backend and model, judge-by-default, the diff budgets, hook installation state per event, the signer, guardian cadence.

Keep the split that already works: repo-tracked settings in `.adr-kit.json`, machine- and person-specific ones in the gitignored local file. The command should make that distinction visible rather than hiding it, because it is the difference between a team decision and a personal one.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 /adr-kit:settings ships and lists every effective setting with its value and provenance
- [x] #2 Every listed setting can be changed through the command, including turning judge-by-default OFF
- [x] #3 The command distinguishes repo-tracked from machine-local settings and writes each to the right file
- [x] #4 Existing surfaces keep working: /adr-kit:judge settings and /adr-kit:install-hooks either delegate here or are documented as the deeper path
- [x] #5 skills/judge/SKILL.md:19 is updated, since it currently documents the opposite decision
- [x] #6 Writes are validated against the schema before landing, and an invalid write is refused rather than half-applied
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
`bin/adr-settings` plus the `/adr-kit:settings` skill: one place to see and change every knob, with the provenance of each value.

Both failures that motivated the task are closed. `judge.llm_enabled` can now be written false - no shipped writer could do that before, because `apply_backend_setting` only ever did `setdefault(..., True)`. And `lifecycle.signer` from TASK-77 has a surface a user will actually find, which was AC #2 of that task.

Design decisions worth keeping in view:

- **Provenance is the point.** Every row says project, machine-local, environment override, or code default. A settings screen exists to answer "why is this on?", not "what is it".
- **The command routes the write.** Team decisions land in the tracked `.adr-kit.json`, personal or machine facts in the gitignored `.adr-kit.local.json`. That split is not bookkeeping: a committed signer would put one name on every teammate's acceptance.
- **Values are typed against the schema before they land**, so `--set guardian.enabled=maybe` is refused rather than stored as a truthy string, and a refused write leaves no file behind.
- **Deeper surfaces keep their job.** Backend selection still prefers `adr-judge --set-backend`, which validates against the live registry; hook installation stays with install-hooks, which needs its own consent. The skill says so instead of duplicating them.
- **No credential is ever printed** - only whether the environment carries one.

`skills/judge/SKILL.md:19` documented the opposite decision (that no separate settings command should exist). Rewritten rather than deleted: the old reasoning held while the judge owned most of the knobs, and stopped holding once the signer, guardian cadence and retrieval limits needed a home.

Adding a sixteenth workflow surfaced that the count was hard-coded in four places. Two test assertions now read the canonical set from `client_generation_model.WORKFLOW_IDS` instead of a literal, so the next workflow is one edit rather than four.

Gates: 1269 passed / 14 skipped, adapter drift clean.</finalSummary>
<!-- SECTION:FINAL_SUMMARY:END -->
