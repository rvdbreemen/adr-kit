---
id: TASK-57
title: Fix Windows CRLF false-positive drift in build-client-adapters.py --check
status: To Do
assignee: []
created_date: '2026-07-26 13:57'
labels:
  - bug
  - release
  - windows
dependencies: []
references:
  - scripts/build-client-adapters.py
  - docs/RELEASING.md
priority: medium
ordinal: 57500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found during the v0.42.0 release (TASK-56). On a Windows checkout with core.autocrlf, `python scripts/build-client-adapters.py --check` reports drift on 13 generated files (codex/, copilot/, hooks/hooks.json, templates) while `git diff` is empty: the generator emits LF, git materializes CRLF in the working copy, and the check compares raw bytes on disk.

Consequences:
- The release runbook's step-2/step-4 gate fails spuriously on the certification machine (which is Windows per the hook reference corpus), forcing the maintainer to trust Linux CI instead of the local gate.
- Running the suggested fix command rewrites all 13 files as LF, which then shows as phantom modifications until the next checkout — noise that can mask real drift.

Fix direction: normalize line endings before comparing in --check (e.g. compare `content.replace(b"\r\n", b"\n")` on both sides), or have the writer honor the existing working-copy ending. Keep the byte-exact comparison for content, only relax the EOL dimension. Add a regression test that a CRLF-materialized adapter tree passes --check.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 --check passes on a Windows checkout where git materialized CRLF and content is otherwise identical
- [ ] #2 --check still fails on real content drift (existing behaviour preserved)
- [ ] #3 Regression test covers the CRLF-materialized tree case
- [ ] #4 Release runbook needs no Windows-specific caveat afterwards
<!-- AC:END -->
