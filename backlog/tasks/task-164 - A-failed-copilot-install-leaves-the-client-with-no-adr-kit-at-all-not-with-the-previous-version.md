---
id: TASK-164
title: >-
  A failed copilot install leaves the client with no adr-kit at all, not with
  the previous version
status: To Do
assignee: []
created_date: '2026-08-09 16:37'
updated_date: '2026-08-09 16:41'
labels:
  - bug
  - installer
  - windows
dependencies: []
references:
  - scripts/install-agent-envs.py
  - clients/installer/transaction.py
  - docs/RELEASING.md
priority: high
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found during the v0.48.0 release (TASK-162), step 6 of docs/RELEASING.md. `python scripts/install-agent-envs.py --clients all` installed claude and codex at 0.48.0 and exited 1 on copilot. Copilot was left with no adr-kit marketplace and no plugin, where it previously had a working 0.47.0.

Verbatim from the run:

```
Installing ADR Kit for copilot:
  $ copilot.cmd plugin marketplace add ...\marketplaces\0.48.0
  $ copilot.cmd plugin install adr-kit@rvdbreemen-adr-kit-copilot
  undo: removing marketplace registered by this run
  $ copilot.cmd plugin marketplace remove rvdbreemen-adr-kit-copilot --force
  $ copilot.cmd plugin marketplace add ...\marketplaces\0.48.0.old
  $ copilot.cmd plugin install adr-kit@rvdbreemen-adr-kit-copilot
  undo: removing marketplace registered by this run
  $ copilot.cmd plugin marketplace remove rvdbreemen-adr-kit-copilot --force
FAILED (copilot): command failed (1): ... plugin install adr-kit@rvdbreemen-adr-kit-copilot
Failed to install plugin: Error: Failed to install plugin: Access is denied. (os error 5)
```

Two separate problems.

**1. The trigger (environmental, Windows, not ours).** `~/.copilot/installed-plugins/rvdbreemen-adr-kit-copilot` and its child `adr-kit` cannot be renamed: "Access to the path is denied". Established by probing:
- No individual file under that tree is exclusively locked. Every file was opened with `FileShare.None`; zero failures.
- The subdirectories `adr-kit\bin` and `adr-kit\skills` rename freely. Only the plugin root and `adr-kit` are held.
- ACLs are identical to the sibling `_direct` directory and the user has Full control, so this is not a permissions problem.
- No process holds either directory as its current working directory. Verified directly by reading `RTL_USER_PROCESS_PARAMETERS.CurrentDirectory` out of the PEB of all 71 candidate processes (WMI does not expose cwd, and Sysinternals handle.exe is not installed on this machine). Zero hits under `.copilot\installed-plugins`.
- In particular the two running `adr-mcp` servers are NOT the holder, which had to be checked properly rather than dismissed on their command line: both were spawned by claude.exe, and their cwds are `D:\...\GitHub\RvdB\adr-kit\` and `D:\...\GitHub\RvdB\OralHistoryAgent\`.

What remains is an open directory handle taken without delete sharing, which is what a directory watcher or the Windows Search indexer does. The holder was not identified, but it is not an adr-kit process.

**2. The defect (ours).** The rollback made the outcome worse than doing nothing. `run_transaction` in `install_selected_clients` undoes the marketplace registration, then reinstalls from `<source>.old`. That second install hit the same lock and also failed, and its undo removed the marketplace again. Net result: copilot went from a working 0.47.0 to nothing, and the single reported error only names the first failure. A user reading that output has no way to know their previous install was also taken down.

An upgrade that cannot proceed should leave the client exactly as it was. Options worth weighing: verify the rollback actually restored a working install before reporting, and if it did not, say so explicitly in the failure message; or detect the un-writable plugin directory before touching the existing registration at all, and refuse the upgrade with a diagnosis instead of dismantling what works.

**Current state of this machine (corrected 2026-08-09, after the notes above were first written).** The marketplace `rvdbreemen-adr-kit-copilot` IS registered again and points at `...\marketplaces\0.48.0`; only the plugin is missing. That registration came from a manual `plugin marketplace add` during diagnosis, not from the installer. It was deliberately left in place: `install_copilot` lists the marketplaces first and skips the add when `marketplace_source_matches` recognises the source, and copilot's listing does print the path, so the next run goes straight to `plugin install` and, with `added_marketplace` false, will not remove anything on failure. The stale 0.47.0 files are still on disk under the plugin directory; copilot's own config.json reads `"installedPlugins": []`.

Remediation once the handle is released (close any Explorer window on that folder, or reboot): `python scripts/install-agent-envs.py --clients copilot`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A failed client install never leaves that client with less than it had before the run
- [ ] #2 When rollback cannot restore the previous install, the failure output says so explicitly rather than reporting only the original error
- [ ] #3 The un-writable plugin directory is detected and diagnosed before the existing registration is removed
- [ ] #4 Regression coverage simulates an install command failing on a client that already has a working older version
<!-- AC:END -->
