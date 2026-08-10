---
id: "ADR-038"
title: "Cost an unusable LLM verdict to that ADR alone, not the whole pass"
status: "Accepted"
date: "2026-08-10"
binding: false
gate: null
documents_shipped: false
verified_in:
  - "tests/test_adr_judge_llm.py"
supersedes: []
superseded_by: null
topics:
  - "llm judging"
  - "partial results"
  - "attestation"
aliases:
  - "partial LLM pass"
  - "per-ADR verdict granularity"
components:
  - "adr-judge"
symbols:
  - "run_llm_batch"
  - "degraded"
  - "evaluated"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-038 Cost an unusable LLM verdict to that ADR alone, not the whole pass

## Status

Accepted, 2026-08-10.

## Status History

```yaml
status_history:
  - date: 2026-08-10
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: Initial proposal
    changed_via: adr-kit
  - date: 2026-08-10
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Reviewed and accepted by the maintainer (TASK-170)
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

`run_llm_batch` judges one ADR per isolated model call. Until now a single
unusable call discarded the entire pass: it set `evaluated` back to `[]` and
returned `None`, so the run fell back to declarative-only.

Observed on 2026-08-09, immediately after TASK-169 gave a machine a working
judge backend for the first time:

```
[adr-judge] running LLM pass over 5 llm_judge ADR(s) with host (claude-code-cli): claude -p, one isolated call each...
[adr-judge] WARN: LLM pass DEGRADED to declarative-only: no usable verdict for ADR-030; whole LLM pass degraded to declarative-only
[adr-judge] OK - 0 violations, 0 advisory
```

Four ADRs were judged. One was not. All five verdicts were thrown away, and the
run printed `OK`.

The discard was deliberate, and its stated reason is in the docstring: "a
partially-evaluated pass reported as complete is precisely the failure mode this
hardening exists to remove." The premise is right and the remedy is wrong. The
danger is a partial pass reported *as complete*, and the attestation already
exists to prevent exactly that. Discarding true positives to avoid
misrepresenting them is paying with the answer to protect the label.

The same question was settled the other way one ADR earlier. ADR-037 gave the
guardian per-ADR verdicts so that an interrupted sweep keeps what it
established. A pre-commit pass is a shorter sweep with the same property.

## Decision Drivers

* A verdict that was genuinely established is evidence; discarding it makes the
  gate weaker than the model it runs on.
* The failure mode to prevent is *misreporting* completeness, not *having*
  partial results — and `attestation.degraded` already carries that distinction.
* The LLM half must never become hostage to whichever single call is most
  fragile; under a stable ordering that is the same ADR on every commit.
* ADR-001's floor: tooling drift must never block a legitimate commit. A
  violation the model actually found is not drift.
* ADR-037 already chose per-item granularity for the guardian on this argument.

## Considered Options

* Discard the whole pass on any unusable call (the behaviour until now).
* Keep every verdict that was established, record which ADRs got none, and mark
  the pass degraded.
* Retry the unusable call before deciding.

## Decision Outcome

Chosen option: **keep every established verdict and mark the pass degraded**,
because it preserves evidence without ever claiming the pass was complete.

`run_llm_batch` now returns the findings it established. `attestation.evaluated`
lists the ADRs that received a verdict, `attestation.degraded` is `true` whenever
any ADR did not, and `degraded_reason` names them along with how many of the
targets were still judged. `None` is returned only when no ADR received a verdict
at all, which keeps the existing caller contract for the unavailable-backend
path.

Retrying was rejected: `_run_llm_single` cannot distinguish a timeout from a
spawn failure or a non-zero exit — `bin/adr_llm.py` funnels all three to `None` —
so a retry policy would be uniform where the right policy is not, and it
multiplies the worst case again on the one path ADR-015 and ADR-033 are about.

### Confirmation

`tests/test_adr_judge_llm.py` asserts that a pass where one ADR yields no usable
verdict still reports the violations found for the others, that the attestation
is `degraded` with the unjudged id named, and that a pass where no ADR yields a
verdict still returns `None`.

## Decision Contract

### Must

* A verdict established for one ADR survives another ADR's unusable call.
* `degraded: true` means THIS PASS IS NOT COMPLETE. It no longer implies that
  nothing was judged: `evaluated` may be non-empty and the run may exit 1.
* `degraded_reason` names every ADR that received no verdict.

### Must Not

* Report a partial pass without setting `degraded`.
* Retry an unusable call inside the pass.

### Exceptions

* When no ADR receives a verdict, the pass returns `None` exactly as before, so
  callers keep one meaning for "the LLM pass produced nothing".

### Verification

* `tests/test_adr_judge_llm.py`

## Consequences

### Positive

* A commit that violates an Accepted ADR is now caught even when an unrelated
  ADR's call fails. Under the previous behaviour it was reported as `OK`.
* The attestation stops lying: `evaluated: []` no longer appears for a pass in
  which four ADRs were judged.
* A single fragile ADR can no longer disable the whole LLM half indefinitely.

### Negative

* A uniformly unresponsive CLI now costs N x `llm_timeout_seconds` instead of
  one, because the loop no longer stops at the first failure — on this
  repository 5 x 120 s. The short-circuit was bounding that by accident;
  `schemas/adr-kit-config.schema.json` already documents the worst case as
  "N x this value on a single commit", so this restores the documented bound
  rather than introducing a new cost. Mitigations: `judge.llm_timeout_seconds`,
  and `ADR_KIT_NO_LLM=1` for a single commit.
* A commit can now fail on a degraded pass, which previously could not happen.
  That is the point, but it is a behaviour change a user will notice.

## Pros and Cons of the Options

### Discard the whole pass

* Good, because a partial pass can never be mistaken for a complete one.
* Bad, because it achieves that by destroying true positives, including
  violations already established.
* Bad, because the attestation it writes (`evaluated: []`) is false about work
  that was done.

### Keep established verdicts, mark degraded

* Good, because evidence is preserved and completeness is still reported
  honestly.
* Good, because it matches ADR-037's resolution of the same question.
* Bad, because `degraded: true` now has two shapes for consumers to handle.

### Retry before deciding

* Good, because a transient failure would often succeed on a second call.
* Bad, because the backend contract cannot distinguish transient from permanent,
  so every failure would be retried.
* Bad, because it multiplies pre-commit latency on the path ADR-015 bounds.

## Open Questions

* None.

## Related Decisions

* ADR-037 — settled the same granularity question for the guardian.
* ADR-001 — the fail-open/fail-closed floor this decision operates within.
* ADR-015 — the latency budget the negative consequence is measured against.

## References

* backlog/tasks/task-170 - One-ADR-yields-no-usable-verdict-and-degrades-the-whole-LLM-pass.md
* `bin/adr-judge`, `run_llm_batch`
* `schemas/adr-kit-config.schema.json` — `judge.llm_timeout_seconds`
