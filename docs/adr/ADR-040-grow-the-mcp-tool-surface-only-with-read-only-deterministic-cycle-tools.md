---
id: "ADR-040"
title: "Grow the MCP Tool Surface Only With Read-Only Deterministic Cycle Tools"
status: "Accepted"
date: "2026-08-19"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
related:
  - "ADR-011"
  - "ADR-014"
  - "ADR-016"
topics:
  - "model context protocol"
  - "tool surface"
  - "agent workflow"
  - "read-only tooling"
aliases:
  - "MCP expansion criterion"
  - "adr_lint MCP tool"
  - "adr_related MCP tool"
components:
  - "bin/adr-mcp"
symbols:
  - "TOOL_DEFINITIONS"
  - "TOOL_HANDLERS"
  - "tool_adr_lint"
  - "tool_adr_related"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-040 Grow the MCP Tool Surface Only With Read-Only Deterministic Cycle Tools

## Status

Accepted, 2026-08-19.

## Status History

```yaml
status_history:
  - date: 2026-08-19
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Initial proposal
    changed_via: adr-kit
  - date: 2026-08-19
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-011
    changed_via: adr-kit lifecycle
  - date: 2026-08-19
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-014
    changed_via: adr-kit lifecycle
  - date: 2026-08-19
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-016
    changed_via: adr-kit lifecycle
  - date: 2026-08-19
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Accepted by explicit user decision after readiness check (ready-for-confirmation, quality 0.88).
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

The MCP server `bin/adr-mcp` exposes five tools: `adr_context`, `adr_judge`,
`adr_status`, `adr_quality`, and `adr_readiness`. ADR-016 keeps the server
deliberately tiny ("thin beats feature count"), ADR-011 forbids lifecycle
mutation over MCP, and ADR-004 requires the task tier to stay key-free.

The generated agent guide (`.adr-kit/ADR-guide.md`) prescribes a development
cycle: query context before implementation, judge the staged diff and run
strict ADR lint before completion, and read the returned ADRs including their
graph links. Mapping that cycle onto the current tool surface shows two
mandatory steps a shell-less MCP client cannot perform:

* "Run strict ADR lint" has no MCP equivalent; `bin/adr-lint` is CLI-only.
* Following graph links after `adr_context` returns an ADR id has no MCP
  equivalent; `bin/adr-related` is CLI-only.

adr-kit ships roughly 25 CLIs. Without a recorded criterion, every future
"should X be an MCP tool?" discussion restarts from zero, and the surface
either stagnates (agents fall back to raw file reads, bypassing the shared
retrieval path of ADR-014) or creeps (composite and LLM-backed tools erode
the key-free guarantee of ADR-016).

## Decision Drivers

* A shell-less agent must be able to complete every step of the prescribed
  ADR development cycle through MCP alone.
* The server must stay key-free, read-only, and thin (ADR-004, ADR-011,
  ADR-016); tool names and schemas are certification surface (ADR-010,
  ADR-012, ADR-039), so additions must be deliberate and rare.
* Future additions need a recorded, checkable criterion instead of
  case-by-case debate.

## Considered Options

* Record an expansion criterion and admit exactly the two cycle tools it
  selects today (`adr_lint`, `adr_related`).
* Expose every read-only CLI (`adr-lint`, `adr-related`, `adr-retire`,
  `adr-audit`, `adr-grill-signal`, doctor's read path) as MCP tools.
* Do nothing: keep the five tools and let shell-less agents read ADR files
  directly.

## Decision Outcome

Chosen option: **record an expansion criterion and admit exactly the two
cycle tools it selects today**, because it completes the prescribed agent
cycle over MCP while keeping the surface thin and giving every future
proposal a recorded test instead of a fresh debate.

A CLI is admitted to the MCP tool surface only when all of the following
hold:

1. **Read-only**: it never mutates repository, lifecycle, or index state.
2. **Deterministic and key-free**: no LLM call, no API key, no network.
3. **Agent-query-shaped**: a single request/response with JSON output, not a
   hook advisory, watcher, or interactive flow.
4. **Cycle-covering**: it covers a step of the generated agent guide's
   development cycle that no exposed tool already covers.

Applied today: `bin/adr-lint` (guide step "run strict ADR lint") and
`bin/adr-related` (guide step "read the returned ADRs", which includes their
graph links) are admitted as `adr_lint` and `adr_related`. The criterion
excludes `adr-retire` (no cycle step), `adr-audit` (composite of already
exposed judge plus newly exposed lint), `adr-suggest` and `adr-judge --llm`
(LLM-backed), `adr-grill-signal` and `adr-watch` (hook-shaped), and every
lifecycle or index mutation (ADR-011).

### Confirmation

`tests/test_adr_mcp.py` verifies that `tools/list` returns exactly the seven
tools in fixed order and that `adr_lint` and `adr_related` delegate to their
CLIs read-only. `python scripts/build-client-adapters.py --check` confirms
the three shipped copies stay byte-identical.

## Decision Contract

### Must

* Every MCP tool delegates to a sister CLI via subprocess and accepts the
  optional `project_root` / `adr_dir` workspace arguments.
* Every addition to `TOOL_DEFINITIONS` satisfies all four admission tests of
  this decision, and the ADR recording that addition names the guide step it
  covers.
* `adr_lint` runs `bin/adr-lint` with JSON output; `adr_related` runs
  `bin/adr-related` with JSON output.

### Must Not

* No MCP tool may mutate repository, lifecycle, or index state (ADR-011).
* No MCP tool may require an API key or invoke an LLM (ADR-004, ADR-016).
* No composite tool may be added when agents can compose the result from
  exposed tools.

### Exceptions

* None.

### Verification

* `tests/test_adr_mcp.py` (tool list, delegation, read-only behaviour).
* `python scripts/build-client-adapters.py --check` (triplicate identity).

## Consequences

### Positive

* A shell-less MCP client can complete the full prescribed development
  cycle: context, judge, lint, readiness, quality, graph links.
* Future surface discussions reduce to four recorded admission tests.
* All retrieval keeps flowing through the shared deterministic path
  (ADR-014) instead of ad-hoc file reads.

### Negative

* Two more tool schemas become certification surface across three clients;
  renames are now breaking changes. Mitigated by choosing names consistent
  with the existing `adr_*` convention.
* `adr-lint` is the heaviest delegate so far; a large ADR set may approach
  the 60-second subprocess timeout. Mitigated by the existing per-call
  timeout handling, which reports a tool error without killing the server.

## Pros and Cons of the Options

### Record a criterion and admit the two cycle tools

* Good, because the agent cycle becomes fully MCP-servable while the surface
  grows by the minimum.
* Good, because the admission tests make future decisions checkable.
* Bad, because seven tools are more certification surface than five.

### Expose every read-only CLI

* Good, because no future discussion is ever needed.
* Bad, because it roughly doubles the certification surface and contradicts
  ADR-016's "thin beats feature count" without serving any cycle step.

### Do nothing

* Good, because zero new surface.
* Bad, because shell-less agents cannot run the mandatory lint step and
  bypass the shared retrieval path with raw file reads, exactly what ADR-014
  centralised retrieval to prevent.

## Open Questions

List unresolved human decisions as unchecked tasks. Accepted ADRs must have no
unresolved items.

Answer them with `bin/adr answer`, which rewrites an item as
`- [x] <question> — **Answered <date> by <signer>:** <answer>`. A checked item
is resolved, so it no longer blocks acceptance and stays in the record. Do not
delete an answered question: the reasoning is what a future reader needs in
order to re-evaluate the decision.

## Related Decisions

* None.

## References

* `bin/adr-mcp` — module docstring records the deliberate `adr-suggest`
  omission and the thin-surface intent.
* `.adr-kit/ADR-guide.md` — the generated agent development cycle this
  decision completes.
* `docs/adr/ADR-016-serve-both-mcp-protocol-eras-from-one-hand-rolled-stdio-server.md`
