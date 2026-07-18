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

## Alternatives Considered

- **Alternative A.** Rejection reason.
- **Alternative B.** Rejection reason.

## Consequences

**Positive:**

- Expected benefit.

**Negative:**

- Accepted cost or risk and its mitigation.

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
  "require_pattern": [],
  "llm_judge": false
}
```
