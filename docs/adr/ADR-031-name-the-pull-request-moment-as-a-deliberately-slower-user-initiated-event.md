---
id: "ADR-031"
title: "Name the Pull-Request Moment as a Deliberately Slower User-Initiated Event"
status: "Accepted"
date: "2026-08-05"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
topics:
  - "latency"
  - "pull request"
  - "hooks"
  - "performance budget"
aliases:
  - "pr-create budget"
  - "pull-request ceiling exception"
  - "user-initiated event"
components:
  - "hook latency ceiling"
  - "pull-request guard budget"
symbols:
  - "pr-create"
  - "latency_budget_ms"
  - "adr_pr_guard"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-031 Name the Pull-Request Moment as a Deliberately Slower User-Initiated Event

## Status

Accepted, 2026-08-05.

## Status History

```yaml
status_history:
  - date: 2026-08-05
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: ADR-015's 2000 ms ceiling assumes an event the user does not initiate; the pull-request guard is one the user asks for and waits on.
    changed_via: adr-kit
  - date: 2026-08-05
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: "Maintainer accepted: the pull-request moment is user-initiated, so the ceiling may be exceeded there when an ADR names it."
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

ADR-015's Decision Contract says, under **Must Not**: "No deterministic
user-facing path may carry a hard budget above 2000 ms." Its **Must** requires
every CLI *or hook* path to keep a budget entry in a committed latency fixture,
and its References name `hooks/manifest.json` as the per-event hook budget file.
So the hook manifest is inside ADR-015's scope, in ADR-015's own words.

`hooks/manifest.json` gives `pr-create` a `latency_budget_ms` of 5000. It is the
only one of the eight events above the ceiling; the other seven read 500, 500,
100, 100, 100, 250 and 500.

The divergence is pre-existing: introduced by commit 323a38a and shipped to
users in v0.44.0. The v0.44.1 hotfix added `runner_timeout_sec: 5` to the same
entry, but that is a different quantity -- a kill timeout, not a latency budget.
`session-start` carries `runner_timeout_sec: 5` against a 500 ms budget, so the
two numbers were never meant to match.

**Why it went unnoticed is the more useful finding: nothing enforces the hook
side of ADR-015.** The ADR's Enforcement block has exactly one rule, a
`require_pattern` for `hard_timeout_ms` against
`tests/fixtures/cli/latency-corpus.json`. `tests/test_hook_performance.py`
contains no reference to the ceiling at all. A 5000 ms hook budget could land,
ship, and pass every gate -- which is exactly what happened.

The moment itself is genuinely unlike the other seven. `session-start`,
`pre-tool-use` and the rest fire as a side effect of something the user is
already doing; a slow one is dead time they did not ask for. `pr-create` fires
because the user typed `gh pr create` and is waiting for a pull request. The
guard runs the ADR judge over the branch before the request is opened, and a
judge that cannot finish is a guard that does not guard.

The alternative is to bring `pr-create` under 2000 ms, which means the branch
judge cannot run an LLM pass at that moment. ADR-015 already excepts opt-in LLM
passes, but the guard runs its declarative pass by default, so it does not fall
under that exception as written.

## Decision Drivers

* A ceiling with one silent exception is worse than a ceiling with one named
  exception: the first decays, the second is reviewable.
* The property ADR-015 protects is that a user is never made to wait for work
  they did not ask for -- which is about *who initiated the wait*, not only about
  the number of milliseconds.
* Whatever is decided, the hook side of the ceiling must actually be enforced,
  or the next 5000 ms entry lands the same way this one did.
* Removing the LLM pass from the pull-request moment removes the one place where
  a missing or violated decision is caught before review.

## Considered Options

* **Name the pull-request moment as a deliberately slower, user-initiated
  event**, and enforce the ceiling on every other hook entry.
* **Bring `pr-create` under 2000 ms**, accepting that the branch judge cannot
  run an LLM pass there.
* **Leave it undecided** and let the gate exempt `pr-create` by name without a
  record.

## Decision Outcome

Chosen option: **name the pull-request moment as a deliberately slower,
user-initiated event**, because the property ADR-015 protects is not violated
here, and lowering the budget would remove the check rather than speed it up.

The distinction this record adds to ADR-015 is explicit: the 2000 ms ceiling
binds every event that fires as a side effect of other work. An event the user
initiates directly, and whose result they are waiting for, may declare a larger
budget provided an Accepted ADR names it and the number is bounded.

`pr-create` is the only such event today. Its budget stays at 5000 ms, matching
the `runner_timeout_sec: 5` the client already enforces.

The exemption is not a name in a test. The gate resolves it from an Accepted ADR
that names the event, so an entry above the ceiling with no ADR behind it fails
-- which is what makes this different from the third option.

### Confirmation

A test asserts ADR-015's ceiling against every `latency_budget_ms` in
`hooks/manifest.json`, and every entry above it must be named by an Accepted ADR
carrying this exemption. A synthetic manifest with an unnamed over-ceiling entry
fails that test.

## Decision Contract

### Must

* Every `latency_budget_ms` in `hooks/manifest.json` must be at or below 2000 ms
  unless an Accepted ADR names that event as user-initiated.
* An exempt event's budget must be bounded by the `runner_timeout_sec` the
  client actually enforces, so the declared number and the kill timeout agree.
* The exemption must be resolved from the ADR record, never from a literal list
  of event names in test code.

### Must Not

* No event that fires as a side effect of other work may carry a budget above
  2000 ms, regardless of what it does.
* No exemption may be added without an Accepted ADR that states which event and
  why.

### Exceptions

* `pr-create` is the one exempt event, on the grounds stated above.

### Verification

* `adr-hook-ceiling-v1`

## Consequences

### Positive

* The hook side of ADR-015 becomes enforced for the first time, so the next
  over-ceiling entry fails instead of shipping.
* The one existing exception is documented with its reasoning rather than
  surviving as an unexplained number.
* The branch judge keeps the LLM pass at the moment it is most useful.

### Negative

* The ceiling now has an exception, and an exception is a thing people reach
  for. The mitigation is that reaching for it costs an Accepted ADR, which is
  deliberately more expensive than editing a JSON number.
* A user who types `gh pr create` may wait up to five seconds. That is real, and
  it is the cost being accepted; the mitigation is that they initiated the wait
  and can see it happening.
* `spec.md` contradicts itself on this point today -- R21 at `spec.md:625-628`
  versus `spec.md:660` -- and three shipped ADRs reason from the 5000 ms as if it
  were already legitimate. Those must be reconciled with this record, or the
  contradiction survives the fix.

## Pros and Cons of the Options

### Name the moment as user-initiated

* Good, because it keeps the check where it catches the most.
* Good, because it forces the hook side of the ceiling to be enforced.
* Bad, because a named exception is still an exception, and the category could
  be stretched later.

### Bring pr-create under 2000 ms

* Good, because the contract stays absolute with no exception to police.
* Bad, because the branch judge cannot run an LLM pass in under two seconds, so
  the check is not made faster -- it is removed.
* Bad, because it treats a wait the user asked for as identical to one they did
  not.

### Leave it undecided

* Good, because it costs nothing today.
* Bad, because the gate would carry an unexplained exemption, which is precisely
  the silent-divergence failure this record exists to close.

## Open Questions

* None.

## Related Decisions

* ADR-015 sets the ceiling this record amends.
* ADR-023 records the pull-request guard as a fail-closed tier.
* ADR-030 recalibrates the seven events this record leaves alone.

## References

* `hooks/manifest.json` -- the `pr-create` entry, `latency_budget_ms: 5000`.
* `docs/adr/ADR-015-enforce-a-two-second-deterministic-latency-budget-as-a-test-fixture-contract.md`
* `tests/test_hook_performance.py` -- carries no ceiling assertion today.
* Commit 323a38a -- where the 5000 ms entry was introduced.

## Enforcement

```json
{
  "forbid_pattern": [],
  "forbid_import": [],
  "require_pattern": []
}
```
