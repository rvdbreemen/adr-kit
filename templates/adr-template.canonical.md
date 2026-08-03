---
id: "ADR-NNN"
title: "Short Imperative Title"
status: "Proposed"
date: "YYYY-MM-DD"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
format: "canonical"
topics: []
aliases: []
components: []
symbols: []
context_scope: "selective"
---

<!-- markdownlint-disable MD025 -->

# ADR-NNN Short Imperative Title

## Status

Proposed, YYYY-MM-DD.

## Status History

```yaml
status_history:
  - date: YYYY-MM-DD
    status: Proposed
    changed_by: user@example.com
    reason: Initial proposal
    changed_via: adr-kit
```

## Context

State the problem, constraints, and concrete evidence.

## Decision

State one concrete chosen approach and its rationale.

## Decision Contract

### Must

- State required implementation constraints.

### Must Not

- State prohibited implementation choices.

### Exceptions

- State explicit exceptions, or `None`.

### Verification

- Name the test, command, or source anchor that verifies this decision.

## Alternatives Considered

- **Alternative A.** Rejection reason.
- **Alternative B.** Rejection reason.

## Consequences

**Positive:**

- Expected benefit.

**Negative:**

- Accepted cost or risk and its mitigation.

## Open Questions

List unresolved human decisions as unchecked tasks. Accepted ADRs must have no
unresolved items.

Answer them with `bin/adr answer`, which rewrites an item as
`- [x] <question> — **Answered <date> by <signer>:** <answer>`. A checked item
is resolved, so it no longer blocks acceptance and stays in the record. Do not
delete an answered question: the reasoning is what a future reader needs in
order to re-evaluate the decision.

## Related Decisions

- None.

## References

- Add at least one verifiable local or external reference.

## Enforcement

Delete this optional section when the decision has no machine-checkable surface.

```json
{
  "forbid_pattern": [
    {
      "pattern": "\\bForbiddenSymbol\\b",
      "path_glob": "src/**/*.py",
      "message": "Use AllowedSymbol instead."
    }
  ],
  "forbid_import": [],
  "require_pattern": []
}
```
