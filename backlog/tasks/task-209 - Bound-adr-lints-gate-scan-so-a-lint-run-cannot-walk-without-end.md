---
id: TASK-209
title: Bound adr-lint's gate scan so a lint run cannot walk without end
status: Done
assignee: []
created_date: '2026-10-03 12:19'
updated_date: '2026-10-03 16:07'
labels:
  - lint
  - performance
  - windows
dependencies: []
modified_files:
  - bin/adr-lint
  - bin/adr
  - tests/test_cli_performance.py
priority: high
type: bug
ordinal: 53000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Reported: an adr-lint run (CLI or indirect, inside a Claude Code session) ran for more than 24 hours. The exact run was not found in transcripts, so the root cause of that specific run is unconfirmed.

Verified 2026-10-03 on Windows / Python 3.12:
- Full lint of this repo: 2.3 s. One binding ADR with an unresolvable `gate`: 19 s cold, 1.0 s warm; nearly all time is in `_resolve_gates_locally`, which reads up to 5000 files in full (including the 19 MB graphify-out/graph.json).
- `_iter_gate_scan_files` uses `os.walk(followlinks=False)`, which on this machine descends into directory junctions (a self-referencing junction was walked 128 levels deep until the path limit).
- The 5000 cap counts yielded files only; directories and skipped files are unbounded. `repo_root` defaults to cwd, so an unexpected cwd or a junction into a large or unreachable tree (network share, OneDrive) gives an unbounded walk or a blocking read.
- `bin/adr accept` runs adr-lint through `_run_json_tool` with no timeout.
- `git` children in adr-lint inherit the parent's stdin.

Not in scope (follow-ups): process-tree kill after a subprocess timeout on Windows; the same walk shape in bin/adr-retire; /adr-kit:lint skill text referring to CLI output while allowed-tools excludes Bash.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The gate scan does not descend into junctions or symlinked directories
- [x] #2 The gate scan stops after a fixed budget of visited entries and of wall-clock time, and a gate it could not verify is reported as not verified rather than as missing
- [x] #3 Files above a size cap are not read, and graphify-out is skipped
- [x] #4 bin/adr's lint call has a timeout and reports a timeout as an error
- [x] #5 git children in adr-lint get stdin=DEVNULL
- [x] #6 Regression tests cover the junction loop and the budget; the full suite passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Branch fix/bound-lint-gate-scan. bin/adr-lint: _is_dir_link (lstat S_ISLNK or FILE_ATTRIBUTE_REPARSE_POINT) prunes links; _scan_gates returns (found, stop_reason); budgets GATE_SCAN_MAX_FILES=5000, MAX_ENTRIES=100000, MAX_SECONDS=10, MAX_FILE_BYTES=1MiB; graphify-out skipped; unverified gate gets its own message. bin/adr: LIFECYCLE_TOOL_TIMEOUT_S=120 + stdin DEVNULL. git calls in adr-lint: stdin DEVNULL.

Measured, CLI, ADR with unresolvable gate: project with a junction to C:\Windows old 160.3 s -> new 0.5 s (gate correctly 'not found'). --repo-root C:/Windows old 42.2 s 'not found' -> new 10.8 s 'could not be verified: scan stopped after 10 seconds'.

Pre-existing, not from this change: test_lint_and_retire_meet_hard_ceiling_on_this_repo fails on adr-retire (p50 2054 ms on unmodified dev code, 2103-2153 ms on the branch; bin/adr-retire untouched). Machine load suspected; not verified on CI.

Reparse check narrowed to IO_REPARSE_TAG_MOUNT_POINT / IO_REPARSE_TAG_SYMLINK, so OneDrive placeholders and dedup volumes are still scanned. The link test creates a junction first on Windows; checked against dev's adr-lint: old found the gate through the junction, new does not.

AC#6 open: full suite 1902 passed, 4 failed. Two were codex/copilot sync (adapters not yet regenerated; pass after regeneration, in isolation). Two also fail on clean dev: adr-retire ceiling (p50 2054-2940 ms, bin/adr-retire untouched) and test_client_certification 'bundle contract date is stale'. Something in the suite wrote into codex/ and copilot/ before regeneration; not chased.

Not covered: the time budget is only checked between directories, so it cannot interrupt one read blocked on a dead share. Gates in files behind a skipped link now read as 'not found'; the message does not say links were skipped.

Next suspect for the 24 h run (unverified): adr-judge's LLM pass. adr_llm.py calls `claude -p` with a timeout per ADR, but without stdin=DEVNULL kill-tree handling, and adr-judge-precommit starts adr-judge with no timeout at all. The judge in this session took 198 s for 6 ADRs.

Committed ff3c1b8 on fix/bound-lint-gate-scan; PR #158 to dev (https://github.com/rvdbreemen/adr-kit/pull/158). No --auto: on dev only `validate` is required and it runs a subset, so wait for the full matrix.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Merged in PR #158. The adr-lint gate scan skips junctions and directory symlinks, skips graphify-out and files over 1 MiB, and stops after 100,000 entries or 10 s. A gate it could not reach is reported as "could not be verified", not as missing. `bin/adr accept` times out after 120 s, and git children get stdin=DEVNULL. Measured: a project with a junction to C:\Windows went from 160 s to 0.5 s. The full suite passes in CI (the pytest job on every PR). The two local failures seen on 2026-10-03 also failed on clean dev: the date-dependent one is fixed by TASK-211, and the adr-retire ceiling moves to TASK-212. The reported 24 h run itself was never identified; the strongest mechanism is the one TASK-210 fixed.
<!-- SECTION:FINAL_SUMMARY:END -->
