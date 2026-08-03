---
id: "ADR-023"
title: "Record the Pull-Request Guard as a Fail-Closed Tier"
status: "Proposed"
date: "2026-08-03"
binding: true
gate: "adr-pr-guard-tier-v1"
documents_shipped: true
verified_in:
  - "tests/test_adr_pr_guard.py"
supersedes: []
superseded_by: null
related:
  - "ADR-004"
  - "ADR-019"
  - "ADR-024"
topics:
  - "hooks"
  - "enforcement"
  - "pull request"
aliases:
  - "PR guard"
  - "fail-closed tier"
components:
  - "lifecycle hooks"
  - "adr-judge"
symbols:
  - "adr_pr_guard"
  - "looks_like_pr_create"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-023 Record the Pull-Request Guard as a Fail-Closed Tier

## Status

Proposed, 2026-08-03.

## Status History

```yaml
status_history:
  - date: 2026-08-03
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: ADR-004 says the commit judge is the only mechanism that blocks and ADR-019 says every hook is model-free; the shipped guard is neither
    changed_via: adr-kit
  - date: 2026-08-03
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: ADR-023 narrows ADR-004's only-mechanism-that-blocks claim
    changed_via: adr-kit lifecycle
  - date: 2026-08-03
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: ADR-023 corrects ADR-019's every-hook-is-model-free premise
    changed_via: adr-kit lifecycle
  - date: 2026-08-03
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: ADR-024 applies the pull-request tier ADR-023 established
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

`hooks/adr_pr_guard.py` shipped in v0.44.0. It intercepts `gh pr create` from
the shell tool, runs `bin/adr-judge` over the branch diff, and returns
`permissionDecision: deny` when the branch violates an Accepted ADR. It is a
good mechanism and it answers R2's "before a diff becomes a PR" literally,
earlier than CI can, because CI only learns about the pull request once it
exists.

It also contradicts two Accepted decisions, and neither contradiction was
noticed when it landed.

**ADR-004, Decision point 2**, states: "`bin/adr-judge` at pre-commit (and the CI
action) remains the only mechanism that blocks. Injection hooks never block;
they steer." The guard blocks, from a hook, and it is neither of the two named
mechanisms.

**ADR-019, Context**, states: "Every hook in this kit today is deterministic,
model-free, offline, and inside the two-second budget ADR-015 makes a test
fixture contract." The guard spawns `adr-judge` with `JUDGE_TIMEOUT_S = 120`, and
`adr-judge` runs the LLM pass when one is configured. It is not model-free, not
necessarily offline, and its declared budget is 5000 ms.

Neither ADR is wrong about what it decided. ADR-004's injection architecture is
in force and correct; ADR-019's conclusion that end-of-session hooks stay silent
is in force and, as argued below, unaffected. What is wrong is a factual claim in
each — a claim that a later reader would use to reason, and would reason
incorrectly from.

That is precisely the failure ADRs exist to prevent, arriving from the inside:
the record drifted from the code, silently, in the repository whose product is
noticing exactly that.

A note on why this is a new decision rather than two supersessions. This toolkit
has no `amends` relationship — only supersession, which retires a record whole.
Superseding ADR-004 would retire the three-tier injection architecture that is
still in force; superseding ADR-019 would retire a conclusion that still holds.
Both would destroy more than they correct. So this ADR adds the tier, names the
two sentences it narrows, and links to both. That the alternative was
unavailable is itself worth recording, because the next person to find a stale
sentence in an Accepted ADR will face the same choice.

## Decision Drivers

* A pull request is outward-facing; a commit is not. The gate strength should
  reflect that.
* By the time a pull request is created, the commit gate has either passed or
  been bypassed, so a second look is not redundant.
* ADR-004's reason for refusing a fail-closed *edit* gate must be examined rather
  than assumed to extend here.
* A blocked action must remain unblockable by a human with a reason (spec R2.1).
* Not every client can enforce a denial, and where one cannot, the kit must not
  claim it does.

## Considered Options

* **Record the guard as a distinct fail-closed tier**, narrowing ADR-004's "only
  mechanism" claim and correcting ADR-019's premise.
* **Supersede ADR-004 and ADR-019** to bring both contracts up to date.
* **Remove the guard**, restoring ADR-004's Decision as written.

## Decision Outcome

Chosen option: **record the guard as a second fail-closed tier**, because the
mechanism is right and only the record is behind.

ADR-004's three fail-open injection tiers are unchanged. Its fail-closed floor
gains one sibling, and the two are distinguished by moment rather than by
strength:

* **Commit tier** — `bin/adr-judge` at pre-commit and in CI. Blocks a commit.
* **Pull-request tier** — `hooks/adr_pr_guard.py` on `gh pr create`. Blocks the
  tool call that would publish the branch.

**Why ADR-004's rejection does not extend to this moment.** ADR-004 rejected
denying *edits* to ADR-governed paths, with a specific and still-correct reason:
"Legitimate compliant edits touch governed paths constantly; a fail-closed edit
gate produces false positives and contradicts the advisory posture that the
pre-commit judge already backstops." Every clause of that turns on frequency and
on the existence of a later backstop. A pull request is created once per branch,
not constantly; and at that moment the pre-commit backstop is behind the user,
not ahead of them — the commit gate has already run, or been skipped with
`ADR_KIT_HOOK_DISABLE`, or never been installed. The sentence "blocking belongs
at commit, not keystroke" is retained in full. This is neither.

**Why ADR-019's conclusion survives its premise.** ADR-019 argues that
end-of-session hooks stay silent, and it offers two supports: that all hooks are
model-free, and that "a session does not end when the user is watching" — an
unattended moment where spend cannot be seen or refused. The first support is
false, as the guard demonstrates. The second is load-bearing and untouched, and
it is also the exact property that makes the pull-request moment *acceptable*:
the user is present, sees the guard run, and can decline. ADR-019's conclusion is
therefore not weakened by this ADR; it is sharpened. The dividing line is not
"model or no model" but "can the user see it fire and refuse it".

**Where a client cannot enforce.** Not every adapter has a permission decision to
return. Where none exists, the branch is still judged and the verdict is still
shown, labelled as advisory and naming the gates that do hold. It is never
rendered as an ordinary context injection, because that would spend the judge's
cost while telling the user their branch was checked and cleared.

### Confirmation

A branch that violates an Accepted ADR is denied at `gh pr create` on a client
that can deny, and produces a labelled advisory on one that cannot. A clean
branch passes through with nothing shown. The guard stays inside the 5000 ms its
manifest entry declares.

## Decision Contract

### Must

* Keep the three injection tiers of ADR-004 fail-open and non-blocking.
* Restrict fail-closed hook behaviour to the pull-request moment; the commit
  tier is otherwise the only blocking mechanism.
* Judge the branch diff, not a single commit, at that moment.
* Label the verdict as advisory, naming the enforcing gates, on any client that
  cannot return a permission decision.
* Record such a client as a degradation, with its user-visible effect, its
  reason and its backstop.
* Stay inside the budget the manifest declares for the event.
* Fail open on tooling failure: a guard that cannot run must not block a pull
  request.

### Must Not

* Block an edit, a prompt, a session start, or a compaction.
* Render a denial as ordinary injected context on a client that cannot enforce
  it.
* Spend on a model pass where the verdict cannot be acted on and the user has
  not asked for it.
* Extend fail-closed behaviour to a moment the user is not present for.

### Exceptions

* `ADR_KIT_HOOK_DISABLE` and the per-ADR override of spec R2.1 apply here as they
  do at commit time. A gate that cannot be overridden with a reason is overridden
  outside the tool.

### Verification

* `adr-pr-guard-tier-v1`: the named gate anchoring this decision in source,
  covering the deny path, the advisory path, and the fail-open path.

## Consequences

### Positive

* The record matches the code again on 2 points that a reader would otherwise
  have reasoned incorrectly from.
* The dividing line for a fail-closed hook is now stated as a principle —
  presence and refusability — rather than as a list of allowed mechanisms.
* ADR-019's conclusion gains a better argument than the one it shipped with.

### Negative

* Two blocking mechanisms are harder to reason about than 1. Mitigated by
  binding each to a named moment rather than to a strength level.
* This ADR corrects sentences in 2 Accepted ADRs without superseding either, so a
  reader of ADR-004 or ADR-019 who does not follow the `related` links will still
  read the stale claim. That is a limitation of having no `amends` relationship,
  and it is the reason the links are mandatory rather than optional.
* A future fail-closed moment will have to argue against this ADR's principle,
  which is the intended friction.

## Pros and Cons of the Options

### Record it as a distinct tier

* Good, because the mechanism is right and only the record lagged.
* Good, because it produces a principle instead of an allowlist.
* Bad, because the corrected sentences stay readable in their original ADRs.

### Supersede both ADRs

* Good, because each contract would then be true as written.
* Bad, because supersession retires a record whole, and both records contain
  decisions still in force.

### Remove the guard

* Good, because ADR-004's Decision would be true again with no writing.
* Bad, because it removes the only mechanism that asks the question before a
  branch becomes outward-facing.

## Open Questions

* None.

## Related Decisions

* Narrows ADR-004's claim that the commit judge is the only blocking mechanism,
  while leaving its three fail-open injection tiers and its rejection of a
  fail-closed edit gate intact.
* Corrects ADR-019's premise that every hook is model-free and offline, and
  strengthens its conclusion by replacing that premise with the one that was
  actually load-bearing.
* Builds on ADR-017, which governs when and how the judge reaches a model.

## References

* `hooks/adr_pr_guard.py` — the guard, including `JUDGE_TIMEOUT_S = 120`.
* `hooks/adapters/claude.py` — the `pr-guard-deny` branch returning
  `permissionDecision: deny`.
* `docs/adr/ADR-004-adopt-layered-adr-context-injection.md` Decision point 2 and
  its "Hard-block edits" alternative.
* `docs/adr/ADR-019-keep-the-end-of-session-hooks-deliberately-silent.md`, the
  Context paragraph beginning "The constraint that produced the silence".
* `spec.md` R2, R2.1, R17, Appendix A.1.
