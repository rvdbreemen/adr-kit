---
id: TASK-164
title: >-
  A failed copilot install leaves the client with no adr-kit at all, not with
  the previous version
status: To Do
assignee: []
created_date: '2026-08-09 16:37'
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

**1. The trigger (environmental, Windows).** `~/.copilot/installed-plugins/rvdbreemen-adr-kit-copilot` and its child `adr-kit` cannot be renamed: "Access to the path is denied". Established by probing:
- No individual file under that tree is exclusively locked (opened every file with FileShare.None; zero failures).
- The subdirectories `adr-kit\bin` and `adr-kit\skills` rename freely; only the plugin root and `adr-kit` are held.
- ACLs are identical to the sibling `_direct` directory and the user has Full control, so this is not a permissions problem.

That pattern is a directory handle without delete sharing, or a process whose current working directory is inside it. No copilot process was running and no process command line referenced the path, so the holder was not identified. Both adr-mcp processes on the machine were spawned by claude.exe from the marketplace tree, not from the copilot plugin tree. Likely candidates are an open Explorer window on the folder, the Windows Search indexer, or a directory watcher.

**2. The defect (ours).** The rollback made the outcome worse than doing nothing. `run_transaction` in `install_selected_clients` undoes the marketplace registration, then reinstalls from `<source>.old`. That second install hit the same lock and also failed, and its undo removed the marketplace again. Net result: copilot went from a working 0.47.0 to nothing, and the single reported error only names the first failure. A user reading that output has no way to know their previous install was also taken down.

An upgrade that cannot proceed should leave the client exactly as it was. Options worth weighing: verify the rollback actually restored a working install before reporting, and if it did not, say so explicitly in the failure message; or detect the un-writable plugin directory before touching the existing registration at all, and refuse the upgrade with a diagnosis instead of dismantling what works.

Remediation for this machine, once the handle is released (close any Explorer window on that folder, or reboot): `python scripts/install-agent-envs.py --clients copilot`. The 0.47.0 files are still on disk at the path above; copilot's own config.json already reads `"installedPlugins": []`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A failed client install never leaves that client with less than it had before the run
- [ ] #2 When rollback cannot restore the previous install, the failure output says so explicitly rather than reporting only the original error
- [ ] #3 The un-writable plugin directory is detected and diagnosed before the existing registration is removed
- [ ] #4 Regression coverage simulates an install command failing on a client that already has a working older version
<!-- AC:END -->
