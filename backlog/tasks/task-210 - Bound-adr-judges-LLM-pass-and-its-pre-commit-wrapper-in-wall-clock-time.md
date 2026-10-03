---
id: TASK-210
title: Bound adr-judge's LLM pass and its pre-commit wrapper in wall-clock time
status: Done
assignee: []
created_date: '2026-10-03 13:05'
updated_date: '2026-10-03 16:07'
labels:
  - judge
  - windows
  - performance
dependencies:
  - TASK-209
priority: high
type: bug
ordinal: 54000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Follow-up from TASK-209. The 24 h run reported there was never identified. The adr-judge LLM pass is the next suspect, based on code reading only and not reproduced:
- bin/adr-judge-precommit runs adr-judge through subprocess.run with no timeout.
- bin/adr_llm.py calls the host CLI (`claude -p`) once per ADR with timeout=llm_timeout_seconds. The total grows with the number of llm_judge ADRs, and nothing bounds the whole pass.
- On Windows, subprocess.run(timeout=) kills only the direct child. If the child has started its own processes and they still hold the output pipes, the wait after the kill can block until they exit. Not verified for claude.exe.
- Measured: in the TASK-209 session, the judge's LLM pass took 198 s for 6 ADRs, against pre_commit_timeout_ms=5000.

First reproduce the 24 h run, or rule this route out, before writing a fix.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 It is established whether a hung or long LLM pass is a cause of a multi-hour run (reproduced, or ruled out with evidence)
- [x] #2 The whole LLM pass has a wall-clock ceiling, and so does adr-judge-precommit's adr-judge run
- [x] #3 On Windows a timed-out host CLI is killed together with its child processes, so the caller does not keep waiting on the pipes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reproduced 2026-10-03 without a real LLM. A fake host CLI starts a grandchild that inherits stdout and sleeps 30-60 s. subprocess.run(capture_output=True, timeout=2) raised only after 60.3 s with the parent alive and 60.5 s with the parent exited: run() kills the child, then waits for pipe EOF with no timeout. Stdin is not the hazard (input= gives a pipe). Code bound: bin/adr-judge DEFAULT_LLM_TIMEOUT_S=120, one sequential call per target, no pass deadline; adr-judge-precommit and .githooks/pre-commit had no timeout at all.

AC#1 is partly established: the mechanism that turns a per-call timeout into an unbounded wait is reproduced. The specific 24 h run was never found in transcripts, so whether it was this mechanism remains unverified. Whether `claude -p` itself starts children that inherit stdout is unverified; 23 running claude.exe had children, but no -p run was observed.

Fix: adr_llm.run_cli (Popen, output to temp files, own session on POSIX, taskkill /T on Windows, SIGKILL to the process group on POSIX); SubprocessBackend.judge uses it. run_llm_batch gets pass_timeout_s, each call gets min(per-call, remaining), and ADRs reached after the deadline are named in the attestation as degraded. Config judge.llm_pass_timeout_seconds (default 600) is in the schema and in --show-config. adr-judge-precommit: timeout 900 s (env ADR_KIT_JUDGE_TIMEOUT_S), exit 2 with a hint. Tests in tests/test_adr_llm_bounded.py (6): 5 red before the fix, the timed-out call took 30.3 s; all green after. The LLM-related files: 167 passed. Known limit: on Windows, a grandchild whose parent already exited is outside the taskkill tree and keeps running, but the call no longer waits on it. .githooks/pre-commit still calls adr-judge without its own timeout; the pass ceiling now bounds it.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Merged in PR #164. Reproduced without a real LLM: subprocess.run(capture_output=True, timeout=2) returned only after 60 s while a grandchild held the stdout pipe. adr_llm.run_cli now writes output to temporary files and kills the process tree on timeout. judge.llm_pass_timeout_seconds (default 600) bounds the whole pass, and ADRs it does not reach are named in the degraded attestation. adr-judge-precommit gives up after 900 s and exits 2. AC#1 closes on the mechanism: a per-call timeout could become an unbounded wait, which fits a multi-hour run. Whether the specific 24 h run was this is unverified, because that run was never found.
<!-- SECTION:FINAL_SUMMARY:END -->
