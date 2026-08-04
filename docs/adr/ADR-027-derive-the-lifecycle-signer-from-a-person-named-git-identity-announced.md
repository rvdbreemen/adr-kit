---
id: "ADR-027"
title: "Derive the Lifecycle Signer From a Person-Named Git Identity, Announced"
status: "Accepted"
date: "2026-08-04"
binding: false
gate: null
documents_shipped: true
verified_in:
  - "tests/test_adr_signer_discovery.py"
supersedes: []
superseded_by: null
topics:
  - "lifecycle"
  - "audit trail"
  - "identity"
aliases:
  - "signer"
  - "changed_by"
components:
  - "adr"
  - "adr-settings"
symbols:
  - "resolve_signer"
  - "person_shaped"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-027 Derive the Lifecycle Signer From a Person-Named Git Identity, Announced

## Status

Accepted, 2026-08-04.

## Status History

```yaml
status_history:
  - date: 2026-08-03
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: the v0.44.0 refusal broke every fresh clone and the walk-back has no decision behind it
    changed_via: adr-kit
  - date: 2026-08-04
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Accepted by the maintainer in the spec gap-analysis review; the decision stands, its gate and binding flag follow when the implementation ships.
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

Every lifecycle command writes a `## Status History` entry naming who decided.
The name lands in a record that is immutable from that point on, so getting it
wrong is not a cosmetic problem: an ADR whose history says a human accepted it
when no human did is a lie that survives the person who told it.

v0.44.0 took the strictest available position. Unless `lifecycle.signer` was set
by hand in the machine-local config, every lifecycle command refused — including
`bin/adr new`, which creates a Proposed record and decides nothing. The
consequence was immediate and total: a fresh clone failed on its first command, a
container failed, a CI runner failed. That is a breaking change delivered as a
safety measure.

The reasoning behind it was a correct rule applied too widely. spec R8.1 forbids
"a default that names the tool" — the earlier behaviour, where the toolkit wrote
`adr-kit` into the record as the decider. `git config user.name` is the opposite
of that. It is a value a human configured on this machine, and every commit in
the repository already carries it as an attribution nobody objects to.

The walk-back shipped in v0.44.1 and is in `spec.md` R8.2. No ADR records it,
which leaves the next person free to re-tighten it for the same good reason and
break a fresh clone again.

## Decision Drivers

* A name in an immutable history must be true.
* A missing attribution is better than a false one — but a refusal that stops
  `bin/adr new` prevents work rather than preventing a lie.
* The toolkit must never sign on the user's behalf.
* A machine is not a human, and R8 asks which *human* accepted.
* A name the user did not know was written is a name they cannot correct.

## Considered Options

* **Derive from a person-named git identity, announced, with a refusal for
  anything that names a machine.**
* **Refuse until `lifecycle.signer` is configured** — the v0.44.0 behaviour.
* **Fall back to a generic actor** such as `adr-kit` or `unknown`.

## Decision Outcome

Chosen option: **derive from `git config user.name` when it names a person, and
announce it**.

Resolution order, unchanged in its first two steps:

1. `--changed-by "User: <name>"` — this one command.
2. `lifecycle.signer` in `docs/adr/.adr-kit.local.json` — this machine.
3. `git config user.name`, adopted as `User: <name>` **and announced on stderr**.
4. Otherwise the command refuses.

Two properties are the whole decision, and both are testable:

**Never silently.** A derived actor is announced when it is used, naming the
source and the command that would set a different one. A name that lands in an
immutable history should never be one the user did not know was written. This is
the property that makes derivation acceptable rather than presumptuous: the user
is told, in the same breath, what was written and how to change it.

**Never a machine.** `github-actions[bot]`, `dependabot[bot]`, `GitHub Actions`,
`runner`, `jenkins`, `root`, a bare `user`, `unknown`, and `adr-kit` itself are
configured values that name a machine. They fall through to the refusal, because
R8 asks for evidence of which human accepted and a runner's name is evidence of
nothing. This is the clause that keeps the derivation honest in exactly the
environment where a false attribution would be least visible.

