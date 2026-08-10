---
id: TASK-172
title: Release v0.50.0 to the three marketplaces
status: In Progress
assignee: []
created_date: '2026-08-10 20:27'
labels:
  - release
dependencies: []
priority: high
ordinal: 16000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Ships the backlog sweep of 2026-08-10: five tasks closed, one decision accepted, one new gate.

- TASK-164 - a failed install no longer reports only half the story. `run_transaction` discarded the rollback outcome whenever the install error was a RuntimeError, which is every failing client command, and the rollback never checked that it had actually restored anything.
- TASK-166 - the installer reported a per-client version it had never read from the client, and a `.old` backup outranked the live marketplace directory.
- TASK-167 - three subprocess call sites reviewed; one closed with evidence and no change, two changed for a measured boundedness defect rather than the cause the task named.
- TASK-170 / ADR-038 - one unusable LLM verdict no longer discards the verdicts already established.
- TASK-163 - the README "What's new" table is now gated against linking decisions that stopped governing.

Minor rather than patch: ADR-038 changes when a commit can fail, and the installer now reads client registrations it never read before.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 bump-version.py moved every version site and the client trees were regenerated
- [ ] #2 CHANGELOG has a release-quality 0.50.0 section naming the behaviour changes
- [ ] #3 All five local gates pass
- [ ] #4 PR into main is green and handed to the maintainer
- [ ] #5 Tag pushed, release-publish.yml green, GitHub Release created
- [ ] #6 Release merged back into dev
- [ ] #7 Local prepared-directory marketplace advanced and the three clients report 0.50.0
<!-- AC:END -->
