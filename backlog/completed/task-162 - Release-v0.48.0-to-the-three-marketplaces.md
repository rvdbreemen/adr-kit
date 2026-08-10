---
id: TASK-162
title: Release v0.48.0 to the three marketplaces
status: Done
assignee:
  - '@claude'
created_date: '2026-08-09 15:49'
updated_date: '2026-08-10 21:03'
labels:
  - release
dependencies: []
priority: high
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Ships 22 commits since v0.47.0: the ADR-036 KISS simplification (vector layer retired, judge reduced to the host backend, eight config keys refused by name, health family folded behind adr-audit, one setup entry point), ADR-037 per-ADR judge verdicts in the guardian, the R5 prompt-injection rephrasing (candidates the model selects from), the upgrade-path work (whole-set cost picture in adr-migrate, backend and cadence steps in the upgrade skill), and eleven review findings fixed. Minor rather than patch: a config carrying a retired key now fails validation loudly instead of being ignored, which is an upgrade step for existing projects.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 bump-version.py moved every version site and the client trees were regenerated
- [x] #2 CHANGELOG has a release-quality 0.48.0 section naming the upgrade step for retired config keys
- [x] #3 All five local gates pass
- [x] #4 PR into main is green and handed to the maintainer
- [x] #5 Tag pushed, release-publish.yml green, GitHub Release created
- [x] #6 Release merged back into dev
- [x] #7 Local prepared-directory marketplace advanced and the three clients report 0.48.0
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-08-09: gates 1-5 all green locally. check-release-version --expect v0.48.0 (all publish surfaces agree), build-client-adapters --check (changed=0), adr-lint --strict (37 PASS strictly, 0 FAIL), adr-index --check (changed: False), pytest -q (1764 passed, 12 skipped, exit 0, 617s). Commit 7722627 on release/v0.48.0, pushed. PR #89 open into main: https://github.com/rvdbreemen/adr-kit/pull/89 - awaiting CI, then the maintainer merges (main is protected, enforce_admins).

Note for the tag step: the pre-commit judge ran declarative-only on this machine because judge.backend is 'host' with no host-client recorded in .adr-kit.local.json. Per ADR-025 that is a machine fact, not repository config; it does not affect the release, but this machine cannot run the LLM pass until `bin/adr-judge --set-backend host --host-client claude-code-cli` is run here.

2026-08-09 (2): PR #89 merged into main at 16:07:59Z. Not an agent bypass - the maintainer (rvdbreemen) enabled auto-merge at 16:07:20Z, 103s after PR creation, and GitHub merged once all 12 checks passed (validate, pytest, 6 x python matrix, ADR enforcement, adr-lint smoke, adr-readiness, index freshness). main head is now 8f2038e.

Caught after that merge: docs/RELEASING.md step 2 asks for a manual README capability review that no gate covers. The 'What's new' table stopped at 0.44.0, whose row advertises the local precomputed vector layer as a headline feature - the exact subsystem 0.48.0 removes. Tagging main as it stood would have published a README selling a deleted subsystem. Fixed in 38614f0 (0.48.0 row, 0.44.0 mention marked retired by ADR-036, stale release count dropped from the intro) and opened as PR #90, because #89 had already merged. Two ADR links in that commit were first written from guessed filenames and corrected against docs/adr/ before the commit.

Tag v0.48.0 must wait for #90 so the tagged tree carries the corrected README.

2026-08-09 (3): PR #90 merged by the maintainer at 16:13:47Z (auto-merge again, 12/12 checks). main head 2c59bdc. Tagged origin/main explicitly rather than HEAD, because `git checkout main` had aborted on the modified task-162.md and the following `git pull` fast-forwarded release/v0.48.0 instead - HEAD and origin/main happened to be the same commit, but the tag command should not depend on that. Verified `git rev-parse v0.48.0` == `git rev-parse origin/main` before pushing.

release-publish.yml run 31323399560: completed success (confirmed against the API, not the watch exit). Release https://github.com/rvdbreemen/adr-kit/releases/tag/v0.48.0 is published, draft=false, prerelease=false, body carries the CHANGELOG section including the upgrade step.

2026-08-09 (4): PR #91 merged by the maintainer at 16:25:11Z; dev is 0 behind main. 11 of 12 checks were green at merge time (Python 3.12/Windows still pending), on a tree identical to the one where all 12 passed on #90. The local pytest re-run was stopped as redundant once CI had covered the same tree on six matrix jobs - it was not run to completion.

Step 6 partially done. install-agent-envs.py --clients all: claude 0.48.0 OK, codex 0.48.0 OK, copilot FAILED and is now left with no adr-kit at all (it had a working 0.47.0). Filed as TASK-164 with the diagnosis: a Windows directory handle on ~/.copilot/installed-plugins/rvdbreemen-adr-kit-copilot that no running process could be attributed to, plus the real defect that our rollback dismantled the working install instead of leaving it alone. Acceptance criterion #7 stays unchecked until copilot is back.

Unrelated observation while diagnosing: a Codex agent on this machine repeatedly spawns `bash.exe /c/Tools/Codex/python -m pytest`, a new one roughly every four minutes. Not from this session.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude Opus 5
created: 2026-08-09 20:09
---
Criterion #7 closed 2026-08-09 22:07. Copilot is back at 0.48.0 after the VS Code window holding the plugin directory was closed; see TASK-164 comments #2-#5 for the diagnosis and the restore. Verified per client, independently of the installer's own reporting (which TASK-166 shows is derived from a shared marketplace marker rather than the client): claude `installed_plugins.json` -> adr-kit@rvdbreemen-adr-kit 0.48.0; codex `config.toml` -> marketplace source ...\marketplaces\0.48.0, plugin enabled; copilot `plugin list` -> adr-kit@rvdbreemen-adr-kit-copilot v0.48.0.

Also worth correcting from the note above: the repeating pytest processes on this machine were blamed on 'a Codex agent'. During TASK-165 I found four such runs hanging for over an hour and, with the user's approval, killed them; more kept appearing with `-p no:cacheprovider`, which is not a flag this session uses. They invalidated two full suite runs before I isolated my own with a dedicated --basetemp. Whatever spawns them, they are still running on this machine.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
v0.48.0 released: https://github.com/rvdbreemen/adr-kit/releases/tag/v0.48.0

All seven acceptance criteria are met. Criterion 7 was the last one open and closed on 2026-08-09 once copilot was back at 0.48.0; the diagnosis of why it failed is in TASK-164, and the reason the installer misreported it afterwards is in TASK-166. Both of those shipped in v0.49.0 and v0.50.0 respectively.

Closed retroactively on 2026-08-10: the task stayed In Progress after its last criterion was ticked. Nothing was outstanding.
<!-- SECTION:FINAL_SUMMARY:END -->