**At install and upgrade the signer is proposed, never assumed.**
`bin/adr signer --suggest` reads the signed-in GitHub account and the git
identity, ranks them, and shows each with its source — a proposal you cannot
trace is a proposal you cannot judge. It writes nothing; the user chooses.

**The signer stays machine-local.** A signer committed to the repository would
put one person's name on every teammate's acceptance, which is worse than no
name at all: a false attribution rather than a missing one.

### Why not the alternatives

**The v0.44.0 refusal** is what this decision walks back, and it is recorded here
as an alternative that was tried in production rather than as one that was
imagined. It optimised for never writing a wrong name and achieved it by never
writing anything, which stopped `bin/adr new` — a command that creates a Proposed
record and attributes no decision at all.

**A generic actor** is the behaviour R8.1 exists to forbid. `adr-kit` in a
`changed_by` field is the toolkit claiming to have decided, which is precisely
the lie the audit trail exists to prevent.

### Confirmation

A repository with a person-named `user.name` produces a working signer and an
announcement on stderr naming the source. A repository whose `user.name` is any
of the machine identities refuses, names why, and writes nothing.
`signer --suggest` writes nothing and shows a source for every candidate.

## Decision Contract

### Must

* Resolve the actor in the order: explicit flag, machine-local config, derived
  git identity, refusal.
* Announce a derived actor on stderr, naming its source and the command that
  would set a different one.
* Refuse an identity that names a machine rather than a person, and say which
  value was rejected.
* Keep the configured signer machine-local.
* Propose candidates at install and upgrade without writing any of them.
* Write nothing when the resolution refuses.

### Must Not

* Write a generic or tool-shaped actor into a Status History entry.
* Adopt a derived identity without announcing it.
* Store a signer in repository-tracked configuration.
* Refuse on a command that attributes no decision, where a person-named identity
  is available.

### Exceptions

* None.

### Verification

* `adr-signer-derivation-v1`: the gate this decision is to be anchored by. It
  does not exist yet, so `gate` is null and `binding` is false: a frontmatter
  that declares enforcement it cannot deliver is worse than one that admits the
  gap. Both fields flip back together when the gate ships, covering derivation,
  announcement, precedence, the machine-identity refusal, and the write-nothing
  behaviour of `--suggest`.

## Consequences

### Positive

* A fresh clone, a container and a CI runner all work again on the first command.
* The attribution is derived from a value the human configured, not invented by
  the tool.
* The 10 machine identities in the refusal list turn the environments where a
  false attribution would be least visible into environments where it cannot
  happen.

### Negative

* A user who shares a machine, or whose git identity is a shared account,
  produces an attribution that is technically true and practically uninformative.
  `lifecycle.signer` and `--changed-by` both override it, and the announcement is
  what makes the situation visible.
* The refusal list is a denylist, so an unusual machine identity — a bespoke
  service account — is adopted as a person. Mitigated by the announcement: the
  name is shown at the moment it is used.
* An announcement on every derived use is noise for a user who has read it once.
  Setting `lifecycle.signer` silences it, which is also the outcome the
  announcement is nudging towards.

## Pros and Cons of the Options

### Derive from a person-named git identity, announced

* Good, because the value was configured by a human and is already trusted for
  commit attribution.
* Good, because the announcement makes an incorrect derivation visible and
  correctable.
* Bad, because the machine-identity check is a denylist and cannot be complete.

### Refuse until configured

* Good, because no wrong name can ever be written.
* Bad, because it stopped every command on every unconfigured machine, including
  ones that attribute no decision.

### Fall back to a generic actor

* Good, because nothing ever fails.
* Bad, because it writes the exact lie the audit trail exists to prevent.

## Open Questions

* None.

## Related Decisions

* Implements spec R8, R8.1 and R8.2, and records the correction between the
  second and the third.
* Shares its machine-local-versus-tracked principle with ADR-025, which applies
  the same reasoning to execution rather than to identity.

## References

* `bin/adr` `resolve_signer`, `person_shaped`, `signer_candidates` — the
  resolution order, the machine-identity check and the ranked proposal.
* `tests/test_adr_signer_discovery.py` — the derivation, precedence, refusal and
  proposal cases.
* `spec.md` R8, R8.1, R8.2.
