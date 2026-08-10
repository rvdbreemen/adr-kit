---
id: TASK-167
title: >-
  Close the remaining inherited-stdin subprocess calls outside the installer
  path
status: Done
assignee: []
created_date: '2026-08-09 19:25'
updated_date: '2026-08-10 17:01'
labels:
  - bug
  - windows
  - subprocess
dependencies: []
references:
  - scripts/project_setup.py
  - bin/adr_doctor_probes.py
  - scripts/probe-client-events.py
  - tests/test_agent_installer.py
modified_files:
  - bin/adr_doctor_probes.py
  - scripts/probe-client-events.py
  - tests/test_agent_installer.py
  - tests/test_client_doctor.py
priority: medium
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-165 fixed the hang where a subprocess inherited the interactive console's stdin and blocked on an EOF that never came, and closed the installer path: `clients/installer/*.py` plus `scripts/install-agent-envs.py`, enforced by an AST guard in `tests/test_agent_installer.py`.

A whole-repo AST sweep (47 call sites, excluding the generated `codex/` and `copilot/` trees and `tests/`) found three more of the same class outside that path. They were deliberately left out of TASK-165: no reproduction exists for them, and widening that fix without a repro would have made its diff unreviewable.

- `scripts/project_setup.py:158` — the runner behind `/adr-kit:setup`, same shape as the installer's `_run` was.
- `bin/adr_doctor_probes.py:16` — runs the three client CLIs for `adr doctor --deep`.
- `scripts/probe-client-events.py:62` — event probing.

The hang needs two things together: a piped stdout, and a child (or a surviving grandchild) that reads stdin. On Windows the blast radius is larger than it looks: CPython's `subprocess.run` re-enters `communicate()` without a bound in its own `TimeoutExpired` handler, and behind a `.CMD` shim a grandchild keeps the pipe open — measured during the TASK-165 review, a 2-second timeout returned after 20.34 seconds.

Cleared as non-findings in the same sweep, with evidence: every in-repo stdin-reading binary (`adr-judge`, `adr-suggest`, `adr-mcp`, `adr-watch --hook`, `adr-hook.py`, `adr_regex_worker`) is already spawned with a non-None `input=`/`stdin=` or a shell pipe; `git` children never read stdin with the pager off; and `bin/adr-audit:328` is a deliberate pass-through with no `capture_output`, so it has no reader threads to deadlock.

Reproduce before fixing: each of the three needs a demonstrated blocking child, or the fix is speculative. If one cannot be reproduced, close that entry with the evidence rather than adding a defensive keyword.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Each of the three call sites is either reproduced as a real hang and fixed, or closed with recorded evidence that its child cannot block on stdin
- [x] #2 Any call site that is fixed is covered by the same guard style used for the installer path
- [x] #3 The guard's scanned set and its docstring stay in agreement after the change
<!-- AC:END -->



## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The recorded cause was not reproduced at any of the three sites. Two of the three entries were wrong, the enumeration missed one, and the change that did ship is for a different, measured defect.

**The mechanism, confirmed on this machine.** CPython 3.12.9's `subprocess.run` really does re-enter `communicate()` with no bound in its Windows `TimeoutExpired` handler, and `Popen.kill` is `TerminateProcess` on one handle - so it kills a shim and nothing below it. Measured A/B with `timeout=2` and an 8-second grandchild: 2.03s direct, 8.18s behind `cmd /c`. `timeout=` is not a bound whenever a descendant outlives the direct child. What could NOT be reproduced is a descendant blocking on stdin: under a non-interactive harness fd 0 gives immediate EOF (0 bytes in 0.13s). Only a real console shows the block.

**scripts/project_setup.py - closed with evidence, no code change.** The task cites `:158`, which is the `def`; the call is at `:159`. It spawns `git.EXE` - a real executable, no shim, no grandchild - through exactly three callers (`rev-parse --git-dir`, `config --get core.hooksPath`, `config core.hooksPath .githooks`). None reads stdin, none paginates with stdout piped, none is a network operation that could prompt. With no surviving descendant, `timeout=5` is a real bound. The task contradicted itself here: its own non-findings paragraph already cleared git children. The entry was classified by shape - a small variadic helper that looks like the installer's `_run` - rather than by what it spawns.

**bin/adr_doctor_probes.py:16 - changed, for the boundedness defect.** Reached from `_native_deep` with `[executable, "plugin", "list"]` where `executable` comes from `shutil.which`. On this machine that is `copilot.CMD`, giving the shim-plus-grandchild shape above, so the declared `timeout=10` is not a bound - which contradicts ADR-010's description of these probes as "bounded". `stdin=subprocess.DEVNULL` is partial mitigation: it removes the precondition that would make the unbounded wait permanent rather than merely long. It does not restore the bound.

**scripts/probe-client-events.py:62 and :82 - changed on weaker but sufficient grounds.** They start a third-party binary we do not control, from a human console, with stdout piped and no use for stdin. `:82` was missing from the task's enumeration and is the higher risk of the two: a full agent session with a model call and tool use, default `timeout=180`, run by a human per docs/client-support.md. That is the one environment where the stdin block manifests and neither pytest nor CI can see it.

**Enumeration checked independently.** An AST sweep over every `**/*.py` plus the extensionless `bin/` entrypoints finds 15 stdin-less subprocess calls outside `tests/`. All but the ones above spawn `git`, `gh`, or `sys.executable` running an in-repo script - no stdin readers, no shims, no grandchildren. So "three of the same class" is defensible for the class "external agent CLI behind a possible shim"; the miss was `probe-client-events.py:82`.

**Coverage.** The source guard is renamed to `test_agent_cli_subprocesses_never_inherit_console_stdin` and now scans six files, with its docstring recording why that set is exhaustive; offenders are reported by repo-relative path so two files cannot collide. A behavioural test lives where the code lives: `tests/test_client_doctor.py::test_deep_native_probe_closes_stdin` monkeypatches `adr_doctor_probes.subprocess.run` and asserts the deep native probe passes `stdin=DEVNULL` with `timeout=10`.

Adapters regenerated once (`bin/` is mirrored wholesale via COPY_ROOTS, so codex/ and copilot/ carry the probe change); `--check` reports `changed=0`. No ADR-010 budget is affected.

Follow-up filed as TASK-171: the declared timeouts on every call that starts a third-party CLI are not bounds on Windows. That is the real remaining defect, and it leaves a false claim inside an Accepted ADR until it is fixed.
<!-- SECTION:FINAL_SUMMARY:END -->
