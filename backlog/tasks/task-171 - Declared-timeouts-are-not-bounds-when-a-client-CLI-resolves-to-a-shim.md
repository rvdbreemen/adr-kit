---
id: TASK-171
title: Declared timeouts are not bounds when a client CLI resolves to a shim
status: Done
assignee: []
created_date: '2026-08-10 17:01'
updated_date: '2026-08-10 21:54'
labels:
  - bug
  - windows
  - subprocess
  - adr-drift
dependencies: []
references:
  - clients/installer/smoke.py
  - bin/adr_doctor_probes.py
  - scripts/install-agent-envs.py
  - >-
    docs/adr/ADR-010-certify-three-native-cli-clients-through-one-outcome-contract.md
modified_files:
  - clients/installer/bounded.py
  - clients/installer/smoke.py
  - scripts/install-agent-envs.py
  - bin/adr_doctor_probes.py
  - scripts/client_generation_model.py
  - tests/test_bounded_runs.py
  - tests/test_client_doctor.py
  - tests/test_release_allowlist.py
priority: medium
ordinal: 15000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Measured during TASK-167, on this machine, against primary sources.

`subprocess.run(..., timeout=N)` does not bound anything once a descendant outlives the direct child. CPython 3.12.9's `run()` does:

```python
except TimeoutExpired as exc:
    process.kill()
    if _mswindows:
        exc.stdout, exc.stderr = process.communicate()   # no timeout
```

and `Popen.kill` on Windows is `TerminateProcess(self._handle, 1)` — one handle, no job object, no tree kill. So the timeout kills the shim and then waits, without a bound, for a grandchild that still holds the output pipe.

A/B measurement, `timeout=2`, an 8-second grandchild:

```
direct child (no shim):  2.03 s
via `cmd /c <child>`  :  8.18 s
```

This matters because a client CLI resolving to a `.CMD` shim is normal, not exotic. On this machine `shutil.which` gives `copilot -> C:\nvm4w\nodejs\copilot.CMD`, whose body runs `node npm-loader.js`, which `spawnSync`s the real binary. `claude` and `codex` are `.EXE` here only because they were installed natively; for an npm install they are shims too. So whether a declared timeout holds depends on how the reader installed their client.

The affected call sites, in descending severity:

1. `clients/installer/smoke.py:115` — `cmd.exe /d /c <wrapper> session-start`, `timeout=30`. A literal shim parent with a Python grandchild, on the install hot path.
2. `bin/adr_doctor_probes.py:16` via `_native_deep`, `timeout=10`. False whenever the client is a shim.
3. `scripts/install-agent-envs.py:59` `_run`, `timeout=120`. Every client-CLI mutation flows through it.
4. `scripts/probe-client-events.py:62` and `:82`. Human-run, not a build path.

TASK-165 and TASK-167 closed the stdin precondition at all of these, which turns a permanent wait into a merely long one. Neither restored the bound.

Why this is not cosmetic: ADR-010 (Accepted, binding) describes these probes as bounded, and `bin/adr_doctor_probes.py`'s own first line says the same. Both claims are false on Windows behind a shim. An Accepted ADR that states a property the code does not have is exactly the drift this kit exists to prevent.

Worth weighing when implementing: a bounded runner that creates the child in a Windows job object and terminates the job, versus `Popen` plus explicit `communicate(timeout=...)` with a hard second-stage kill, versus accepting the unbounded recovery and documenting it honestly in ADR-010 instead. The third is legitimate if the others cost more than they are worth — but then the ADR and the docstring have to change.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A declared timeout on a call that starts a third-party CLI is either a real bound, or ADR-010 and the module docstrings stop claiming it is
- [x] #2 The chosen approach is demonstrated against the reproduction in this task: a shim parent with a grandchild that outlives the kill
- [x] #3 clients/installer/smoke.py, bin/adr_doctor_probes.py and scripts/install-agent-envs.py all follow whichever rule is chosen
- [x] #4 Regression coverage pins the behaviour without requiring an 8-second sleep in the suite
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The claim was made true rather than softened. ADR-010 needed no change.

`clients/installer/bounded.py` kills the whole process tree on timeout - `taskkill /T /F` on Windows, `killpg` elsewhere with the child in its own session - and bounds the drain that follows, so `TimeoutExpired` is the only way out. All three sites that start a client CLI or a packaged runtime use it: `clients/installer/smoke.py` (the hook smoke test, cmd.exe with a Python grandchild), `scripts/install-agent-envs.py` `_run` (every client-CLI mutation), and `bin/adr_doctor_probes.py` `_command` (deep doctor). One implementation, so bounded.py joined RUNTIME_SUPPORT_FILES and ships into the generated codex/ and copilot/ trees.

**Measured against the reproduction this task recorded**, not an approximation of it - `cmd.exe /d /c` on a `.cmd` that starts a Python grandchild, `timeout=1`:

```
subprocess.run   returned after 25.22s | grandchild ran to its own end
run_bounded      returned after  1.65s | tree gone
```

The second column matters as much as the first: returning quickly while leaking a grandchild would not be a fix. A separate probe counted surviving processes by command line and found none after run_bounded.

Two measurements were discarded along the way rather than interpreted. One filtered on a marker that lived in the script file instead of the command line; the other counted its own PowerShell query. Both reported "0", which reads as success.

**Two call sites keep plain `subprocess.run` deliberately**, recorded so the enumeration is not silently partial: `smoke.py` `_validate_mcp_process` and `adr_doctor_probes.py`'s MCP probe both start `sys.executable` directly with `input=` piped. No shim, no grandchild, so the timeout binds - the same reasoning that cleared `project_setup.py` in TASK-167. They also use `input=`, which `run_bounded` deliberately does not offer.

**Coverage** (criterion 4, without an 8-second sleep): `tests/test_bounded_runs.py`, 4 tests in 5.7s. A 3-second grandchild against a 1-second timeout is the smallest gap that separates bounded from unbounded. One test pins the defect itself - plain `subprocess.run` must still take the full grandchild lifetime on Windows - so the fix cannot be quietly reverted, and it fails loudly with a pointer to bounded.py if CPython ever changes this.

Two things the review turned up and fixed: the first test used a Python parent rather than a real `.cmd` shim, which is not the mechanism under test; and `_kill_tree` could leave through an unexpected exception if `taskkill` failed to start, in a function whose whole purpose is removing unpredictability.

Full suite: 1786 passed, 12 skipped, 0 failed. An earlier run reported 59 failures; all five affected files pass in isolation (79 passed) and none touched bounded, the installer or the doctor - it was contention from nine concurrent python processes, the same artefact seen twice before this evening.
<!-- SECTION:FINAL_SUMMARY:END -->
