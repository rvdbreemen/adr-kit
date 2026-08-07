---
id: "ADR-033"
title: "Name the User-Initiated Whole-Repository Commands as Deliberately Slower"
status: "Accepted"
date: "2026-08-06"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
topics:
  - "latency"
  - "cli"
  - "performance budget"
aliases:
  - "cli ceiling exception"
  - "whole-repository commands"
  - "user-initiated cli"
components:
  - "CLI latency ceiling"
  - "latency corpus exceptions"
symbols:
  - "adr-audit"
  - "adr-doctor"
  - "latency_ceiling_exception"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-033 Name the User-Initiated Whole-Repository Commands as Deliberately Slower

## Status

Accepted, 2026-08-06.

## Status History

```yaml
status_history:
  - date: 2026-08-05
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Three CLI paths exceed ADR-015's ceiling doing whole-repository work the user asked for; the hook side already has this distinction in ADR-031.
    changed_via: adr-kit
  - date: 2026-08-06
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Accepted decision after all four verification gates passed
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

Completing the CLI latency corpus (TASK-126) put every `bin/` entrypoint inside
ADR-015's fixture contract for the first time. That immediately surfaced three
paths measuring above the 2000 ms ceiling while doing real work. Two of them
belong to a category; the third turned out to be a defect. Measured
2026-08-05, Windows 11 / CPython 3.12.9, on this repository (327 commits, 33
ADRs):

| path | measured |
|---|---|
| `adr-audit --whole-codebase` | ~10 s |
| `adr-doctor --check` | ~6.8 s |

The corpus records them rather than budgeting or omitting them, because omitting
would let it read as full coverage — which is the defect TASK-126 set out to
fix. These two are the paths inside the contract with no decision behind them.

ADR-031 already drew the distinction that resolves this, one layer down. The
2000 ms ceiling protects a property: *a user is never made to wait for work they
did not ask for*. That is about who initiated the wait, not only about the
number of milliseconds. ADR-031 applied it to the pull-request hook; nothing
applied it to the CLI, even though the CLI is where a user types a command and
waits on purpose.

A third path, `adr-discover` in its default history-scanning form, measured
2.8 s and is **deliberately not covered here**. Its cost grew with the number of
candidate files rather than with anything the user chose: `scan_first_appearance`
ran one `git log --follow` per path, so each invocation paid a fresh git startup
and re-ran rename detection over the whole history. Batching it into a single
`git log` brought the command from 3622 ms to 938 ms, under the ceiling. A cost
that can be removed is a defect, not a category, and naming it as an exception
would have hidden the growth instead of stopping it.

## Decision Drivers

* The property ADR-015 protects is about unrequested waiting, and neither of
  these is unrequested.
* A corpus with unexplained over-ceiling rows decays into a corpus nobody
  trusts, which is worse than rows with a reason attached.
* An exception is for a cost that cannot be removed. Reaching for one before
  looking at the cost is how a ceiling stops meaning anything.
* An exception that is a name in a test is not reviewable; an exception that
  costs an ADR is.
* A cost that grows without bound is a different problem from a cost that is
  merely large, and lumping them together would hide the one that gets worse.

## Considered Options

* **Name the class of user-initiated whole-repository commands**, and require
  each over-ceiling row to reference an accepted ADR.
* **Optimise everything under the ceiling**, treating 2000 ms as absolute.
* **Declare the CLI outside ADR-015 entirely**, and keep the ceiling for hooks.

## Decision Outcome

Chosen option: **name the class**, extending to the CLI the distinction ADR-031
made for hooks.

A `bin/` entrypoint may declare a budget above 2000 ms when it does
whole-repository work the user explicitly invoked, provided an Accepted ADR
names it and the corpus row references that record. The gate resolves the
exception from the ADR, never from a list of command names in test code — the
same mechanism ADR-031 established, for the same reason.

`adr-audit --whole-codebase` and `adr-doctor --check` are covered. Both are
diagnostics a person runs deliberately and waits on, and both are bounded by the
repository they are pointed at.

`adr-discover` is **not** covered. It was fixed instead, which is the outcome
this record prefers wherever it is available: an exception is for a cost that
cannot be removed, not for one nobody has looked at yet.

Optimising everything under 2000 ms was rejected because it is not achievable
for a whole-codebase audit at any repository size worth auditing, and pretending
otherwise would produce a ceiling people route around. Declaring the CLI outside
ADR-015 was rejected because it discards the coverage TASK-126 just built.

### Confirmation

`tests/test_cli_corpus_coverage.py` fails when an over-ceiling corpus row names
no ADR, or names one that does not exist. It requires the record to **exist**,
not to be Accepted.

That distinction is deliberate. These rows are recorded findings, not declared
budgets: ADR-015's ceiling binds the `budgets` block, which a separate test holds
at 2000 ms. Demanding a signature before a measurement may be written down would
make the honest move -- recording what was measured -- the one the gate blocks. A
second check reports which exceptions are still Proposed, so a record cannot sit
unaccepted while the corpus reads as settled.

## Decision Contract

### Must

* A CLI budget above 2000 ms must carry a reference to an Accepted ADR naming
  that path.
* The exception must be resolved from the ADR record, never from a literal list
  of command names in test code.
* An exempt path must be invoked directly by the user, not reached as a side
  effect of another command.

### Must Not

* No path reached automatically — from a hook, a pre-commit gate, or another
  command — may carry a budget above 2000 ms under this record.
* No exception may be added without an Accepted ADR that names the path and
  states why.

### Exceptions

* `adr-audit --whole-codebase` and `adr-doctor --check`.

### Verification

* `adr-cli-ceiling-exception-v1`

## Consequences

### Positive

* The two remaining over-ceiling paths carry a reason a reviewer can disagree
  with, rather than sitting in the corpus unexplained.
* Requiring the ADR before the exception is what surfaced the third path as a
  defect: it had to be argued for, and the argument did not hold.
* The CLI and hook sides of ADR-015 now share one mechanism, so a reader who
  understands one understands the other.
* The gate stays real: an over-ceiling row with no ADR behind it still fails.

### Negative

* The ceiling now has exceptions on both sides, and an exception is a thing
  people reach for. The mitigation is that reaching for it costs an Accepted
  ADR, which is deliberately more expensive than editing a number.
* Batching `scan_first_appearance` gives up `--follow`, so a file that arrived
  under a different name now reports the rename rather than the original
  creation. A real loss, and a small one: the signal is about the ORDER
  subsystems appeared, and a rename does not reorder anything.
* A user who types `adr-audit --whole-codebase` waits about ten seconds. That is
  the cost being accepted; the mitigation is that they asked for it and can see
  it running.

## Pros and Cons of the Options

### Name the class

* Good, because it reuses a distinction the repository already made and tested.
* Good, because the exception is reviewable rather than implicit.
* Bad, because it grows the number of places the ceiling does not apply.

### Optimise everything under the ceiling

* Good, because the contract would stay absolute with nothing to police.
* Bad, because a whole-codebase audit cannot run in two seconds at any
  repository size worth auditing.
* Bad, because a ceiling nobody can meet is one people route around.

### Declare the CLI outside ADR-015

* Good, because it is simple and removes the tension entirely.
* Bad, because it discards the coverage TASK-126 just built, and the CLI is
  where most user-facing waiting actually happens.

## Open Questions

* None.

## Related Decisions

* ADR-015 sets the ceiling this record amends for the CLI.
* ADR-031 made the same distinction for the hook side; this extends it.

## References

* `tests/fixtures/cli/latency-corpus.json` — the `known_over_ceiling` block.
* `bin/adr_history_scan.py` — `scan_first_appearance`, batched rather than
  per-path.
* `docs/adr/ADR-031-name-the-pull-request-moment-as-a-deliberately-slower-user-initiated-event.md`

## Enforcement

```json
{
  "forbid_pattern": [],
  "forbid_import": [],
  "require_pattern": []
}
```
