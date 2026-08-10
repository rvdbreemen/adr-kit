---
id: TASK-167
title: >-
  Close the remaining inherited-stdin subprocess calls outside the installer
  path
status: To Do
assignee: []
created_date: '2026-08-09 19:25'
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
- [ ] #1 Each of the three call sites is either reproduced as a real hang and fixed, or closed with recorded evidence that its child cannot block on stdin
- [ ] #2 Any call site that is fixed is covered by the same guard style used for the installer path
- [ ] #3 The guard's scanned set and its docstring stay in agreement after the change
<!-- AC:END -->
