# ADR-009 Use PostgreSQL for Persistence

## Status

Accepted, 2026-04-02. Deciders: platform team.

## Context

The order service needs a durable store for order state. Writes are
transactional (an order and its line items must commit together) and reads
are mostly key lookups with a few reporting joins. Which database should the
service use?

Decision drivers:

* Transactional integrity across order and line-item tables
* Operational familiarity: the team already runs two PostgreSQL clusters
* Reporting queries need joins and aggregations

## Decision

Use PostgreSQL, because it is the only option that satisfies the
transactional-integrity driver without giving up the reporting joins, and
the team already operates it in production.

## Alternatives Considered

- **PostgreSQL (chosen).** Good, because ACID transactions and joins are
  first-class. Good, because the team already operates two clusters. Bad,
  because it adds one more stateful service per environment.
- **MongoDB.** Good, because the document model maps neatly to the order
  payload. Bad, because multi-document transactions arrived late and the
  team has no operational experience with them.
- **SQLite.** Good, because there is nothing to operate. Bad, because a
  single-writer embedded file does not fit a multi-instance service.

## Consequences

**Positive:**

- ACID transactions cover the order plus line-item write path.
- Reporting joins run in the database instead of application code.

**Negative:**

- The service now depends on a managed PostgreSQL instance per environment.
- Schema migrations need a migration tool and review step.

## Related Decisions

- Supersedes ADR-0004 (file-based order log)

## References

- [PostgreSQL documentation](https://www.postgresql.org/docs/)
