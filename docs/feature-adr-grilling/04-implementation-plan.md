# ADR Grilling implementation plan

## Epic

**Title:** EPIC: Grilling for ADRs across the complete ADR lifecycle

The epic delivers interactive decision support without weakening deterministic
governance. It is complete when all fifteen child tasks are Done and the
end-to-end, cross-client, packaging, lifecycle, hook, and performance evidence
has been recorded.

## Delivery waves

| Wave | Tasks | Purpose |
|---|---|---|
| 1 | ST-01 | Approve architecture and contracts. |
| 2 | ST-02, ST-03 | Build the readiness model and Open Questions semantics. |
| 3 | ST-04, ST-05 | Expose readiness and determine explicit implementation links. |
| 4 | ST-06, ST-07 | Add MCP access and the canonical grill workflow. |
| 5 | ST-08 | Integrate authoring and acceptance. |
| 6 | ST-09, ST-10, ST-11, ST-12 | Integrate lifecycle entry points in parallel. |
| 7 | ST-13, ST-14 | Add bounded hooks and deterministic CI. |
| 8 | ST-15 | Certify and release the complete feature. |

## Child tasks

### ST-01 — Record the ADR Grilling architecture and public contracts

Create and human-accept an ADR defining evidence classes, readiness,
interaction, lifecycle authority, CI behavior, public commands, failure modes,
and performance limits. Validate strict lint, quality, relationships, and the
ADR index.

### ST-02 — Build the deterministic ADR readiness domain model

Implement a stdlib-only, read-only, versioned readiness report with an injected
clock, stable ordering, normalized paths, public finding codes, and all agreed
classifications. Certify a 50-ADR warm p95 of at most 100 ms.

Depends on ST-01.

### ST-03 — Add semantic Open Questions support to ADR profiles

Add the optional semantic role to MADR, Nygard, and legacy profiles. Keep
existing ADRs compatible, make unresolved Proposed questions advisory, and
prevent acceptance while questions remain unresolved.

Depends on ST-01.

### ST-04 — Add the read-only adr-readiness CLI

Support one ADR, all Proposed ADRs, and diff ranges with human, JSON, and GitHub
renderers. Analysis success uses exit code 0; invalid input or runtime failure
uses exit code 2. Certify the single-ADR and 50-ADR budgets.

Depends on ST-02 and ST-03.

### ST-05 — Detect deterministic implementation links to Proposed ADRs

Implement explicit, inspectable linkage evidence and keep likely missing ADRs
advisory. Cover renames, deletes, monorepos, multiple ADRs, ordering, injection,
and false-positive fixtures.

Depends on ST-02.

### ST-06 — Expose readiness through the key-free MCP server

Add the fifth read-only MCP tool `adr_readiness`, retain the existing four tool
contracts, and certify CLI/MCP parity, workspace isolation, structured errors,
and bounded adapter overhead.

Depends on ST-04 and ST-05.

### ST-07 — Implement the canonical adr-kit grilling workflow

Add `/adr-kit:grill` for an ADR, PR, range, source file, revalidation, or all
Proposed ADRs. Implement repository grounding, one-question interaction,
recommended answers, inline updates, resumability, source fencing, and explicit
human confirmation across all clients.

Depends on ST-03 and ST-04.

### ST-08 — Integrate grilling into ADR authoring and acceptance

Make `/adr-kit:adr <subject>` qualify the decision, create a Proposed ADR, and
grill it. Add the acceptance packet and same-session confirmation, retain
`adr accept` as authority, and change the unspecified after-the-fact default
from `auto` to `assist` while preserving explicit `auto`.

Depends on ST-07.

### ST-09 — Add adaptive reconstruction grilling to adr-kit init

Make init candidates Proposed first. Use compact confirmation only when chosen
decision, rationale, alternatives, and consequences are directly evidenced;
otherwise use a deep grill. Keep mixed batches resumable and prevent duplicate
or conflicting candidates.

Depends on ST-08.

### ST-10 — Integrate grilling into review and judge workflows

Separate ordinary code findings, Accepted ADR conflicts, suspected undocumented
decisions, and linked Proposed ADRs. Route the latter two to a grill without
weakening judge enforcement or trusting PR instructions.

Depends on ST-05 and ST-08.

### ST-11 — Manage Proposed ADRs as an active guardian work queue

Add stable priority ranking, an atomic derived cache, and at most three
SessionStart actions. Keep heavy analysis outside the hook and retain its
existing p50, p95, and hard limits.

Depends on ST-04 and ST-08.

### ST-12 — Add grilling to supersede, retire and revalidation flows

Grill changed forces, migration, and consequences; accept a successor before
transactionally changing the previous ADR; preserve reciprocal links; and
support unchanged, successor, reject, and defer outcomes.

Depends on ST-08.

### ST-13 — Add advisory grilling signals to hooks and pre-commit

Add short, shell-safe commands for suspected decisions and linked Proposed ADRs.
Do not start an interview, model call, or full readiness scan. Preserve all hook
budgets and the pre-commit five-second warning threshold.

Depends on ST-05 and ST-07.

### ST-14 — Add deterministic PR readiness reporting and merge gate

Publish Step Summary, annotations, and outputs without a PR comment or secret.
Keep missing ADRs advisory and fail only for an explicitly linked, implemented
Proposed ADR. Cover forks, shallow clones, refs, escaping, and action latency.

Depends on ST-04, ST-05, and ST-08.

### ST-15 — Certify, document and release ADR Grilling end to end

Run end-to-end lifecycle scenarios, all supported platforms and clients,
packaging checks, generated-artifact drift checks, hook and command benchmarks,
and upgrade validation. Publish the final usage, migration, and release
documentation only after all upstream tasks pass.

Depends on ST-06, ST-09, ST-10, ST-11, ST-12, ST-13, and ST-14.

## Shared completion requirements

Every child task:

- includes its own tests and relevant documentation;
- records exact validation commands and results in Backlog notes;
- uses deterministic fixtures and a fixed clock where time affects output;
- records performance evidence when it touches a measured path;
- keeps runtime dependencies unchanged unless a separately accepted ADR permits
  a change;
- updates modified files and final summary before completion.
