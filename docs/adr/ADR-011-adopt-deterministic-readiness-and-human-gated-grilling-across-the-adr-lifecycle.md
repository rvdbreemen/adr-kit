---
id: "ADR-011"
title: "Adopt Deterministic Readiness and Human-Gated Grilling Across the ADR Lifecycle"
status: "Accepted"
date: "2026-07-20"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-011 Adopt Deterministic Readiness and Human-Gated Grilling Across the ADR Lifecycle

## Status

Accepted, 2026-07-20.

## Status History

```yaml
status_history:
  - date: 2026-07-20
    status: Proposed
    changed_by: Codex
    reason: Initial proposal
    changed_via: adr-kit
  - date: 2026-07-20
    status: Accepted
    changed_by: Robert van den Breemen
    reason: Maintainer approved the ADR Grilling plan and explicitly authorized complete TASK-45 implementation in this session
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

ADR Kit validates, indexes, enforces, supersedes, and retires Architecture
Decision Records, but its authoring workflows still assume that the rationale
arrives complete. In practice, code, pull requests, and chat logs expose what
was built while leaving intent, rejected alternatives, ownership, and accepted
consequences unresolved. The current review workflow can draft a Proposed ADR,
and guardian can flag an old or shipped proposal, but neither provides one
shared process for completing the human decision.

This gap has two costly outcomes. An agent can produce a syntactically complete
record whose rationale was inferred rather than confirmed, or a valid Proposed
record can remain unfinished after its code ships. Adding an unconstrained
model interview to hooks or continuous integration would create the opposite
problem: nondeterministic enforcement, surprise cost, latency, and false merge
blocks.

The approved Backlog epic 45 design dossier records the required boundary. Repository
facts and readiness must be computed locally and deterministically. A separate
interactive workflow may ask the engineer for intent, one dependent decision at
a time. The existing lifecycle commands and four verification gates remain the
only authority for status transitions.

## Decision Drivers

* Engineers and architects must remain accountable for architecture decisions.
* Questions answered by repository evidence must not be delegated to a human.
* Facts, human statements, inferences, and unknowns must not be conflated.
* Proposed ADRs must converge on Accepted, Rejected, or explicit deferral.
* Hooks and continuous integration (CI) must stay local, model-free, bounded,
  and deterministic.
* Existing lint, evidence, clarity, consistency, lifecycle, and reciprocal-link
  gates must not be weakened.
* Claude, Codex, and Copilot must expose the same outcome contract from one
  canonical workflow source.
* Readiness must remain useful through a command-line interface (CLI) and Model
  Context Protocol (MCP) without granting mutation authority.

## Considered Options

* Combine a deterministic readiness engine with a human-gated, one-question
  grilling workflow and retain existing lifecycle commands as mutation
  authority.
* Put the full interview in each authoring, review, guardian, and CI workflow.
* Let an agent infer missing rationale and automatically accept records above a
  confidence threshold.
* Keep the current drafting and staleness nudges without an interactive
  completion workflow.

## Decision Outcome

Chosen option: **combine a deterministic readiness engine with a human-gated,
one-question grilling workflow**, because it adds active decision support while
preserving ADR Kit's deterministic governance floor.

### Evidence model

Every input used by the grill is classified as:

* **observed** when directly supported by a cited repository or source fact;
* **human-stated** when supplied or explicitly confirmed by the engineer;
* **inferred** when reasoned from evidence but not confirmed; or
* **unknown** when neither repository evidence nor the engineer resolves it.

Only observed and human-stated information is settled. Inferences stay labelled
and unknowns become Open Questions.

### Readiness boundary

A shared stdlib-only, read-only engine returns lifecycle state, gate findings,
Open Questions, implementation-link evidence, related decisions, required
mechanical actions, required human decisions, and one of:

* `not-an-adr`;
* `needs-human-input`;
* `needs-mechanical-fix`;
* `ready-for-confirmation`;
* `accepted`;
* `rejected`; or
* `supersession-required`.

The same repository, arguments, and injected date produce stably ordered
structured output. CLI, MCP, guardian, review, hooks, and CI consume this shared
model rather than reimplementing readiness.

### Interaction and lifecycle boundary

`/adr-kit:adr <subject>` qualifies a decision and creates a Proposed record.
`/adr-kit:grill` accepts an ADR, pull request, git range, source path,
revalidation target, or the Proposed work queue. It reads repository facts
first, asks one unresolved decision question at a time with a recommended
answer, records each answer, and recomputes readiness.

Acceptance requires a final packet summarizing decision, rationale,
alternatives, consequences, evidence, scope, conflicts, and lifecycle effect.
The engineer must explicitly confirm that packet in the active session. The
workflow then invokes `adr accept`; it never emulates or bypasses that command.

An interrupted grill leaves a valid Proposed ADR with explicit Open Questions
and a resume command. A proposal ends as Accepted, Rejected, or explicitly
deferred with a reason and re-evaluation condition.

### Automation boundary

Hooks never start an interview or full readiness sweep. They may emit a short,
fail-open advisory with an exact grill command. CI performs deterministic diff
readiness, writes Step Summary and annotations, and requires no secret or model.
A suspected undocumented decision is advisory. CI blocks only when explicit,
inspectable evidence shows that the pull request implements a linked Proposed
ADR.

MCP exposes readiness only. It does not expose acceptance or another lifecycle
mutation.

### Compatibility and performance

The unspecified after-the-fact acceptance default changes from `auto` to
`assist`. An explicitly configured `auto` remains a supported opt-in and
existing configuration is not rewritten.

Existing ADR-010 hook and generator budgets remain unchanged. New warm p95
targets are 100 ms for a 50-record readiness core, 500 ms for single-record
CLI, 1 second for all-Proposed over 50 records, 250 ms for 500 changed paths
against 50 records, and no more than 100 ms MCP adapter overhead. The pull
request action has at most 5 seconds overhead excluding checkout and runtime
installation. Existing measured paths may not regress by more than 20 percent.

### Confirmation

Confirm this decision through Backlog epic 45's fifteen child tasks:

* strict lint and all four quality gates for this ADR;
* deterministic permutation and fixed-clock readiness tests;
* profile tests proving unresolved Open Questions block acceptance;
* CLI and MCP parity plus no-mutation tests;
* explicit-link positive and false-positive fixtures;
* resumable and source-fenced grill conversation fixtures;
* authoring, init, review, guardian, supersede, retire, hook, and CI scenarios;
* unchanged ADR-010 hook and client-generation budgets; and
* cross-platform, packaging, and three-client release certification.

## Consequences

### Positive

* Repository facts are reusable across every interaction and automation surface.
* Human intent remains explicit instead of being reconstructed as fact.
* Proposed ADRs become a visible decision work queue with terminal outcomes.
* CI can prevent shipped-but-unaccepted decisions without blocking speculative
  architecture findings.
* One canonical grill protocol reduces semantic drift across workflows and
  clients.

### Negative

* The feature adds a readiness engine, a CLI, an MCP surface, and another
  canonical client workflow. Shared modules, packaging inventories, and
  generation tests mitigate that maintenance cost.
* Interactive authoring takes longer than generating a complete-looking record.
  Adaptive depth and repository-grounded answers keep the interaction focused.
* The `auto` to `assist` default is a behavior change. Explicit legacy `auto`
  remains supported and the upgrade guide must call out the new default.
* Explicit-link CI is intentionally conservative and can miss undocumented
  decisions. Review advisories and guardian provide coverage without converting
  a heuristic into a merge gate.

## Pros and Cons of the Options

### Deterministic readiness plus human-gated grilling

* Good, because automation remains explainable and interaction remains human
  accountable.
* Good, because one readiness contract serves local tools, agents, and CI.
* Bad, because it requires disciplined boundaries and a larger test matrix.

### Independent interviews in every workflow

* Good, because each workflow could optimize its questions independently.
* Bad, because question semantics, acceptance behavior, and source fencing
  would drift across authoring, review, guardian, and clients.

### Confidence-based automatic acceptance

* Good, because shipped decisions could be documented with minimal interaction.
* Bad, because confidence cannot prove rationale, ownership, or acceptance of
  consequences and would weaken the existing human lifecycle.

### Keep current drafting and nudges

* Good, because no new surface or maintenance burden is introduced.
* Bad, because incomplete Proposed records and inferred rationale remain
  unresolved.

## Related Decisions

* ADR-001 keeps cost-bearing model behavior opt-in.
* ADR-004 defines fail-open context tiers and deterministic pre-commit
  enforcement.
* ADR-005 requires one semantic representation across ADR profiles.
* ADR-009 requires heuristic gates to produce actionable findings.
* ADR-010 requires one outcome contract and fixed budgets for the three native
  clients.

## References

* `docs/feature-adr-grilling/01-research.md`
* `docs/feature-adr-grilling/02-lifecycle-analysis.md`
* `docs/feature-adr-grilling/03-solution-design.md`
* `docs/feature-adr-grilling/04-implementation-plan.md`
* `docs/feature-adr-grilling/05-validation-plan.md`
* Backlog epic 45 and its architecture child task.
* `clients/workflows.json:1`, the canonical workflow source.
* `bin/adr-mcp:1`, the read-only MCP server entry point.
* <https://www.aihero.dev/grill-with-docs>
* <https://www.aihero.dev/skills-grilling>

## Open Questions

None.

## Enforcement

```json
{
  "forbid_pattern": [],
  "forbid_import": [],
  "require_pattern": [
    {
      "pattern": "\"grill\"",
      "path_glob": "clients/workflows.json",
      "message": "ADR Grilling must remain a canonical generated workflow (ADR-011)."
    },
    {
      "pattern": "adr_readiness",
      "path_glob": "bin/adr-mcp",
      "message": "MCP must expose deterministic readiness without lifecycle mutation (ADR-011)."
    }
  ],
  "llm_judge": false
}
```
