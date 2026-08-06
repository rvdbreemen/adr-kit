---
id: "ADR-035"
title: "Run the Suggestion Pass by Default on the Same Terms as the Judge"
status: "Proposed"
date: "2026-08-06"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
related:
  - "ADR-001"
  - "ADR-017"
  - "ADR-024"
topics:
  - "suggestion pass"
  - "defaults"
  - "cost control"
aliases:
  - "suggest.enabled"
  - "adr-suggest default"
components:
  - "adr-suggest"
symbols:
  - "suggest.enabled"
  - "ADR_KIT_SUGGEST_DISABLE"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-035 Run the Suggestion Pass by Default on the Same Terms as the Judge

## Status

Proposed, 2026-08-06.

## Status History

```yaml
status_history:
  - date: 2026-08-06
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: The suggestion pass is off by default on the authority of a superseded record, so R2's second half effectively never runs.
    changed_via: adr-kit
  - date: 2026-08-06
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-001
    changed_via: adr-kit lifecycle
  - date: 2026-08-06
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-017
    changed_via: adr-kit lifecycle
  - date: 2026-08-06
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-024
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

`bin/adr-suggest` answers the second half of spec R2: *does this change contain
a decision nobody recorded?* It is off unless a user sets `suggest.enabled` or
exports `ADR_KIT_SUGGEST=1`.

**That default rests on a superseded record.** ADR-001 made both LLM passes
opt-in, for reasons that were correct at the time: the judge fired up to two
`claude -p --model claude-sonnet-4-6` calls per commit at roughly $0.10–$0.30,
against a pinned model the user had not chosen, with no concurrency guard and no
question asked at init.

ADR-017 revisited every one of those reasons for the judge and flipped it back
on: the model is now the host CLI's own, resolved from what the installer
recorded, with **no model flag**, so the pass costs what the user's existing
subscription already covers rather than separate metered spend against a pin.
ADR-001 is `status: Superseded, superseded_by: ADR-017`.

ADR-017 did not carry that reasoning to the second entry point. `adr-suggest`
resolves through the *same* registry — `resolve_backend` is literally
`adr-judge`'s resolver, and `bin/adr_llm.resolve_llm_backend` is shared — so
every argument ADR-017 made about cost and model identity applies to it
unchanged. What is left is a default that no live decision supports.

**The observable cost is that the check does not happen.** ADR-024 put the
suggestion at the pull-request moment on the argument that this is where a
missing decision is most worth asking about, and `tests/test_pr_suggest_nudge.py`
records the state it was fixing: the second question "happened if someone typed
`/adr-kit:review` or had individually opted into `ADR_KIT_SUGGEST`, which in
practice means it did not happen." Wiring the moment did not change that,
because the gate in front of it stayed shut.

**The advertised off-switch does not work everywhere the pass runs.**
`bin/adr-suggest:602` prints "Disable: ADR_KIT_SUGGEST_DISABLE=1" in its own
advisory. Only `templates/githooks/pre-commit:316` reads that variable. The
pull-request guard spawns `bin/adr-suggest` directly, so at that moment the
documented escape hatch does nothing at all — the same documented-but-unread
no-op shape ADR-001 was written to fix, in the same file. Off by default hides
this; on by default makes it the first thing a user reaches for.

## Decision Drivers

* A default should rest on a decision that is still in force.
* The cost argument that justified opt-in was retired for the judge by ADR-017,
  and the two entry points share one backend registry.
* A check that is off by default is a check that does not run; ADR-024 spent
  real design on a moment that the gate then closed.
* Turning a pass on raises the bar for its off-switch, which must then work on
  every path the pass runs on.

## Considered Options

* **Default the suggestion pass on**, matching ADR-017's terms, and make the
  disable switch work everywhere.
* **Leave it opt-in** and remove the pull-request nudge, accepting that R2's
  second half is a manual command.
* **Leave it opt-in** and ask at init, as ADR-001 prescribed.

## Decision Outcome

Chosen option: **default the suggestion pass on, on the same terms as the
judge**, because the reasoning ADR-017 applied to one entry point was never
answered for the other, and the two share a backend.

`suggest.enabled` defaults to `true`. `ADR_KIT_SUGGEST=1` keeps working as the
per-commit opt-in for a project that has set it `false`.

Three properties bound what "on" costs, and none of them are new:

* **No backend, no call.** `resolve_backend` returns `None` when nothing is
  configured, and `run_llm_suggest` turns that into exit 0 with a stderr note.
  A machine with no host client recorded sees no behaviour change at all.
* **No decision-shaped diff, no call.** The existing skip fires before the model
  is reached: an empty diff, or one touching only docs, markdown and lockfiles,
  returns early.
* **Never blocking.** Unchanged and non-negotiable (ADR-001's guarantee, which
  ADR-017 explicitly retained, and ADR-024 restated for the pull-request
  moment). A suggestion may not deny.

**The off-switch is made real.** `bin/adr-suggest` reads
`ADR_KIT_SUGGEST_DISABLE` itself, so the variable it advertises works on the
commit path, the pull-request path, and any direct invocation. Advertising a
switch that one caller honours is worse than advertising none.

### Confirmation

With no configuration, `adr-suggest` runs its pass rather than reporting itself
disabled. `ADR_KIT_SUGGEST_DISABLE=1` suppresses it on every path, asserted
against the script directly rather than through the pre-commit template. A
project setting `suggest.enabled: false` still switches it off.

## Decision Contract

### Must

* Default `suggest.enabled` to `true`.
* Honour `ADR_KIT_SUGGEST_DISABLE` in `bin/adr-suggest` itself.
* Keep the no-backend and non-decision skips ahead of any model call.

### Must Not

* A suggestion may never block a commit or a pull request.
* Do not advertise a switch that only one caller reads.

### Exceptions

* None.

### Verification

* `adr-suggest-default-on-v1`: the gate this decision is to be anchored by. It
  does not exist yet, so `gate` is null and `binding` is false. Both fields flip
  together when it ships.

## Consequences

### Positive

* R2's second half runs, at commit time and at the pull-request moment, without
  each user having to discover a flag.
* The default stops resting on a record that was superseded six days earlier.
* The disable variable works everywhere it is advertised.

### Negative

* Users on the host backend will see model calls they did not previously get.
  That is the intended change, and it is bounded by the two skips above; it is
  also a behaviour change that belongs in the CHANGELOG rather than only here.
* This is a default reversal, so `release_policy.default_or_hook_reversal` must
  carry this record in the certification evidence before a release ships it.
* A noisy suggestion is now something users meet by default, so the confidence
  threshold that keeps it quiet matters more than it did.

## Pros and Cons of the Options

### Default it on

* Good, because it makes the check actually run.
* Good, because it puts both entry points on one set of terms.
* Bad, because it changes behaviour for existing users on the host backend.

### Leave it opt-in, drop the nudge

* Good, because it is the smallest change and surprises nobody.
* Bad, because it discards ADR-024 and leaves R2 half-answered by design.

### Leave it opt-in, ask at init

* Good, because it is what ADR-001 prescribed.
* Bad, because ADR-017 already concluded that question is not worth asking once
  the model is the user's own; asking it for one pass and not the other is the
  inconsistency this record exists to remove.

## Open Questions

* None.

## Related Decisions

* ADR-001 set the opt-in default and is superseded.
* ADR-017 flipped the judge on the reasoning this record applies to the second
  entry point.
* ADR-024 placed the suggestion at the pull-request moment.

## References

* `bin/adr-suggest` -- the opt-in gate, and the unread `ADR_KIT_SUGGEST_DISABLE`
  at line 602.
* `templates/githooks/pre-commit:316` -- the one caller that reads it today.
* `docs/adr/ADR-017-run-the-llm-judge-by-default-on-the-host-agent-model.md`

## Enforcement

```json
{
  "forbid_pattern": [],
  "forbid_import": [],
  "require_pattern": []
}
```
