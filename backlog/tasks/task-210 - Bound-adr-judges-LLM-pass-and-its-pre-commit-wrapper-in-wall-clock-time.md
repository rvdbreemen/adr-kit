---
id: TASK-210
title: Bound adr-judge's LLM pass and its pre-commit wrapper in wall-clock time
status: To Do
assignee: []
created_date: '2026-10-03 13:05'
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
- [ ] #1 It is established whether a hung or long LLM pass is a cause of a multi-hour run (reproduced, or ruled out with evidence)
- [ ] #2 The whole LLM pass has a wall-clock ceiling, and so does adr-judge-precommit's adr-judge run
- [ ] #3 On Windows a timed-out host CLI is killed together with its child processes, so the caller does not keep waiting on the pipes
<!-- AC:END -->
