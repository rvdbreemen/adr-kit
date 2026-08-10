---
id: TASK-168
title: Release v0.49.0 to the three marketplaces
status: In Progress
assignee: []
created_date: '2026-08-09 20:20'
updated_date: '2026-08-09 20:31'
labels:
  - release
dependencies: []
priority: high
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Ships the installer robustness work done on 2026-08-09, after v0.48.0 exposed two ways the installer could fail badly on Windows.

**The hang (TASK-165).** `python scripts/install-agent-envs.py` stalled forever at the packaged Claude hook smoke test when run from an interactive console. The hook was started without `stdin=`, inherited the console, and blocked on an EOF that never came; CPython's `subprocess.run` then re-entered `communicate()` unbounded from its own timeout handler, so the user saw a frozen process and no error. Fixed at three call sites on the installer path, with an AST guard that fails if any of them loses its `stdin=`/`input=` again.

**The destructive rollback (TASK-164, criterion 3).** A copilot install whose plugin directory is held open failed partway and its rollback then removed the client's working marketplace registration — twice in one evening on this machine. `install_copilot` now probes the directory for replaceability before touching anything and refuses with a diagnosis that names the actual cause: an editor running the plugin as an MCP server, VS Code being the usual one.

Minor rather than patch: the pre-flight refusal is new behaviour a user will notice. An install that previously ran and failed now stops before it starts and explains why. No configuration changes, no upgrade step.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 bump-version.py moved every version site and the client trees were regenerated
- [x] #2 CHANGELOG has a release-quality 0.49.0 section describing both fixes in user-facing terms
- [ ] #3 All five local gates pass
- [ ] #4 PR into main is green and handed to the maintainer
- [ ] #5 Tag pushed, release-publish.yml green, GitHub Release created
- [ ] #6 Release merged back into dev
- [ ] #7 Local prepared-directory marketplace advanced and the three clients report 0.49.0
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Branch release/v0.49.0 off the work in progress. Commit ffc06a0 carries both installer fixes; the two could not be split cleanly because tests/test_agent_installer.py holds the coverage for both, and a split would have produced a commit that is not green on its own.

bump-version.py 0.49.0 moved all 12 declared sites, build-client-adapters.py regenerated 6 files, and --check then reported changed=0. CHANGELOG 0.49.0 written to release quality: an intro naming both failures, Added for the copilot pre-flight refusal, Fixed for the hang and the destructive rollback, Changed for the payload/smoke split.

README needed no 'What's new' row: that table covers releases that change what ADR Kit does, and 0.43/0.45/0.46/0.47 are absent for the same reason. INSTALL-AGENT.md did need a change and got one - it is the runbook an agent follows to install, so it now documents that the copilot install refuses an unreplaceable plugin directory, names the editor-holding-an-MCP-server cause, and explicitly tells the agent not to work around it by deleting the plugin directory.

Gates 1-4 green: version consistency across all publish surfaces, adapter drift changed=0, adr-lint --strict 0 findings, adr-index --check changed False. Gate 5 (full suite) running isolated with its own --basetemp, because another Claude session is running pytest for the OralHistoryAgent repo on this machine and the shared pytest-of-Robert/pytest-N numbering collides.
<!-- SECTION:NOTES:END -->
