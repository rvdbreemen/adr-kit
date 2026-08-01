---
id: TASK-78
title: 'Build /adr-kit:settings as the one place every knob lives'
status: To Do
assignee: []
created_date: '2026-08-01 10:33'
updated_date: '2026-08-01 10:33'
labels:
  - spec-gap
  - R13
  - settings
dependencies: []
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
- [ ] #1 /adr-kit:settings ships and lists every effective setting with its value and provenance
- [ ] #2 Every listed setting can be changed through the command, including turning judge-by-default OFF
- [ ] #3 The command distinguishes repo-tracked from machine-local settings and writes each to the right file
- [ ] #4 Existing surfaces keep working: /adr-kit:judge settings and /adr-kit:install-hooks either delegate here or are documented as the deeper path
- [ ] #5 skills/judge/SKILL.md:19 is updated, since it currently documents the opposite decision
- [ ] #6 Writes are validated against the schema before landing, and an invalid write is refused rather than half-applied
<!-- AC:END -->
