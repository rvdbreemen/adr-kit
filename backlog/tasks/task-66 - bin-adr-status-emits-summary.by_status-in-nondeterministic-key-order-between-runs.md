---
id: TASK-66
title: >-
  bin/adr-status emits summary.by_status in nondeterministic key order between
  runs
status: Done
assignee: []
created_date: '2026-07-30 21:25'
updated_date: '2026-07-30 22:09'
labels:
  - bug
  - determinism
dependencies: []
modified_files:
  - bin/adr-status
  - tests/test_adr_status_coverage.py
  - tests/test_adr_mcp.py
priority: low
ordinal: 71500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found while building the MCP dual-era conformance suite (TASK-58.3), which needed a byte-exact golden of the legacy `tools/call` output and could not get one for `adr_status`.

`bin/adr-status --format json` emits `summary.by_status` with a key order that varies **between runs of the same binary on the same input**. Verified by the TASK-58.1 implementer, who ran the unmodified HEAD three times and got three different orders — so this predates the dual-era work and is not a regression from it.

The practical cost: any consumer wanting a stable artifact — a golden test, a cached response, a diff between two runs, a hash — cannot have one. TASK-58.3 had to fall back to a structural comparison for that one frame while the other seven are byte-exact.

**Two further sources of instability were found in the same output.** These are not defects in the same sense, but anyone fixing the key order should know they exist, because fixing only the ordering will not make the output reproducible:

- `summary.avg_age_days` and `adrs[].age_days` are computed from today's real date, so a stored expectation goes stale overnight.
- `retrieval.index_error` quotes a native OS path, so the string differs between Windows and Linux.

**Fix direction.** A `sorted()` at construction of `by_status` addresses the ordering. Whether the date-derived and path-derived fields should also become stable is a separate judgement: they are honest values, and the alternative is a `--deterministic` flag or documenting that the output is not byte-comparable. Decide rather than defaulting to the smallest change.

Not urgent. It is a reproducibility defect, not a correctness one: every value is right, only their order is unstable.</description>
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `bin/adr-status --format json` produces identical `summary.by_status` key order across repeated runs on unchanged input
- [x] #2 A regression test asserts stability across at least two runs rather than asserting one specific order
- [x] #3 The date-derived and OS-path-derived fields are either made stable or explicitly documented as reasons the output is not byte-comparable
- [x] #4 tests/test_adr_mcp.py's structural comparison for the adr_status frame is revisited: tighten it to byte-exact if the output became reproducible, or leave a comment saying why it cannot be
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Root cause: `bin/adr-status:313` built `by_status` by iterating `CANONICAL_STATUSES`, which is a **set**, so key order followed `PYTHONHASHSEED`. Proven at HEAD — 5 seeds produced 5 distinct orders. Fixed with `sorted(CANONICAL_STATUSES | {"unknown"})`.

Independently re-verified after the change: `PYTHONHASHSEED` in {0, 1, 42, 1234, 99999} all yield `['accepted', 'amended', 'deprecated', 'proposed', 'superseded', 'unknown']`.

**AC3 — the other instability sources are documented, not fixed**, in `bin/adr-status`'s module docstring, with the reasons:

- `avg_age_days` / `age_days` are honest values derived from today's date. A `--today` flag would add a lying mode to a read-only dashboard for the sake of golden tests.
- `retrieval.index_error` and — a **fourth source this task did not list** — `retrieval.probe_file` (an absolute resolved path) come from the shared `adr_query` / `adr_retrieval_health` modules, which `adr-context` and `adr-doctor` also read. Normalising them here would either lie or fork the message.

**AC4 — the structural comparison in `tests/test_adr_mcp.py` stays, and now says why.** `probe_file` settles it: that frame can never become byte-comparable, so tightening it to byte-exact is not available. The edit is docstring-only in `normalised_status_payload`, recording that reason 1 is fixed while 2 and 3 stand. No code change, no golden change — the golden's stale key order at line 1051 is harmless because that frame is compared through `json.loads` plus dict equality.

**Test design matters here.** `PYTHONHASHSEED` is fixed per process, so two ordinary runs prove nothing and two random seeds can agree by luck. The regression test runs the CLI as subprocesses under five explicitly different seeds and compares the orders *between* runs, never against a hard-coded list. Teeth verified by reverting the fix in a scratch copy: 5 distinct orders under those same seeds.</finalSummary>
<!-- SECTION:FINAL_SUMMARY:END -->
