---
id: "ADR-026"
title: "Record the Combined Audit Command and Its Five-Way Exit Contract"
status: "Accepted"
date: "2026-08-04"
binding: false
gate: null
documents_shipped: true
verified_in:
  - "tests/test_adr_audit_command.py"
supersedes: []
superseded_by: null
related:
  - "ADR-009"
topics:
  - "audit"
  - "cli contract"
  - "exit codes"
aliases:
  - "adr-audit"
  - "adr-discover"
components:
  - "adr-audit"
  - "adr-discover"
symbols:
  - "EXIT_ADR_QUALITY"
  - "EXIT_CODE_VIOLATION"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-026 Record the Combined Audit Command and Its Five-Way Exit Contract

## Status

Accepted, 2026-08-04.

## Status History

```yaml
status_history:
  - date: 2026-08-03
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: the exit contract lives only as constants and the name adr-audit changed meaning without a record
    changed_via: adr-kit
  - date: 2026-08-03
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: ADR-026 depends on ADR-009's split between authoring-time and merge-time gates
    changed_via: adr-kit lifecycle
  - date: 2026-08-04
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Accepted by the maintainer in the spec gap-analysis review; the decision stands, its gate and binding flag follow when the implementation ships.
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

`bin/adr-audit` means something different than it did a week ago. It used to be
the deterministic repository scanner that `/adr-kit:init` runs to discover
candidate decisions. That scanner is now `bin/adr-discover`, and the name
`adr-audit` belongs to the combined lint-and-judge command of spec R15.

Two things about that are recorded nowhere.

**The rename.** Two commands called audit that audit different things is exactly
the ambiguity ADRs exist to prevent, and the resolution — one of them was
renamed to what it does — is currently visible only as a file that moved.

**The exit contract.** `EXIT_OK = 0`, `EXIT_CODE_VIOLATION = 1`,
`EXIT_TOOLING = 2`, `EXIT_ADR_QUALITY = 3`, `EXIT_BOTH = 4`. Those five values
are the reason the command exists in the shape it does. "Your ADRs are not good
enough" and "your code violates an ADR" are different problems with different
owners; a caller that receives a single non-zero exit learns that something is
wrong and nothing about who should fix it.

A contract that lives only as five constants in one file is a contract the next
person collapses to zero-or-one, reasonably, because nothing told them the
distinction was load-bearing. CI jobs will branch on these values; once they do,
collapsing them is a breaking change nobody will recognise as one.

## Decision Drivers

* A caller must be able to route a failure to its owner without parsing output.
* Lint and judge are meaningless apart: a clean judge over vague ADRs proves
  nothing, because vague rules cannot be violated.
* A command with no arguments must not answer a question it was not asked.
* The whole-codebase question — does today's code obey today's decisions — cannot
  be answered by any per-diff gate.

## Considered Options

* **Five exit codes, one command, two modes.**
* **Two exit codes** (success, failure) with the distinction in the output text.
* **Two separate commands**, each with its own exit code.

## Decision Outcome

Chosen option: **one command running both halves, with five exit codes**.

`/adr-kit:audit` runs the lint over the ADRs and the judge over the code in one
pass, in one of two modes:

* **Diff mode** — the default in a hook or pull-request context. Judge the change
  at hand.
* **Whole-codebase mode** — judge everything, not only what changed. Mechanically
  this is a diff against the empty tree, so every line reads as added and
  `forbid_pattern` applies repository-wide; `require_pattern` already reads a
  snapshot and needs no change. Such a diff is large, which is what the separate
  diff budget exists for.

The five exits are the contract:

| code | meaning | owner |
|---|---|---|
| 0 | on course | — |
| 1 | the code violates an ADR | whoever wrote the code |
| 2 | the tooling failed to answer | whoever installed it |
| 3 | the ADRs are not good enough | whoever wrote the ADRs |
| 4 | both 1 and 3 | both |

**A bare invocation is refused with exit 2**, pointing at `bin/adr-discover`.
Before that refusal it read closed standard input, found an empty diff, and
reported "on course" — a green answer to a question nobody asked, which is the
worst possible output for a governance tool. Exit 2 is correct there because the
fault is in how the command was called, not in the code or the ADRs.

**Why one command rather than two.** Anyone asking "are we still on course?"
needs both answers at once and should not have to know they come from two
binaries. Splitting them puts the burden of remembering to run both on the person
least likely to know that they interact.

### Confirmation

Each of the five exit codes is produced by a fixture that provokes exactly that
condition. A bare invocation with closed standard input exits 2 and names
`bin/adr-discover`. Whole-codebase mode over a repository with a rule added after
a file was written reports that file.

## Decision Contract

### Must

* Run both the lint and the judge in a single invocation.
* Return 0, 1, 2, 3 or 4 according to the table above, and nothing else.
* Refuse a bare invocation with exit 2, naming the discovery command.
* Implement whole-codebase mode as a diff against the empty tree, bounded by the
  declared diff budget.
* Keep `bin/adr-discover` the name of the init-time repository scanner.

### Must Not

* Collapse the ADR-quality failure and the code-violation failure into one exit
  code.
* Report success when no mode was selected.
* Reuse the name `adr-audit` for anything but the combined command.
* Exceed the diff budget silently; a truncated whole-codebase run must say what
  it dropped.

### Exceptions

* None.

### Verification

* `adr-audit-exit-contract-v1`: the gate this decision is to be anchored by. It
  does not exist yet, so `gate` is null and `binding` is false: a frontmatter
  that declares enforcement it cannot deliver is worse than one that admits the
  gap. Both fields flip back together when the gate ships. It asserts each of
  the five exit codes against a fixture, so the contract is enforced rather
  than described.

## Consequences

### Positive

* A CI job can route a failure to its owner from the exit code alone, with no
  output parsing.
* The 2 halves of the question are asked together, which is the only way either
  answer means anything.
* The rename is on record, so `adr-audit` cannot quietly drift back to meaning
  discovery.

### Negative

* 5 exit codes are more than most tools have, and a caller that treats non-zero
  as one thing gets no benefit from them. That caller is no worse off than with
  2 codes.
* Whole-codebase mode produces a large diff by construction, which is why the
  budget exists and why exceeding it must be reported rather than truncated.
* The command name changed meaning once already. Anyone with the old
  `adr-audit` in a script gets the new behaviour, which is why the bare
  invocation refuses instead of guessing.

## Pros and Cons of the Options

### Five codes, one command

* Good, because a caller can route a failure without parsing output.
* Good, because the two halves cannot be run apart by accident.
* Bad, because five codes are unusual and need documenting.

### Two exit codes

* Good, because it matches what every other tool does.
* Bad, because the caller learns nothing about who should fix it.

### Two separate commands

* Good, because each has an obvious single responsibility.
* Bad, because the person who most needs both answers is the least likely to
  know they interact.

## Open Questions

* None.

## Related Decisions

* Governed by ADR-009, which settles which gates are authoring-time and which are
  merge-time; this decision does not change that split, it only makes the
  combined command able to express both outcomes.
* Consumes the enforcement engine ADR-004 established as the fail-closed floor.

## References

* `bin/adr-audit` — the five exit constants and the bare-invocation refusal.
* `bin/adr-discover` — the renamed init-time scanner.
* `spec.md` R15, including the whole-codebase-as-empty-tree interpretation and
  the requirement that exit behaviour distinguish the two failures.
