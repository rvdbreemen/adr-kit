---
id: TASK-104
title: Rebuild the Windows native hook and hold it to parity with the Python core
status: To Do
assignee: []
created_date: '2026-08-03 19:33'
labels:
  - hooks
  - bug
  - windows
dependencies:
  - TASK-103
priority: high
ordinal: 3100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The shipped `hooks/bin/windows-x64/adr-hook.exe` is stale, and `run-hook.cmd` prefers the exe whenever it exists — so on the maintainer's own platform the binary silently overrides the Python hook.

Reported symptoms: it returns **three** ADRs where the Python path returns five and the release notes say five; it has no plan-exit branch and no Bash/PR branch, so both of the newest registered moments produce `b''`; and it never reads `.adr-kit.json`, so `context.default_limit` does nothing there.

**Cause.** `hooks/native/adr-hook.rs` went to `MAX_RESULTS = 5` at `cd992f3`; `hooks/bin/` was last committed at `d1d6462` (v0.40.0). `tests/test_adr_hook_result_limit.py:44` asserts parity by reading the `.rs` **source text**, so it passes over a stale binary — a test that reads source cannot see binary staleness.

Reported by a subagent; **verify by reproduction before fixing**, since it is going into a release.

No ADR needed for the rebuild. An ADR *is* needed if the answer is to stop shipping the exe: that is a distribution reversal on the platform `clients/capabilities.json` marks release-required.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The staleness is reproduced first: run the shipped exe and the Python path on one payload and diff the results
- [ ] #2 The exe is rebuilt from the current `.rs` and committed, or the exe preference is dropped from `run-hook.cmd` with an ADR recording why
- [ ] #3 The source-text parity test is replaced by one that runs the artefact and compares its output to the Python path over the full manifest payload set
- [ ] #4 The plan-exit and PR-guard branches exist in `adr-hook.rs`, or the exe declines those events and falls through to Python
- [ ] #5 The `.adr-kit.json` `context.default_limit` read works on the native path, or the native path defers to Python when a config is present
<!-- AC:END -->
