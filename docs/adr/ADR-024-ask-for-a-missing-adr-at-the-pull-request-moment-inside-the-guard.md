---
id: "ADR-024"
title: "Ask for a Missing ADR at the Pull-Request Moment, Inside the Guard"
status: "Accepted"
date: "2026-08-04"
binding: true
gate: "adr-pr-suggest-v1"
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
related:
  - "ADR-023"
  - "ADR-034"
topics:
  - "hooks"
  - "missing decisions"
  - "pull request"
aliases:
  - "suggest nudge"
  - "PR moment"
components:
  - "lifecycle hooks"
  - "adr-suggest"
symbols:
  - "adr_pr_guard"
  - "judge_branch"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-024 Ask for a Missing ADR at the Pull-Request Moment, Inside the Guard

## Status

Accepted, 2026-08-04.

## Status History

```yaml
status_history:
  - date: 2026-08-03
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: the pull-request moment answers only half of R2; nothing asks whether the branch contains an unrecorded decision
    changed_via: adr-kit
  - date: 2026-08-03
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: ADR-024 applies the pull-request tier ADR-023 established
    changed_via: adr-kit lifecycle
  - date: 2026-08-04
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Accepted by the maintainer in the spec gap-analysis review; the decision stands, its gate and binding flag follow when the implementation ships.
    changed_via: adr-kit lifecycle
  - date: 2026-08-06
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-034
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

Spec R2 asks two questions at the moment a branch becomes a pull request: does
this change violate an Accepted decision, and does it contain a decision nobody
recorded.

Only the first is answered. `hooks/adr_pr_guard.py` runs `bin/adr-judge` over
the branch diff and denies on a violation. The second question is answered by
`bin/adr-suggest`, which runs when someone types `/adr-kit:review` or has
individually set `ADR_KIT_SUGGEST` — which means, in practice, that it does not
run.

The asymmetry matters because the two failures are not symmetric in cost. A
violated decision is at least recorded and will be caught again at merge. An
unrecorded decision is invisible from that point onward: the branch adds a
dependency, changes an interface and shifts a non-functional requirement, and
six months later the only trace is the code.

ADR-023 established the pull-request moment as a fail-closed tier and stated the
principle that makes it acceptable: the user is present, sees the hook fire, and
can refuse it. That principle also decides where this question belongs.

## Decision Drivers

* R2 has two halves and one of them never fires.
* ADR-019's rule stands: no hook may spend on an event the user cannot see fire
  and cannot refuse.
* A suggestion is not a verdict, and must never acquire the authority of one.
* Cost must be bounded and attributable to the person who caused it.
* Whatever ships must not slow down a clean branch.

## Considered Options

* **Extend the existing `gh pr create` guard** so the moment answers both halves
  of R2.
* **A `pull_request` CI workflow** running `adr-suggest` over the branch range
  and posting one self-updating comment.
* **Both**, with the guard covering agent-created pull requests and CI covering
  the rest.
* **Leave it on demand** and amend the spec, as ADR-019 did for session end.

## Decision Outcome

Chosen option: **extend the guard**, because the moment is already intercepted,
the user is already present, and the cost is already attributable.

The interception of `gh pr create` emits the missing-ADR nudge alongside the
judge verdict. A violation still denies. A suggestion never denies — it is
advisory by construction, because "this looks like an architectural decision" is
a judgement a human has to confirm, and a gate that blocks on a guess is a gate
people disable.

A branch with no candidate decisions produces nothing, so the common case is
unchanged.

**Why not CI.** A `pull_request` workflow spends on every push with nobody
present to refuse, and the bill lands on the repository owner rather than on the
author who triggered it. That is the exact premise ADR-019 rejected, and
ADR-023 restated as the dividing line for the whole kit. Choosing CI here would
mean overturning that line for convenience, in the one place where the in-session
alternative already exists.

**The cost of that choice, stated plainly.** A pull request opened by hand — from
the web interface, by a teammate not working through an agent, by a script — gets
nothing. That is a real gap, and a CI workflow is the only thing that closes it.
It is
accepted rather than mitigated, because the alternative trades a visible gap for
an invisible expense. A team that wants the CI route can add the workflow; what
this decision refuses is shipping it on by default.

### Confirmation

A branch that adds a dependency and changes an interface produces both a verdict
and a nudge at `gh pr create`. A clean branch produces neither. The nudge alone
never changes the permission decision. The combined path stays inside the 5000 ms
the manifest declares for the event.

## Decision Contract

### Must

* Emit the missing-ADR nudge from the same interception that runs the judge.
* Keep the nudge advisory: it may never deny, and may never change a verdict.
* Produce nothing when the branch carries no candidate decisions.
* Stay inside the event's declared budget with both passes running.
* Fail open: a failure in the suggest pass must not affect the judge verdict or
  the tool call.

### Must Not

* Run the missing-ADR question on an unattended event.
* Spend on a model pass the user has not seen start and cannot refuse.
* Present a suggestion in a form that reads as a verdict.
* Block a pull request on the absence of an ADR.

### Exceptions

* A project may add a `pull_request` workflow of its own. This decision governs
  what adr-kit turns on by default, not what a team may choose.

### Verification

* `adr-pr-suggest-v1`: the gate that anchors this decision. It ships in
  `tests/test_pr_suggest_nudge.py`, so `gate` carries the name and `binding` is
  true. It covers the both-signals case, the clean-branch case, and the
  advisory-never-denies case.

## Consequences

### Positive

* R2 is answered in full at the moment it names, rather than in half.
* The question arrives earlier than CI can ask it, because CI only learns of a
  pull request once it exists.
* No new unattended spend, and no new workflow for a downstream project to
  maintain. The cost stays at 0 for a clean branch and is bounded by the same
  5000 ms budget for one that is not.

### Negative

* **A hand-opened pull request is not covered.** Stated in the contract rather
  than buried: this decision trades that coverage for the absence of unattended
  cost.
* The pull-request moment now runs 2 passes instead of 1, inside one budget. The
  suggest pass is bounded by the same 5000 ms and fails open.
* A client without a shell-tool interception gets neither half of R2 at this
  moment, which is a degradation to record rather than a defect to fix here.

## Pros and Cons of the Options

### Extend the guard

* Good, because the user is present and can refuse.
* Good, because it reuses an interception that already exists.
* Bad, because it misses pull requests opened outside an agent.

### A CI workflow

* Good, because it covers every pull request regardless of origin.
* Bad, because it spends unattended and bills the repository owner.

### Both

* Good, because coverage is complete.
* Bad, because the unattended spend remains, only less often, and the ADR would
  have to argue why the exception is acceptable.

### Leave it on demand

* Good, because nothing new is spent or built.
* Bad, because half of R2 stays unanswered and the spec is bent to the code.

## Open Questions

* None.

## Related Decisions

* Builds on ADR-023, which established the pull-request tier and the
  presence-and-refusability principle this decision applies.
* Governed by ADR-017's rules on when the judge reaches a model.
* Applies ADR-019's constraint on unattended spend to a new question.

## References

* `hooks/adr_pr_guard.py` — the interception this decision extends.
* `bin/adr-suggest` — the missing-ADR pass, today reachable only on demand.
* `clients/workflows.json`, workflow id `review` — the on-demand path that exists
  and requires someone to ask.
* `spec.md` R2, R14 track 2.
