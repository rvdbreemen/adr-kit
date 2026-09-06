# ADR-001 References Left On The Placeholder

## Status

Accepted, 2026-04-25.

## Context

Synthetic fixture: References still carries the placeholder adr-migrate
writes when it adds a missing heading. That is a hole, not content.

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

- TODO: add verifiable references.
