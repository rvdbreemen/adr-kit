---
id: TASK-117
title: Dogfood the layout this kit ships
status: Done
assignee: []
created_date: '2026-08-03 19:36'
updated_date: '2026-08-03 22:10'
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
- [x] #1 `scripts/setup-project.py` is run against this repository, using the fixed invocation
- [x] #2 The STUB block and `.claude/adr-kit-guide.md` are migrated to the layout the kit ships
- [x] #3 `AGENTS.md` carries the ADR Kit block, so a Codex or Copilot session in this repository is told about the ADRs
- [x] #4 Nothing outside the managed markers is rewritten — the migration is the first real test of that guarantee
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Ran `scripts/setup-project.py --clients claude,codex,copilot --project-root .` against this repository. It found two things that only running it could find.

**This repository's own `CLAUDE.md` `@`-imported a gitignored file.** It said `Full guide: @.claude/adr-kit-guide.md`, and `.gitignore:23` carries `.claude/*` — so the guide was never tracked and **anyone cloning this repository got a dangling import**. The kit's flagship instruction surface was broken in the kit's own repository, and nobody noticed because the file exists on the maintainer's machine. That is the entire argument for this task, produced by the task.

**`--no-pre-commit` uninstalls; it does not skip.** Reached for on the assumption it meant "leave the hook alone", it printed `disable-pre-commit` and deleted `.githooks/pre-commit`. Restored from git. Not fixed here — worth a task, because the flag name reads as "do not install" and means "remove".

What landed: `.adr-kit/ADR-guide.md` tracked, the legacy `.claude/` guide gone (backed up), `CLAUDE.md` migrated to the managed marker, `AGENTS.md` and `.github/copilot-instructions.md` given the ADR block, and `.githooks/pre-commit` refreshed from the current template — two documentation lines, version stamp unchanged at 0.44.0, so no collision with the v0.44.1 release branch.

`.gitignore` gained `.adr-kit/backups/` and `.adr-kit/ADR-guide.local.md`: a backup records what *this* checkout looked like before the write, which is meaningless to a teammate.

AC#4 verified by what git reported: only the four managed files and the new guide changed. Nothing outside the markers moved — `AGENTS.md`'s existing Backlog and verification conventions are byte-identical, with the ADR block appended.
<!-- SECTION:FINAL_SUMMARY:END -->
