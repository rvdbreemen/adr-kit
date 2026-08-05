---
id: "ADR-028"
title: "Gate the Declared Related Link and Leave the Prose One Alone"
status: "Accepted"
date: "2026-08-04"
binding: true
gate: "adr-reference-gate-scope-v1"
documents_shipped: true
verified_in:
  - "tests/test_adr_cross_references.py"
supersedes: []
superseded_by: null
related:
  - "ADR-009"
topics:
  - "lint"
  - "cross-references"
aliases:
  - "related link"
  - "reference gate"
components:
  - "adr-lint"
symbols:
  - "detect_reference_issues"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-028 Gate the Declared Related Link and Leave the Prose One Alone

## Status

Accepted, 2026-08-04.

## Status History

```yaml
status_history:
  - date: 2026-08-03
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: the asymmetry between the declared link and the prose one is deliberate and reads as an oversight
    changed_via: adr-kit
  - date: 2026-08-03
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: ADR-028 applies ADR-009's bounded-heuristic principle to the reference gate
    changed_via: adr-kit lifecycle
  - date: 2026-08-04
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Accepted by the maintainer in the spec gap-analysis review; the decision stands, its gate and binding flag follow when the implementation ships.
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

`detect_reference_issues` in `bin/adr-lint` gates the `related` frontmatter. A
link whose target does not exist is a FAIL; a link the other side does not
reciprocate is a FAIL. It deliberately does not gate the prose
`## Related Decisions` section, where a sentence naming another decision resolves
to nothing as far as the linter is concerned.

That asymmetry looks like an oversight and it is not. The first implementation
did gate the prose, and it produced **57 advisories on an ADR set with no actual
problem**. The reason is structural: `bin/adr accept` lints a single file, so
every cross-reference in that file points at an ADR the linter was not given, and
every one of them dangles.

Nothing records this. The next person to notice that prose references are
unchecked will fix the gap, in good faith, and rediscover the same 57 findings.

## Decision Drivers

* A machine-written link is a claim the machine can verify; a sentence is not.
* `bin/adr accept` lints one file, so any check requiring the whole directory
  cannot run there.
* spec R15: a blocking gate must be satisfiable by editing the record.
* Gating prose would make writing about a decision more expensive than not
  writing about it.

## Considered Options

* **Gate the declared `related` frontmatter only.**
* **Gate both**, resolving prose references against the whole directory.
* **Gate neither**, treating all cross-references as documentation.

## Decision Outcome

Chosen option: **gate the declared link, leave the prose alone**.

`related` is written by `bin/adr relate`, which writes both sides in one
transaction. That makes reciprocity a property the tool guarantees at write time
and can therefore check at read time: a one-sided link means something bypassed
the command, which is exactly the case worth catching. A dangling target means a
file was renamed or removed without the graph being updated, which is the other.

The prose section is where a human explains *how* two decisions relate — a
sentence like "narrows ADR-004's claim that the commit judge is the only
blocking mechanism". That is not a link, it is an argument that happens to
contain an identifier, and gating it punishes the writing that makes an ADR set
readable.

The reasoning is ADR-009's, applied to a second gate: bound a check to the region
and the vocabulary where a finding is actionable. There, metadata was excluded
from a prose check because metadata cannot carry an inline expansion. Here, prose
is excluded from a link check because prose is not a link.

**The declared link needs the directory, and the caller has to supply it.** A
single-file lint cannot resolve a declared link either — the target is a file it
was never given. `bin/adr accept` already solves this with `--context-dir`, which
hands the linter the sibling ADRs to resolve against while it still reports on
the one file it was asked about. That flag is therefore part of this contract
rather than a convenience: any caller reproducing the acceptance gates must pass
it, or it is not reproducing them.

This is not theoretical. Writing the first `related` link onto ADR-007 broke a
test that ran the full acceptance gate set without `--context-dir`; the record
itself accepted cleanly the whole time. The failure was in the caller, and it
would have recurred for every future cross-reference.

**What this leaves uncovered, stated plainly.** A prose reference to an ADR that
does not exist, or that was renumbered, is not caught by any gate. That is the
cost. It is bounded by the fact that a prose reference is read by a human, who
notices a broken one, whereas a declared link is read by machinery, which does
not.

### Confirmation

An ADR set where every declared link reciprocates passes with no findings. A
hand-written one-sided `related` entry FAILs. A `related` entry pointing at a
non-existent ADR FAILs. A prose sentence naming a non-existent ADR produces no
finding, and a single-file `bin/adr accept` on an ADR with prose references
produces no finding.

## Decision Contract

### Must

* Gate only the declared `related` frontmatter for existence and reciprocity.
* Keep the gate satisfiable in a single-file lint given `--context-dir`, so
  `bin/adr accept` can run it.
* Pass `--context-dir` from any caller reproducing the acceptance gate set; a
  caller that omits it is testing something else.
* Leave `## Related Decisions` prose ungated.
* Keep `bin/adr relate` the supported way to create a link, writing both sides in
  one transaction.

### Must Not

* Resolve prose identifiers as links.
* Require the whole ADR directory for a check that a single-file lint must pass.
* Fail a one-sided link silently; a half link is a FAIL with both sides named.

### Exceptions

* None.

### Verification

* `adr-reference-gate-scope-v1`: the gate that anchors this decision. Both fields flip back together when the gate ships,
  covering the dangling case, the one-sided case, and the prose-is-ignored
  case.

## Consequences

### Positive

* The graph machinery reads is verified, and the prose humans read is left free.
* `bin/adr accept` keeps working on a single file, which is what it was built to
  do.
* The 57 findings that the first implementation produced on a healthy set cannot
  recur.

### Negative

* A prose reference to a renumbered or deleted ADR is caught by no gate. Accepted
  deliberately: a human reads that sentence and a machine does not.
* The asymmetry still needs explaining to anyone reading the linter, which is why
  this record exists and why the code cites it.
* A team that wants prose references checked has no option to turn it on. Adding
  one would reintroduce the single-file problem for whoever enables it.

## Pros and Cons of the Options

### Gate the declared link only

* Good, because it verifies exactly what a machine wrote and can therefore check.
* Good, because it runs in a single-file lint.
* Bad, because prose references go unchecked.

### Gate both

* Good, because every stated relationship would resolve.
* Bad, because it cannot run in a single-file lint, which is where acceptance
  happens.
* Bad, because it makes writing about a related decision more expensive than
  staying silent about it.

### Gate neither

* Good, because it is the simplest rule to explain.
* Bad, because a half-written link would then survive, and the relationship graph
  is what the retrieval layer reads.

## Open Questions

* None.

## Related Decisions

* Applies ADR-009's principle of bounding a check to where a finding is
  actionable, to a second gate.
* Supports ADR-007's generated graph, which consumes the declared links this gate
  verifies.

## References

* `bin/adr-lint` `detect_reference_issues` — the gate and its scope.
* `bin/adr` `command_relate` — the transaction that writes both sides.
* `tests/test_adr_cross_references.py` — the cases this decision fixes.
* `docs/adr/ADR-009-bound-heuristic-gates-to-findings-an-author-can-act-on.md` — the
  principle this reuses.
