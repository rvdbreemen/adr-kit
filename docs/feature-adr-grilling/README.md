# ADR Grilling

This dossier describes the implemented ADR Grilling feature for ADR Kit: an
interactive layer that helps engineers and architects formulate, reconstruct,
review, complete, and revalidate Architecture Decision Records.

The feature is deliberately split into two cooperating parts:

1. Deterministic, read-only analysis establishes repository facts, lifecycle
   state, evidence, implementation links, and readiness.
2. An interactive grill asks one decision-relevant question at a time and
   records the human answers in a Proposed ADR.

The engineer or architect remains the decision maker. A grill can prepare an
ADR for acceptance, but it cannot bypass `adr accept`, the existing lifecycle,
or the four verification gates.

## Contents

- [User guide](../adr-grilling.md) — runnable grill, readiness, queue,
  acceptance, migration, and CI examples.
- [Research](01-research.md) — source material and transferable grilling
  principles.
- [Lifecycle analysis](02-lifecycle-analysis.md) — where grilling adds value,
  where it must remain advisory, and where it must not run.
- [Solution design](03-solution-design.md) — commands, readiness model,
  interaction protocol, automation, robustness, and performance.
- [Implementation plan](04-implementation-plan.md) — the epic, its subtasks,
  dependencies, and delivery waves.
- [Validation plan](05-validation-plan.md) — functional, deterministic,
  security, performance, compatibility, and release validation.
- [Benchmark report](06-benchmark-report.md) — 30-sample readiness, linkage,
  MCP, hook, CI, and client-generation evidence.
- [Final certification](07-final-certification.md) — end-to-end, compatibility,
  performance, packaging, and lifecycle release evidence.
- [Backlog task map](task-map.md) — the concrete Backlog.md task IDs and
  dependency graph.

## Product outcome

ADR Kit should become a complete decision-governance toolset for agentic coding:

- create an ADR from a subject without mistaking every implementation choice
  for architecture;
- reconstruct a decision from code, a pull request, a diff, a chat log, or a
  document;
- keep facts, human statements, inferences, and unknowns visibly separate;
- turn Proposed ADRs into active decision work instead of permanent parking;
- guide Proposed ADRs toward Accepted, Rejected, or explicitly deferred;
- revalidate Accepted decisions when their forces or implementation change;
- surface useful prompts in review, judge, guardian, hooks, and CI without
  weakening deterministic enforcement.

## Non-negotiable invariants

- Only existing lifecycle commands may mutate lifecycle state.
- Acceptance requires an explicit human confirmation in the active session,
  followed by `adr accept`.
- An Accepted ADR cannot contain unresolved open questions.
- CI and hooks do not invoke a model or require a secret.
- A possibly undocumented decision is advisory.
- CI may block only when deterministic evidence shows that a pull request
  implements an explicitly linked Proposed ADR.
- Existing lint, quality, evidence, consistency, lifecycle, hook, packaging,
  and performance guarantees remain authoritative.
- The implementation remains local, stdlib-first, cross-platform, and
  deterministic.

## Delivery status

The implementation is tracked as one Backlog.md epic with fifteen
dependency-linked child tasks. The deterministic core, all client workflows,
guardian queue, bounded signals, and CI action are complete; final
certification evidence is recorded in
[07-final-certification.md](07-final-certification.md).
