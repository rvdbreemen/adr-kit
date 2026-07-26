---
id: "ADR-015"
title: "Enforce a Two-Second Deterministic Latency Budget as a Test Fixture Contract"
status: "Accepted"
date: "2026-07-26"
binding: true
gate: "adr-kit-cli-latency-v1"
documents_shipped: false
verified_in:
  - "tests/test_cli_performance.py"
  - "tests/test_hook_performance.py"
supersedes: []
superseded_by: null
topics:
  - "performance"
  - "latency budget"
  - "non-functional requirement"
  - "regression guard"
aliases:
  - "2s budget"
  - "latency corpus"
  - "user-wait ceiling"
components:
  - "adr-lint"
  - "adr-retire"
  - "hooks"
  - "tests"
symbols:
  - "latency-corpus.json"
  - "reference-corpus.json"
  - "_resolve_gates_locally"
  - "resolve_present_terms"
  - "_WALK_CACHE"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-015 Enforce a Two-Second Deterministic Latency Budget as a Test Fixture Contract

## Status

Accepted, 2026-07-26.

**Decision Maker:** User: Robert van den Breemen (chose to record the NFR as an
enforced contract after the TASK-55 measurement pass).

## Status History

```yaml
status_history:
  - date: 2026-07-26
    status: Proposed
    changed_by: adr-kit
    reason: Initial proposal
    changed_via: adr-kit
  - date: 2026-07-26
    status: Accepted
    changed_by: Robert van den Breemen
    reason: Accepted after TASK-55 evidence review; explicit yes in session
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

adr-kit's deterministic surface (hooks, CLIs, generated-index queries) runs
inside interactive agent sessions and pre-commit paths where a human is
waiting. A latency regression there is invisible to functional tests and only
surfaces as user pain at scale.

The TASK-55 measurement pass (2026-07-26, Windows, Python 3.12.9) proved this
is not hypothetical: `adr-lint` reached p95 2032 ms and `adr-retire` p95
2607 ms on this repository, and `adr-retire` scaled linearly with ADR count
(p50 5229 ms at 100 ADRs on a clean tree) because of a repeated full-repo walk
per scored item. The target audience is teams with growing ADR sets, so the
degradation lands exactly where adoption should grow. The fixes shipped in
v0.42.0 (single-pass scans, walk memoization, nested-checkout pruning; commit
`d2d0ccc`), but nothing yet prevented the same bug class from returning
silently.

Hook latency already had an enforced budget contract:
`tests/fixtures/hooks/reference-corpus.json` consumed by
`tests/test_hook_performance.py`. CLI latency had no equivalent, which is why
the regression could exist unnoticed.

## Decision Drivers

* A user-facing wait above ~2 seconds breaks the flow of an interactive agent
  session and a pre-commit hook path.
* Performance fixes without committed budgets regress silently; functional
  tests stay green while latency decays.
* Wall-clock assertions alone are machine-dependent and flaky on slow CI
  runners; structural guarantees are not.
* The hooks side already proved the fixture-plus-tests pattern works
  (`reference-corpus.json`, budgets held since v0.35).

## Considered Options

* Fixture contract: budgets plus measured evidence committed as a versioned
  fixture, enforced by structural guards plus a live smoke test.
* CI-only timing assertions without a committed fixture.
* Per-tool ad-hoc budgets in each test file.
* Do nothing: keep the v0.42.0 fixes but treat the 2 s goal as documentation.

## Decision Outcome

Chosen option: **the fixture contract**, because it is the only option that
survives both slow CI runners and future tool additions: every deterministic
user-facing CLI path must stay under a 2000 ms wall-clock ceiling, recorded
with its measured evidence in `tests/fixtures/cli/latency-corpus.json`
(method `adr-kit-cli-latency-v1`, mirroring
`tests/fixtures/hooks/reference-corpus.json`), and enforced by
`tests/test_cli_performance.py` in two layers:

1. **Machine-independent structural guards** that pin the mechanisms behind
   the budget: repo walks are memoized per root, multi-needle scans resolve in
   one pass with early exit, and directories containing a `.git` entry are
   never scanned. These fail on any runner regardless of speed.
2. **A live smoke test** asserting the measured median stays under the hard
   2000 ms ceiling on the repository itself, with the measured p50 kept a
   factor 2 or more below the ceiling to absorb CI variance.

New deterministic user-facing tools must be added to the corpus and test when
they ship.

### Confirmation

`python -m pytest tests/test_cli_performance.py tests/test_hook_performance.py`
passes; `tests/fixtures/cli/latency-corpus.json` carries the budgets and the
before/after evidence for the v0.42.0 baseline.

## Decision Contract

### Must

* Every deterministic user-facing CLI or hook path keeps a p50/p95/hard-budget
  entry in a committed latency fixture with measured evidence.
* Latency-critical scan mechanisms are guarded by machine-independent
  structural tests, not only by wall-clock assertions.
* Repo scanners prune any directory containing a `.git` entry (nested
  checkouts are not project source).

### Must Not

* No deterministic user-facing path may carry a hard budget above 2000 ms.
* Repo scanners must not re-walk or re-read the tree once per scored item
  (per ADR, per gate, per term); needle resolution is single-pass.
* Budgets must not be relaxed to make a failing test pass; a budget change
  requires superseding or amending this ADR.

### Exceptions

* Opt-in LLM passes (`adr-judge --llm`, guardian LLM tier) are excluded: their
  latency is network- and model-bound and covered by ADR-001's opt-in gate.
* The ~124 ms Python interpreter spawn floor per CLI invocation is accepted as
  irreducible for the subprocess-per-call design on Windows.

### Verification

* `tests/test_cli_performance.py` (structural guards + 2 s ceiling smoke,
  method `adr-kit-cli-latency-v1`).
* `tests/test_hook_performance.py` (hook budgets, method
  `adr-kit-hook-latency-v1`).
* Evidence: `tests/fixtures/cli/latency-corpus.json`,
  `tests/fixtures/hooks/reference-corpus.json`.

## Consequences

### Positive

* The repeated-walk bug class cannot return silently: structural guards fail
  deterministically on any runner the moment memoization, single-pass
  resolution, or nested-checkout pruning is removed.
* The budget is an inspectable artifact with audit history (before/after
  numbers per scenario), not tribal knowledge.
* New tools inherit a clear, quantified performance bar instead of an implied
  one.

### Negative

* The live smoke test measures real wall-clock and can flake on a severely
  overloaded runner; mitigated by asserting only against the hard ceiling with
  a measured factor 2-4 margin, and by keeping the structural guards
  machine-independent.
* The fixture's evidence section goes stale as the codebase grows; mitigated
  by re-measuring whenever a budget entry changes (which this ADR requires to
  go through supersession or amendment anyway).
* A genuine future need for a >2 s deterministic path (for example a
  whole-repo migration command) requires an amending ADR; that friction is
  intentional.

## Pros and Cons of the Options

### Fixture contract (chosen)

* Good, because budgets, method, and evidence live in version control next to
  the tests that enforce them, mirroring the proven hooks pattern.
* Good, because the structural/wall-clock split keeps CI reliable while still
  guarding the mechanism.
* Bad, because it adds a fixture to maintain when tools are added or renamed.

### CI-only timing assertions

* Good, because minimal footprint.
* Bad, because thresholds hidden in CI config are invisible in review, carry
  no evidence, and flake on shared runners with no structural fallback.

### Per-tool ad-hoc budgets

* Good, because each tool can tune its own numbers.
* Bad, because budgets drift apart, there is no single user-wait ceiling, and
  the next tool ships without one (exactly how `adr-lint`/`adr-retire` escaped
  the hooks-side discipline).

### Do nothing

* Good, because zero effort after the v0.42.0 fixes.
* Bad, because the measurement pass proved the bug class ships and scales;
  without enforcement the 2 s goal decays into a wish.

## Open Questions

None.

## Related Decisions

* **ADR-001 (Make Per-Commit LLM Gates Opt-In)**: complements; LLM passes are
  the explicit exception to this budget.
* **ADR-009 (Bound Heuristic Gates to Findings an Author Can Act On)**:
  complements; both bound a quality mechanism to stay usable in the hot path.
* **ADR-010 (Certify Three Native CLI Clients Through One Outcome Contract)**:
  depends on; the hook latency budgets this ADR generalizes were introduced by
  the client certification contract.

## References

* TASK-55 (measurement, fixes, evidence) and TASK-56 (v0.42.0 release) in
  `backlog/tasks/`.
* Fix commit `d2d0ccc` (perf(cli): make repo scans single-pass in adr-lint and
  adr-retire), released in v0.42.0.
* `tests/fixtures/cli/latency-corpus.json` — budgets plus measured
  before/after evidence (clean tree, contaminated tree, 16/50/100 ADR
  scaling).
* `bin/adr-retire` `_walk_repo_files`/`resolve_present_terms` and
  `bin/adr-lint` `_resolve_gates_locally` — the guarded mechanisms.
* `hooks/manifest.json` — per-event hook latency budgets (p50/p95/hard).

## Enforcement

```json
{
  "forbid_pattern": [],
  "forbid_import": [],
  "require_pattern": [
    {
      "pattern": "\"hard_timeout_ms\": 2000",
      "path_glob": "tests/fixtures/cli/latency-corpus.json",
      "message": "The 2000 ms hard ceiling is the ADR-015 contract; changing it requires superseding or amending ADR-015."
    }
  ],
  "llm_judge": false
}
```
