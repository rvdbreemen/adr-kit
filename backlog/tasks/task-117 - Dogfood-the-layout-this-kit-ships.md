---
id: TASK-117
title: Dogfood the layout this kit ships
status: To Do
assignee: []
created_date: '2026-08-03 19:36'
labels:
  - docs
  - setup
dependencies:
  - TASK-105
priority: low
ordinal: 5300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
This repository does not use the layout it ships. `CLAUDE.md` carries the legacy STUB block and `.claude/adr-kit-guide.md` — the footprint `scripts/project_setup.py` classifies as `LEGACY_GUIDES` and migrates away from — and the root `AGENTS.md` (31 lines) carries zero ADR instructions, only Backlog and verification conventions.

The user gets nothing directly. The maintainer gets a repository that exercises its own setup surface, which is the cheapest way for a broken setup path to be noticed by the person who can fix it. TASK-105 exists because that path was broken for two of three clients and nobody hit it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `scripts/setup-project.py` is run against this repository, using the fixed invocation
- [ ] #2 The STUB block and `.claude/adr-kit-guide.md` are migrated to the layout the kit ships
- [ ] #3 `AGENTS.md` carries the ADR Kit block, so a Codex or Copilot session in this repository is told about the ADRs
- [ ] #4 Nothing outside the managed markers is rewritten — the migration is the first real test of that guarantee
<!-- AC:END -->
