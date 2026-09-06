# ADR-001 References Heading With No Body

## Status

Accepted, 2026-04-25.

## Context

Synthetic fixture: every canonical heading is present, but References has
no body. Counting headings calls this complete; a reader gets nothing.

## Decision

This file is used as the PASS-strictly fixture in adr-lint test cases.

## Alternatives Considered

- Skip this fixture: rejected; we need a positive control.
- Reuse an existing example: rejected; tests should not depend on documentation files.

## Consequences

The test suite has a stable PASS baseline.

## Related Decisions

- None.

## References

