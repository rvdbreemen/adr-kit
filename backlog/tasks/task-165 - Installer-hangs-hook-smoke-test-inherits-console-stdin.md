---
id: TASK-165
title: 'Installer hangs: hook smoke test inherits console stdin'
status: Done
assignee: []
created_date: '2026-08-09 18:13'
updated_date: '2026-08-09 19:41'
labels: []
dependencies: []
modified_files:
  - clients/installer/payload.py
  - clients/installer/smoke.py
  - clients/installer/detection.py
  - scripts/install-agent-envs.py
  - tests/test_agent_installer.py
  - tests/test_release_allowlist.py
  - C4-Documentation/c4-component-agent-integration.md
priority: high
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`python scripts/install-agent-envs.py --clients claude` hangs forever at the packaged Claude hook smoke test when run from an interactive console.

Root cause: `validate_prepared_hooks` in `clients/installer/payload.py` calls `subprocess.run(...)` without `stdin=`. The child inherits the console stdin, and `hooks/adr-hook.py` blocks on `sys.stdin.buffer.read(64 * 1024 + 1)`, which never reaches EOF.

Second order: after the 30s timeout, `subprocess.run` re-enters `process.communicate()` without a timeout in its own exception handler. cmd.exe is killed but its grandchildren keep the stdout pipe open, so the call blocks indefinitely and the user only sees a stalled process instead of an error.

Reproduced on Windows: without `stdin=subprocess.DEVNULL` it hangs; with it, the hook returns exit 0 in 0.4s.

`clients/installer/detection.py:28` has the same unguarded stdin inherit. Not observed to hang, but same class.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 validate_prepared_hooks passes stdin=subprocess.DEVNULL so the hook smoke test cannot block on inherited console stdin
- [x] #2 detection.py subprocess call also closes stdin
- [x] #3 A regression test fails on the old code and passes on the fixed code
- [x] #4 python -m pytest -q passes in full
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reproduced on Windows: the packaged hook returns exit 0 in 0.4s with stdin=DEVNULL and hangs indefinitely without it. The regression test is an AST scan over clients/installer/*.py requiring every subprocess call to pass stdin= or input=; on the unfixed tree it names exactly detection.py:28 and payload.py:387.

Adding the fix pushed payload.py to 405 lines, over the 400-line ADR-010 budget it was already sitting exactly on. Split the activation-independent smoke probes into clients/installer/smoke.py along the seam the old docstring already named: payload.py 291 lines, smoke.py 133. packaging/public-artifacts.json lists 'clients' as a directory, so the new module ships without an allowlist change.

Acceptance test: python scripts/install-agent-envs.py --clients claude --source . --project-root . now runs to 'ADR Kit install complete for: claude' with exit 0.

Adversarial review (20 agents, 5 lenses) produced two changes beyond the original fix. First, the guard's docstring promised 'no installer subprocess may inherit the console's stdin' while it scanned only clients/installer/*.py, so it could not see scripts/install-agent-envs.py:58 — the runner every client-CLI mutation flows through. That call site now passes stdin=subprocess.DEVNULL and the entrypoint is in the scanned set. Proven by running the guard's own matcher over `git show HEAD:scripts/install-agent-envs.py`: it reports install-agent-envs.py:59 on the pre-fix source and nothing on the current one. Second, the matcher accepted stdin=None and input=None as 'present', which is exactly the broken default; an ast.Constant of None now counts as absent, verified against a synthetic module.

Scoped out deliberately, filed as TASK-167: scripts/project_setup.py:158, bin/adr_doctor_probes.py:16 and scripts/probe-client-events.py:62 are the same class with no reproduction, and widening this fix to cover them would have made the diff unreviewable.

Found while checking whether the install itself succeeded, filed as TASK-166: detection.py derives installed_version from one marketplace marker shared by all three clients, and _marker_roots sorts lexicographically so ...\0.48.0.old outranks the live 0.48.0 directory. That is why the plan says 'copilot: SKIP; installed:0.48.0' on a machine where copilot has no plugin at all.

C4-Documentation/c4-component-agent-integration.md described payload.py as 'exactly 400 lines ... smoke-test' and linked twice to payload.py:335, which is past end-of-file at 291 lines. Updated to the post-split reality, added a smoke.py node to the clients-installer subgraph, and re-pointed the MCP tool-set assertion at smoke.py:63.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The installer hung forever at the packaged Claude hook smoke test. `validate_prepared_hooks` started the hook without `stdin=`, so the child inherited the interactive console and `hooks/adr-hook.py` blocked on `sys.stdin.buffer.read(64 * 1024 + 1)` waiting for an EOF that never came. The 30s timeout did not save it: CPython's `subprocess.run` re-enters `process.communicate()` without a bound in its own `TimeoutExpired` handler (subprocess.py:561), and cmd.exe's grandchildren keep the stdout pipe open, so the user saw a stalled process and no error at all.

Fix: `stdin=subprocess.DEVNULL` at the hook smoke test, at `clients/installer/detection.py:28`, and at `scripts/install-agent-envs.py:58` — the runner every client-CLI mutation flows through. Measured on Windows: the packaged hook hangs indefinitely without it and returns exit 0 in 0.4s with it.

Because `payload.py` was sitting exactly on its 400-line ADR-010 ceiling, even the bare keyword failed the budget gate. The activation-independent smoke probes moved to the new `clients/installer/smoke.py` along the seam the old docstring already named: payload.py 291 lines, smoke.py 133, both named in the budget test. `packaging/public-artifacts.json` ships `clients` as a directory, so nothing else was needed to release it.

Regression guard: an AST scan requiring every subprocess call on the installer path to pass a non-None `stdin=`/`input=`. Verified red-on-old, green-on-new — on the pre-fix tree it names exactly `detection.py:28`, `payload.py:387` and `install-agent-envs.py:59`, and it rejects `stdin=None`/`input=None`, which are the broken default in disguise. A behavioural test cannot see this bug: under pytest fd 0 is already closed, so only an interactive console reproduces it.

Acceptance test: `python scripts/install-agent-envs.py --clients claude --source . --project-root .` runs to `ADR Kit install complete for: claude`, exit 0. Full suite: 1765 passed, 12 skipped, 0 failed in 837s, run in isolation with a dedicated `--basetemp` after three earlier runs were invalidated by concurrent pytest processes from another session.

Filed separately rather than folded in: TASK-166 (detection reports a per-client version it never read from the client; `_marker_roots` sorts lexicographically so `0.48.0.old` outranks the live `0.48.0`) and TASK-167 (three same-class subprocess calls outside the installer path, no reproduction yet). TASK-164's record was re-verified and confirmed correct.
<!-- SECTION:FINAL_SUMMARY:END -->
