---
id: "ADR-009"
title: "Bound Heuristic Gates to Findings an Author Can Act On"
status: "Accepted"
date: "2026-07-18"
binding: false
gate: null
documents_shipped: true
verified_in:
  - "tests/test_adr_lint_clarity.py"
supersedes: []
superseded_by: null
related:
  - "ADR-026"
  - "ADR-028"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-009 Bound Heuristic Gates to Findings an Author Can Act On

## Status

Accepted, 2026-07-18.

## Status History

```yaml
status_history:
  - date: 2026-07-18
    status: Proposed
    changed_by: Claude
    reason: Initial proposal
    changed_via: adr-kit
  - date: 2026-07-18
    status: Proposed
    changed_by: Claude
    reason: Behavior shipped in v0.34.0; six tests pin the bounded gate
    changed_via: adr-kit lifecycle
  - date: 2026-07-18
    status: Accepted
    changed_by: Robert van den Breemen
    reason: "Human approval: records the v0.34.0 heuristic-gate scope decision after review"
    changed_via: adr-kit lifecycle
  - date: 2026-08-03
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: ADR-028 applies ADR-009's bounded-heuristic principle to the reference gate
    changed_via: adr-kit lifecycle
  - date: 2026-08-03
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: ADR-026 depends on ADR-009's split between authoring-time and merge-time gates
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

Two of the four verification gates are deterministic: completeness and
consistency are structural checks with exact answers. The other two, evidence
and clarity, are heuristics that estimate prose quality. They are off by
default for that reason, but `bin/adr accept` runs the full gate set, so a
heuristic gate is a hard precondition for accepting any record.

That makes a heuristic false positive more than noise. It becomes an
unsatisfiable acceptance condition.

The clarity gate flagged three-to-five-letter capitalized words that never
appear immediately followed by a parenthesis, and failed a record at three or
more distinct hits. Three of its rules misfired at once:

1. It scanned the whole file, including YAML frontmatter. A title such as
   `"JSON ADR Graph Index for Agent Retrieval"` contributed `JSON` and `ADR`
   as unexplained terms. Neither can carry an inline expansion, because
   frontmatter is metadata, not prose.
2. It recognized only `ACRONYM (expansion)`. The equally normal
   `command-line interface (CLI)` was read as an unexplained hit, so an author
   who had already explained the term was penalized for word order.
3. It required expansion of vocabulary the toolkit itself uses everywhere,
   including `ADR`. Expanding those inline would degrade the record, not
   improve it.

ADR-007 hit all three. Its unexpanded set was `ADR`, `CLI`, `INDEX`, `JSON`,
`MADR`, and `MCP`, of which `ADR`, `INDEX`, and `JSON` came from the
frontmatter, the heading, and the filename. Three or more distinct hits
therefore remained no matter what the author wrote. `bin/adr accept ADR-007`
reported:

```
adr: acceptance blocked: strict lint failed: {"fail": 1, "pass": 0, ...}
```

The only way to accept the record was to rename it, which would have contorted
a permanent decision to satisfy a heuristic. The gate's own docstring promises
it fires only on acronyms "without an obvious expansion", so this was a defect
against its stated intent rather than a policy the record violated.

A related reporting defect confirmed the gate was not being read carefully: it
returned at most five hits and then counted distinct acronyms over that
truncated slice, so a record with seven unexplained acronyms was reported as
having two.

## Decision Drivers

* A gate that gates acceptance must be satisfiable by editing the record. If no
  edit can pass it, it is a defect, not a standard.
* Accepted records are immutable. A gate must never pressure an author into
  wording that the record would not otherwise use.
* Heuristics should be conservative: a false negative costs a missed nit, a
  false positive costs a blocked decision.
* Findings must be reported accurately, or maintainers will discount the gate
  rather than fix the record.
* Loosening must be explicit and reviewable, not an arbitrary threshold change.

## Considered Options

* Bound the gate to the region and vocabulary where a finding is actionable:
  skip frontmatter, accept both expansion word orders, and skip a documented
  allowlist.
* Drop clarity and evidence from the acceptance gate set, leaving them as lint
  advisories only.
* Raise the failure threshold from three distinct acronyms to a higher number.
* Do nothing, and let authors work around the gate by renaming records or
  adding per-file overrides.

## Decision Outcome

Chosen option: **bound the gate to the region and vocabulary where a finding is
actionable**, because it restores the gate's stated intent without weakening
the acceptance bar for the prose the gate was written to catch.

Three changes, each narrow and separately reviewable:

1. YAML frontmatter is excluded. Line numbers are preserved so reported
   positions stay accurate. Frontmatter is metadata and cannot hold an inline
   expansion.
2. `expansion (ACRONYM)` counts as expanded, alongside `ACRONYM (expansion)`.
   Both are normal technical prose and neither is more explanatory.
3. A named constant, `CLARITY_ACRONYM_ALLOWLIST`, holds universal technical
   vocabulary and the terms this toolkit defines everywhere else, including
   `ADR`, `JSON`, `YAML`, `HTTP`, and `MCP`. The list is a reviewable literal,
   not a threshold to tune.

The three-distinct-acronym failure threshold is unchanged, so a record that
introduces genuinely unexplained domain vocabulary still fails. The reporting
defect is fixed separately: details stay capped at five for readability, while
the summary counts every distinct acronym.

### Confirmation

Confirm the decision with `tests/test_adr_lint_clarity.py`, which pins each
rule against the public interface:

* three unexplained, non-allowlisted acronyms still fail;
* allowlisted vocabulary passes;
* `expansion (ACRONYM)` passes;
* frontmatter acronyms are ignored;
* a seven-acronym record reports seven, not five.

A sixth test asserts that the records this repository ships satisfy their own
acceptance gate set, so the unsatisfiable condition cannot return unnoticed.

## Consequences

### Positive

* Acceptance is reachable for every well-written record, including records
  whose title contains a common acronym.
* Authors are no longer pushed toward wording that a permanent decision would
  not otherwise use.
* The allowlist states in one reviewable place which vocabulary the project
  treats as common knowledge.
* Reported counts match what the gate actually found, so findings can be
  trusted.

### Negative

* The gate is more permissive. A record that uses an allowlisted term in a
  genuinely unfamiliar sense will not be flagged. Reviewers, not heuristics,
  remain responsible for that.
* The allowlist is a judgement call and will need occasional extension. Each
  extension is a reviewable one-line change with the same effect as any other
  loosening.
* Records that previously failed clarity may now pass, so the gate's historical
  verdicts are not comparable across the v0.34.0 boundary.

## Pros and Cons of the Options

### Bound the Gate to Actionable Findings

* Good, because every change restores the gate's documented intent instead of
  trading strictness for convenience.
* Good, because the allowlist is explicit and reviewable, unlike a tuned
  threshold.
* Bad, because it adds three rules to a heuristic that was meant to be simple.

### Drop Clarity and Evidence from Acceptance

* Good, because it is the smallest change and makes acceptance agree with
  `adr-lint --strict`.
* Bad, because it removes two gates from every project's acceptance bar to fix
  a defect in one of them, and leaves the false positive live in lint and
  continuous integration.

### Raise the Failure Threshold

* Good, because it is a one-character change.
* Bad, because it does not fix the cause. Frontmatter and filename hits still
  accumulate, so a longer record reaches any threshold, and the gate becomes
  less useful for the prose it was written to catch.

### Do Nothing

* Good, because the gate stays untouched.
* Bad, because records must be renamed to be acceptable, which corrupts the
  permanent record to satisfy a heuristic.

## Related Decisions

* ADR-004 makes injection tiers fail open and keeps one fail-closed
  enforcement floor. This decision keeps a heuristic gate from behaving as an
  unsatisfiable floor.
* ADR-005 requires one semantic record shape across body profiles. The gate
  must therefore be satisfiable for every profile, not only for canonical.
* ADR-007 is the record whose acceptance the defect blocked.

## References

* `bin/adr-lint`, `gate_clarity`, `_strip_frontmatter_lines`, and
  `CLARITY_ACRONYM_ALLOWLIST`.
* `bin/adr`, `_assert_acceptance_gates`, which runs clarity as a precondition
  for acceptance.
* `tests/test_adr_lint_clarity.py`, six tests pinning the rules above.
* Commit `3961e72` (v0.34.0), which introduced the bounded gate.

## Enforcement

```json
{
  "forbid_pattern": [],
  "forbid_import": [],
  "require_pattern": [
    {
      "pattern": "CLARITY_ACRONYM_ALLOWLIST",
      "path_glob": "bin/adr-lint",
      "message": "The clarity gate must keep its reviewable allowlist rather than a tuned threshold (ADR-009)."
    }
  ]
}
```
