---
id: TASK-172
title: Release v0.50.0 to the three marketplaces
status: Done
assignee: []
created_date: '2026-08-10 20:27'
updated_date: '2026-08-10 21:06'
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
- [x] #1 bump-version.py moved every version site and the client trees were regenerated
- [x] #2 CHANGELOG has a release-quality 0.50.0 section naming the behaviour changes
- [x] #3 All five local gates pass
- [x] #4 PR into main is green and handed to the maintainer
- [x] #5 Tag pushed, release-publish.yml green, GitHub Release created
- [x] #6 Release merged back into dev
- [x] #7 Local prepared-directory marketplace advanced and the three clients report 0.50.0
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude Opus 5
created: 2026-08-10 21:06
---
Criterion 6 closed: PR #97 merged 2026-08-10T20:53:10Z, `git rev-list --count origin/dev..origin/main` is 0. The v0.50.0 release is on both branches, so the next release cannot silently revert it.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
v0.50.0 is released: https://github.com/rvdbreemen/adr-kit/releases/tag/v0.50.0

Five tasks closed, one decision accepted (ADR-038), one new gate. Three of the five fixes share a shape: the tooling reported something it had never checked.

Gates: version consistency across every publish surface, adapter drift changed=0, adr-lint --strict 0 findings, adr-index --check 38 ADRs changed False, full suite 1782 passed / 12 skipped / 0 failed in 808s.

PR #96 merged by the maintainer (aa3a919, all checks green). Tag v0.50.0 pushed to the verified origin/main after explicit approval - manifests and CHANGELOG heading checked on main before tagging, not assumed. release-publish.yml run 31430912908 succeeded; the GitHub Release is published, draft=false, prerelease=false. Merge-back opened as PR #97, which still needs the maintainer.

Local install is the best evidence this release works. `--clients all` printed `installed:0.49.0 -> installed:0.50.0` for all three clients. Before TASK-166 that line read the payload marker and would have said `0.50.0 -> 0.50.0` regardless of what the clients actually had - so the plan now states something it verified. Confirmed independently afterwards at each client's own registration: claude 0.50.0, codex 0.50.0, copilot 0.50.0. validation PASS for all three, exit 0.

The clients need a restart to load it.

Open after this release: TASK-171 - a declared timeout is not a real bound behind a .CMD shim, which leaves a false claim inside Accepted ADR-010. It carries a genuine design choice and deserves its own round rather than a release-tail fix.
<!-- SECTION:FINAL_SUMMARY:END -->
