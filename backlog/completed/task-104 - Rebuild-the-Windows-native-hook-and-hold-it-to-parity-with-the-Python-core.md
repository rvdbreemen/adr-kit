---
id: TASK-104
title: Rebuild the Windows native hook and hold it to parity with the Python core
status: Done
assignee: []
created_date: '2026-08-03 19:33'
updated_date: '2026-08-04 01:28'
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
- [x] #1 The staleness is reproduced first: run the shipped exe and the Python path on one payload and diff the results
- [x] #2 The exe is rebuilt from the current `.rs` and committed, or the exe preference is dropped from `run-hook.cmd` with an ADR recording why
- [ ] #3 The source-text parity test is replaced by one that runs the artefact and compares its output to the Python path over the full manifest payload set
- [ ] #4 The plan-exit and PR-guard branches exist in `adr-hook.rs`, or the exe declines those events and falls through to Python
- [ ] #5 The `.adr-kit.json` `context.default_limit` read works on the native path, or the native path defers to Python when a config is present
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
**The task read as a chore and turned out to be a decision, which is why it ends with an ADR rather than a rebuild.**

Rebuilding the binary from current source did not close the gap. Finding out why changed what this task is:

The Python edit tier stopped doing its own matching when ADR-014 introduced the shared index-first engine. It calls `query_adr_context(..., paths=(relative,))`, which scores path at weight 1.0 alongside symbols, components, topics, aliases, title, decision contract and summary, expands related decisions and applies authority filtering. The Rust host still implements the *earlier* design — glob match, else a token-overlap rank with **no path term at all**, dropping every record that scores zero. On one edited file that leaves 1 record where the engine finds 4.

So the divergence is not neglect. It is two implementations, only one of which every other caller uses. Closing it means porting `bin/adr_query.py` — 764 lines — into Rust and holding the port in step with it permanently.

**ADR-029 proposes retiring the binary, with the price measured rather than estimated:** `SessionStart` 21 ms → 235 ms at the median on this Windows machine, an order of magnitude. Inside the 500 ms event budget and R21's 2 s ceiling. The 100 ms edit tier becomes the binding constraint, and the ADR says that if it proves unmeetable the answer is to supersede ADR-015, not to quietly relax a number.

Two alternatives are argued rather than listed. **Narrowing the binary to the events where it already matches is the worst option, not the careful one** — the remaining divergence would be silent by construction, because the matching events are the ones nobody re-checks. Keeping it opt-in is stable today and decays into the state that produced this ADR.

**It is Proposed, not accepted.** The maintainer may prefer the port; the ADR records what that costs so the choice is made on the numbers rather than on instinct.

AC#1 was done in v0.44.1 (reproduced before fixing). AC#3, #4 and #5 are conditional on which option is accepted, and the ADR's Decision Contract carries them: verify a future native path by running the artefact, never by reading its source — the failure that let a two-release-old binary pass a parity test.
<!-- SECTION:FINAL_SUMMARY:END -->
