---
id: TASK-164
title: >-
  A failed copilot install leaves the client with no adr-kit at all, not with
  the previous version
status: In Progress
assignee: []
created_date: '2026-08-09 16:37'
updated_date: '2026-08-09 20:14'
labels:
  - bug
  - installer
  - windows
dependencies: []
references:
  - scripts/install-agent-envs.py
  - clients/installer/transaction.py
  - docs/RELEASING.md
modified_files:
  - clients/installer/native.py
  - tests/test_agent_installer.py
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
- [x] #3 The un-writable plugin directory is detected and diagnosed before the existing registration is removed
- [ ] #4 Regression coverage simulates an install command failing on a client that already has a working older version
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Acceptance criterion #3 implemented. `install_copilot` now probes the plugin directory before it touches anything: `directory_replacement_blocked_by` renames the directory aside and back, and a failure aborts the run with a diagnosis instead of proceeding into the mutation the rollback would later have to undo. Two syscalls, and only on a real run — dry run reports rather than renames, so it does not mutate to find out.

The message names the cause the investigation found rather than a generic 'file in use':

```
  FAILED (copilot): copilot's plugin directory cannot be replaced, so this install would fail
  partway through and leave copilot with less than it has now. Nothing was changed.

    directory: C:\Users\rvdbr\.copilot\installed-plugins\rvdbreemen-adr-kit-copilot
    reason:    [WinError 5] Access is denied: '...'

  An editor holding the ADR Kit plugin keeps this directory open. VS Code is the
  usual cause: it runs the plugin as an MCP server and keeps handles on the
  plugin directory, which blocks the rename copilot needs. Closing the editor
  window for this project releases them; killing the server process alone does
  not, because the editor restarts it within seconds.

  Close the editor, then run this command again.
```

The 'killing the server alone does not work' sentence is there because it was measured, not assumed — see comment #4.

Coverage: three tests in tests/test_agent_installer.py. The important assertion is that the runner is never called once the directory is known to be locked, since the whole point is that nothing gets dismantled. The others check that the probe puts the directory back (an absent directory blocks nothing, and no `.adr-kit-probe` is left behind) and that dry run skips the probe entirely. Verified against the real client afterwards: `--clients copilot` on the now-healthy machine reports `no-op: adr-kit 0.48.0 is already healthy` and `validation: PASS (copilot)`, so the probe does not obstruct a working install.

Still open here: #1 only holds for the locked-directory case, not for an install command that fails for some other reason; #2 (rollback saying so when it could not restore) and #4 (a regression that simulates the failing install command itself) are untouched.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude Opus 5
created: 2026-08-09 19:25
---
State re-verified 2026-08-09 ~21:20 while reviewing TASK-165. Unchanged from the corrected note in the description: `~/.copilot/config.json` still reads `"installedPlugins": []`, and the stale 0.47.0 tree is still on disk — `~/.copilot/installed-plugins/rvdbreemen-adr-kit-copilot/adr-kit/plugin.json` reports version 0.47.0. So the plugin.json on disk is a leftover, not a working install; anyone reading only that file will conclude copilot is on 0.47.0, which it is not.

New, and filed separately as TASK-166: the installer actively misreports this. `python scripts/install-agent-envs.py --clients claude` printed `copilot: SKIP; installed:0.48.0 -> installed:0.48.0` for exactly this machine state, because detection.py takes installed_version from one marketplace marker shared by all three clients rather than from the client's own registration. Remediation for this task is unchanged; the point is that the plan output cannot be used as evidence that copilot is fine.
---

author: Claude Opus 5
created: 2026-08-09 20:01
---
Handle holder identified 2026-08-09. It is VS Code, running the adr-kit copilot plugin as an MCP server. The earlier probe missed it because it looked for a process whose *current directory* was inside the tree; this is an open directory handle held by a watcher, which never shows up as a cwd.

Method: enumerated all 284,515 system handles via NtQuerySystemInformation(SystemExtendedHandleInformation=64), duplicated each into the probe process, filtered to FILE_TYPE_DISK before calling NtQueryObject (querying a pipe blocks forever), and translated \\Device\\HarddiskVolumeN back to drive letters with QueryDosDevice. Script kept at scratchpad/find-handle.ps1. 191 processes could not be opened for PROCESS_DUP_HANDLE (SYSTEM/protected), so the scan is not exhaustive — but it did not need to be.

Result:
```
pid 38420 (Code)  ...\rvdbreemen-adr-kit-copilot\adr-kit          (5 handles)
pid 38420 (Code)  ...\rvdbreemen-adr-kit-copilot\adr-kit\skills  (2 handles)
pid 38420 (Code)  ...\rvdbreemen-adr-kit-copilot                  (1 handle)
pid 38420 (Code)  ...\installed-plugins                           (1 handle)
pid 38420 (Code)  ...\installed-plugins\_direct                   (1 handle)
```
PID 38420 is a `--type=utility --utility-sub-type=node.mojom.NodeService` child of PID 14816, which is `code.exe D:\Users\Robert\Documents\GitHub\RvdB\adr-kit`, started 15:58:04 — before the failed release install. Confirmed independently by the log file VS Code writes for it: `AppData\Roaming\Code\logs\20260809T155757\window1\mcpServer.plugin.file<...installed-plugins\rvdbreemen-adr-kit-copilot\adr-kit>.adr-kit.log`.

