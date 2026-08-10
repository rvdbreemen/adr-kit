---
id: TASK-168
title: Release v0.49.0 to the three marketplaces
status: Done
assignee: []
created_date: '2026-08-09 20:20'
updated_date: '2026-08-10 05:28'
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
- [x] #3 All five local gates pass
- [x] #4 PR into main is green and handed to the maintainer
- [x] #5 Tag pushed, release-publish.yml green, GitHub Release created
- [x] #6 Release merged back into dev
- [x] #7 Local prepared-directory marketplace advanced and the three clients report 0.49.0
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Branch release/v0.49.0 off the work in progress. Commit ffc06a0 carries both installer fixes; the two could not be split cleanly because tests/test_agent_installer.py holds the coverage for both, and a split would have produced a commit that is not green on its own.

bump-version.py 0.49.0 moved all 12 declared sites, build-client-adapters.py regenerated 6 files, and --check then reported changed=0. CHANGELOG 0.49.0 written to release quality: an intro naming both failures, Added for the copilot pre-flight refusal, Fixed for the hang and the destructive rollback, Changed for the payload/smoke split.

README needed no 'What's new' row: that table covers releases that change what ADR Kit does, and 0.43/0.45/0.46/0.47 are absent for the same reason. INSTALL-AGENT.md did need a change and got one - it is the runbook an agent follows to install, so it now documents that the copilot install refuses an unreplaceable plugin directory, names the editor-holding-an-MCP-server cause, and explicitly tells the agent not to work around it by deleting the plugin directory.

Gates 1-4 green: version consistency across all publish surfaces, adapter drift changed=0, adr-lint --strict 0 findings, adr-index --check changed False. Gate 5 (full suite) running isolated with its own --basetemp, because another Claude session is running pytest for the OralHistoryAgent repo on this machine and the shared pytest-of-Robert/pytest-N numbering collides.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
v0.49.0 is released: https://github.com/rvdbreemen/adr-kit/releases/tag/v0.49.0

Four fixes, all found by installing v0.48.0 on Windows and following the failures instead of working around them.

1. TASK-165: the installer hung forever at the packaged Claude hook smoke test. The hook inherited the interactive console's stdin and blocked on an EOF that never came; CPython's subprocess.run then re-entered communicate() without a bound from its own TimeoutExpired handler, so the process stalled with no error at all. Every subprocess on the installer path now closes stdin, guarded by an AST scan that also rejects stdin=None.
2. TASK-164 criterion 3: a copilot install whose plugin directory is held open dismantled the client's working registration. install_copilot now probes for replaceability before touching anything and refuses with a diagnosis naming the real cause - an editor running the plugin as an MCP server - established by enumerating all 284,515 system handles rather than guessed.
3. TASK-169: the installer never recorded judge.host_client, so the LLM judge was off by default despite ADR-036 stating it is recorded at install time. This repository had been running that way itself.
4. The pre-commit hook advertised ADR_KIT_NO_LLM=1 and then overwrote it with an internal lock flag. Harmless while no backend existed; with one it is the difference between a 21-second and a 126-second commit.

Gates: version consistency, adapter drift changed=0, adr-lint --strict 0 findings, adr-index --check changed False, and the full suite via CI (12/12 checks green on PR #93). The one local suite failure was a wall-clock assertion that this release also fixes: test_client_generator_performance asserted the p50 budget against a live clock with 33% of headroom over the committed p50, where ADR-015 asks a live smoke test to guard the hard ceiling with a factor two of margin.

PR #93 merged by the maintainer, tag v0.49.0 pushed to the verified origin/main commit 6e184fc after explicit approval, release-publish.yml run 31358358369 succeeded, GitHub Release published from the CHANGELOG section (draft=false, prerelease=false).

Merge-back into dev opened as PR #94 (dev was 5 commits behind; clean merge, gates re-run on the result). That PR still needs the maintainer.

Local install: `--clients all` reports validation PASS for all three. Verified per client at the source rather than from the installer's own reporting, since TASK-166 shows that reporting is derived from a shared marketplace marker: claude installed_plugins.json 0.49.0, codex config.toml marketplace source ...\marketplaces\0.49.0, copilot config.json installedPlugins adr-kit 0.49.0. The clients need a restart to load it.

One blemish in the published notes: the release intro says "Two failures" because it was written before TASK-169 and the hook fix joined the release. The four entries below it are complete and correct.

Follow-ups filed: TASK-166 (per-client version never read from the client; lexicographic marker ordering lets .old outrank the live directory), TASK-167 (three same-class inherited-stdin call sites outside the installer path), TASK-170 (one unusable verdict degrades the whole LLM pass).
<!-- SECTION:FINAL_SUMMARY:END -->
