---
id: TASK-110
title: Make an unattended acceptance refuse rather than sign
status: Done
assignee: []
created_date: '2026-08-03 19:35'
updated_date: '2026-08-03 21:38'
labels:
  - lifecycle
  - correctness
dependencies: []
priority: high
ordinal: 3700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`bin/adr accept ADR-NNN` succeeds unattended. With `lifecycle.signer` configured — which is now the common case, since v0.44.1's derivation makes it the common case — it writes the user's name, a plausible reason and today's date into an immutable history entry the user never saw.

False attribution is worse than a missing one. That is R8's own argument, turned against the command that implements it.

The consent step is prose on all three clients (`skills/adr/SKILL.md:31-34`, and `clients/workflows.json`'s `adr` workflow step 6), and no hook intercepts it: `adr_hook_core:543` returns noop for any tool outside `WRITE_TOOLS`, so a Bash call to `adr accept` is injected nothing and blocked never. R14's own reading says a guarantee needs something that fires without the model choosing to.

No ADR needed: ADR-011 records the human-gated principle. What is missing is enforcement at the boundary.

**This changes the exit behaviour of a shipped command.** It needs a CHANGELOG entry that names the break, and `--auto --auto-mode auto` stays as it is, because R1 grants the init flow that exception explicitly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An unattended `bin/adr accept` refuses instead of signing, using the `--confirm` shape auto-accept's assist mode already uses at `bin/adr:686`
- [x] #2 `--auto --auto-mode auto` keeps working, because R1 grants init that exception
- [x] #3 A test asserts that accept with closed stdin and no confirmation writes nothing and exits non-zero
- [x] #4 `bin/adr signer --audit` runs somewhere real — the guardian sweep or CI — rather than existing and never being called
- [x] #5 The CHANGELOG names the behaviour change explicitly, since scripts may depend on the old exit
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
`bin/adr accept` now requires `--confirm`, checked immediately before the write.

**The presence test I reached for first is wrong on Windows, and that is worth recording.** `sys.stdin.isatty()` looked like the honest way to detect an unattended run. Measured: a subprocess with `stdin=DEVNULL` reports `isatty() == True` on Windows, because `NUL` is a character device and the C runtime answers about the device rather than about a terminal. A presence test that says "someone is there" for the null device is worse than no test, because it reads as a guarantee. The explicit flag the task specified is the right mechanism.

**What the flag buys, stated honestly.** An acceptance can no longer happen by accident — from a script written against an older interface, from CI, from an agent following a stale instruction. It does not stop a caller who deliberately passes it, and nothing at the process level could: an agent runs with the user's own terminal, working directory and environment.

**Gates run first, the flag last.** Checking the flag first would tell an author to add `--confirm` and only then tell them the record was incomplete all along — two round trips with the real problem discovered second. `tests/test_adr_lifecycle.py::test_a_broken_record_reports_the_gate_not_the_missing_flag` guards the ordering.

Callers updated: five skills, `clients/workflows.json`, `.claude/adr-kit-guide.md`, and eleven test call sites across four modules. `--auto` untouched per spec R1.

`bin/adr signer --audit` wired into the weekly guardian sweep, which is the first place it has ever run. On this repository it reports ADR-016 and ADR-017 attributed to `adr-kit`.

**Two unrelated defects surfaced while making the suite green again, both real:**

1. `tests/test_adr_lint_clarity.py` ran the acceptance gate set **without `--context-dir`**, so it was not reproducing `bin/adr accept` at all. The moment ADR-007 gained a `related` link it failed on a record that accepts cleanly. Fixed, and recorded in ADR-028's Decision Contract, since that ADR is precisely about this.
2. **12 of 28 ADRs had no retrieval metadata whatsoever** — ADR-004 among them, so the injection architecture was unfindable on a query about injection. Annotated all twelve; probes recovered. Structural cause is now TASK-118.

CHANGELOG carries the breaking change with the upgrade step.
<!-- SECTION:FINAL_SUMMARY:END -->