So the trigger is not environmental in the 'unknowable Windows' sense recorded earlier: the plugin blocks its own upgrade whenever an editor has it loaded. That makes acceptance criterion #3 concrete and cheap — probe the plugin directory for renameability before removing the existing registration, and when it fails, name the holding process instead of dismantling a working install. Note that `_direct` is also held yet renames fine, so the presence of a handle is not the test; attempting the rename is.

Remediation on this machine: close the VS Code window on the adr-kit repo (or stop that MCP server in it), then run `python scripts/install-agent-envs.py --clients copilot`.
---

author: Claude Opus 5
created: 2026-08-09 20:02
---
The defect fired a second time, 2026-08-09 ~21:55, and the 'Current state of this machine' paragraph in the description is now stale. A user-run `python scripts/install-agent-envs.py --clients copilot` did:

```
  $ copilot.cmd plugin install adr-kit@rvdbreemen-adr-kit-copilot
  $ copilot.cmd plugin marketplace remove rvdbreemen-adr-kit-copilot --force
  $ copilot.cmd plugin marketplace add ...\marketplaces\0.48.0.old
  $ copilot.cmd plugin install adr-kit@rvdbreemen-adr-kit-copilot
  undo: removing marketplace registered by this run
  $ copilot.cmd plugin marketplace remove rvdbreemen-adr-kit-copilot --force
```

Verified after the run: `copilot plugin marketplace list` now shows only `copilot-plugins` and `awesome-copilot`. The manually restored `rvdbreemen-adr-kit-copilot` registration is gone.

The reasoning recorded in the description — that `install_copilot` would skip the add because `marketplace_source_matches` recognises the listed source, leaving `added_marketplace` false so nothing would be removed on failure — did not hold. The run removed the pre-existing registration anyway, on its rollback path, and then removed the `.old` one it had added itself. So the client ends a failed run with strictly less than it started with, for the second observed time.

This also feeds TASK-166: the rollback is what registers `...\marketplaces\0.48.0.old`, and that is exactly the directory whose marker then outranks the live `0.48.0` in `_marker_roots`. The two defects compound — a failed install both dismantles the client and poisons the version the next plan reports.
---

author: Claude Opus 5
created: 2026-08-09 20:05
---
Killing the MCP server process does not work as a workaround, tested 2026-08-09 22:03. `taskkill /PID 38420 /T /F` released the lock — a rename of the plugin directory succeeded immediately afterwards — but VS Code respawned the utility service as PID 16520 at 22:03:30, seconds later, and a re-run of the handle scan shows it holding the identical set:

```
pid 16520 (Code)  ...\rvdbreemen-adr-kit-copilot\adr-kit          (5 handles)
pid 16520 (Code)  ...\rvdbreemen-adr-kit-copilot\adr-kit\skills  (2 handles)
pid 16520 (Code)  ...\rvdbreemen-adr-kit-copilot                  (1 handle)
```

`python scripts/install-agent-envs.py --clients copilot` run immediately after the kill still exited 1, and the rollback again removed the marketplace it had added. `copilot plugin marketplace list` still shows only the two GitHub defaults. So the window between killing the server and copilot finishing its directory swap is too small to exploit; the editor has to be closed, or that MCP server disabled inside it.

This strengthens the case for acceptance criterion #3 over any retry-based approach: a pre-flight rename probe would have refused this run in under a millisecond and left the registration alone, instead of failing slowly and taking the marketplace down with it — twice in one evening.
---

author: Claude Opus 5
created: 2026-08-09 20:07
---
Machine restored 2026-08-09 22:07. With VS Code fully closed (zero Code.exe processes; the plugin directory renamed on the first try), `python scripts/install-agent-envs.py --clients copilot` printed `validation: PASS (copilot)` and `ADR Kit install complete for: copilot`, exit 0.

Verified independently of the installer's own reporting, since TASK-166 shows that reporting cannot be trusted:
```
copilot plugin marketplace list -> rvdbreemen-adr-kit-copilot (Local: ...\marketplaces\0.48.0)
copilot plugin list            -> adr-kit@rvdbreemen-adr-kit-copilot (v0.48.0)
~/.copilot/config.json         -> installedPlugins[0] = adr-kit 0.48.0, enabled true, installed_at 2026-08-09T20:07:13.829Z
plugin.json on disk            -> 0.48.0
```
All three clients are now on 0.48.0, so TASK-162's acceptance criterion 7 can be revisited.

This task stays open: only the machine was repaired, not the defect. The trigger is now fully understood — an editor holding the plugin as an MCP server — which makes it reproducible on demand rather than a Windows curiosity, and makes acceptance criteria #1-#4 straightforward to implement and test.
---
<!-- COMMENTS:END -->
