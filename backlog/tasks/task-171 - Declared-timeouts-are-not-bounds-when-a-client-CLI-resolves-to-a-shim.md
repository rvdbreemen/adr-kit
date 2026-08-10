---
id: TASK-171
title: Declared timeouts are not bounds when a client CLI resolves to a shim
status: To Do
assignee: []
created_date: '2026-08-10 17:01'
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
- [ ] #1 A declared timeout on a call that starts a third-party CLI is either a real bound, or ADR-010 and the module docstrings stop claiming it is
- [ ] #2 The chosen approach is demonstrated against the reproduction in this task: a shim parent with a grandchild that outlives the kill
- [ ] #3 clients/installer/smoke.py, bin/adr_doctor_probes.py and scripts/install-agent-envs.py all follow whichever rule is chosen
- [ ] #4 Regression coverage pins the behaviour without requiring an 8-second sleep in the suite
<!-- AC:END -->
