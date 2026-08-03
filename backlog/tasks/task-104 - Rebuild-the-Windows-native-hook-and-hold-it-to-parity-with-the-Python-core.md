---
id: TASK-104
title: >-
  Restore native-hook parity, or retire the binary — measured divergence is in
  the implementation, not staleness
status: To Do
assignee: []
created_date: '2026-08-03 19:33'
updated_date: '2026-08-03 20:15'
labels:
  - hooks
  - bug
  - windows
dependencies:
  - TASK-103
priority: medium
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
- [x] #1 The staleness is reproduced first: run the shipped exe and the Python path on one payload and diff the results
- [ ] #2 The exe is rebuilt from the current `.rs` and committed, or the exe preference is dropped from `run-hook.cmd` with an ADR recording why
- [ ] #3 The source-text parity test is replaced by one that runs the artefact and compares its output to the Python path over the full manifest payload set
- [ ] #4 The plan-exit and PR-guard branches exist in `adr-hook.rs`, or the exe declines those events and falls through to Python
- [ ] #5 The `.adr-kit.json` `context.default_limit` read works on the native path, or the native path defers to Python when a config is present
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude
created: 2026-08-03 20:15
---
**Partly delivered in v0.44.1; the parity half is still open.**

Reproduced and then measured against the Python oracle on this repository, first with the shipped v0.40.0 binary and again after rebuilding from current source with the README's own rustc line:

| event | native | python |
|---|---|---|
| session-start | ADR-019 | ADR-019 (byte-identical) |
| user-prompt-submit | 4 ADRs | 5 ADRs |
| pre-tool-use / Write | **1 ADR** | **4 ADRs** |
| post-tool-use / Write | 1 ADR | 4 ADRs |
| plan-exit | 0 bytes | 1900 bytes |
| pr-create, subagent-start, pre-compact | match | match |

The rebuild did **not** close the gap. `MAX_RESULTS` was 3 in the old binary and is 5 in current source, but 1-against-4 on an edit is not a cap — the edit-governance selection itself diverges. So this is a parity defect in `hooks/native/adr-hook.rs`, not the staleness the ticket assumed.

What shipped in v0.44.1: the binary is rebuilt and committed, and `run-hook.cmd` no longer prefers it. It runs only under `ADR_KIT_NATIVE_HOOK=1`, on both the Windows and the POSIX branch. That was blocking two other fixes — the dispatcher intercepted every event, so the plan-exit and PR-guard repairs would have changed nothing on Windows. `tests/test_adr_hook_dispatch_matrix.py::test_the_native_host_is_opt_in_until_it_passes_parity` guards the gate.

What is left, and it is a real choice rather than a chore: either bring the Rust host to parity — edit-governance selection, the prompt-time count, the ExitPlanMode branch, the `.adr-kit.json` `context.default_limit` read, and its own encoding behaviour, which was never checked — or retire the binary and take the subprocess-startup cost on Windows. Retiring it *is* a distribution reversal and needs an ADR; restoring the preference needs the artefact parity test this ticket already asks for.
---
<!-- COMMENTS:END -->
