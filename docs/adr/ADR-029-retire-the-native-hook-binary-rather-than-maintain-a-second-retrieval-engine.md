---
id: "ADR-029"
title: "Retire the Native Hook Binary Rather Than Maintain a Second Retrieval Engine"
status: "Accepted"
date: "2026-08-04"
binding: true
gate: "adr-single-retrieval-engine-v1"
documents_shipped: true
verified_in:
  - "tests/test_adr_hook_dispatch_matrix.py"
  - "tests/test_client_adapter_generation.py"
  - "tests/test_hook_performance.py"
supersedes: []
superseded_by: null
related:
  - "ADR-015"
topics:
  - "hooks"
  - "latency"
  - "distribution"
  - "maintenance surface"
aliases:
  - "native hook"
  - "adr-hook.exe"
  - "Rust host"
components:
  - "lifecycle hooks"
  - "adr-query"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-029 Retire the Native Hook Binary Rather Than Maintain a Second Retrieval Engine

## Status

Accepted, 2026-08-04.

## Status History

```yaml
status_history:
  - date: 2026-08-04
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: "parity is not a patch: the divergence is two implementations drifting, and closing it means porting the query engine"
    changed_via: adr-kit
  - date: 2026-08-04
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: ADR-029 must be measured against ADR-015's latency contract
    changed_via: adr-kit lifecycle
  - date: 2026-08-04
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Accepted by the maintainer in the spec gap-analysis review; the decision stands, its gate and binding flag follow when the implementation ships.
    changed_via: adr-kit lifecycle
  - date: 2026-08-24
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Implementation landed in TASK-187 - artefact, Rust source, dispatcher branch, benchmark branch and doctor requirement removed from all three trees. The gate and binding flag had been flipped by TASK-127 on 2026-08-05 while the implementation had NOT shipped, and its anchor asserted the opt-in state this ADR rejected; both are corrected here.
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

`hooks/bin/windows-x64/adr-hook.exe` is a dependency-free Rust reimplementation
of the hook hot path, built because Windows process creation is slow and the
edit-tier budget is 100 ms. It works: measured on this repository, `SessionStart`
costs **21 ms at the median** against Python's **235 ms**, an order of magnitude.

It also answers differently. Measured against the Python oracle after rebuilding
it from current source:

| event | native | Python |
|---|---|---|
| session-start | ADR-019 | ADR-019, byte-identical |
| user-prompt-submit | 4 records | 5 records |
| pre-tool-use / Write | **1 record** | **4 records** |
| post-tool-use / Write | 1 record | 4 records |
| plan-exit | nothing | full injection |

The first reading was that the binary was stale. It was — `hooks/bin/` was last
committed at v0.40.0 while the source moved on — but rebuilding it did **not**
close the gap, and that is the finding that matters.

The cause is structural. The Python edit tier stopped doing its own matching when
ADR-014 introduced the shared index-first engine: it now calls
`query_adr_context(..., paths=(relative,))`, which scores path at weight 1.0
alongside symbols, components, topics, aliases, title, decision contract and
summary, expands related decisions, and applies authority filtering. The Rust
host still implements the *earlier* design — glob match, else a token-overlap
rank with no path term at all, dropping every record that scores zero. On
`src/thing.py` that leaves one record standing where the engine finds four.

So the two implementations did not drift by neglect. They drifted because there
are two, and only one of them is the one every other caller uses.

Closing the gap is therefore not a patch. It is porting `bin/adr_query.py` — 764
lines of scoring, relationship expansion and authority rules — into Rust, and
then holding the port in step with every future change to it. `hooks/native/`
already tracks the Python core's constants by hand; this would extend that to
the retrieval engine itself.

Two decisions this project has already made describe what to do with a
maintenance surface of that shape. Spec R17 caps the client list at three and
calls a fourth "its own decision", because each surface adds contract
monitoring, tests, migration and release evidence that one maintainer carries.
Spec R18 accepts hand-maintaining what a library would absorb, and names the
cost rather than hiding it. A second retrieval engine is the same kind of cost,
taken on for latency rather than for a capability.

## Decision Drivers

* A hook that answers with a quarter of the governing decisions is wrong faster,
  not better.
* One retrieval engine, or every fix has to be made twice and verified twice.
* Windows is release-required in `clients/capabilities.json`, so its latency is a
  real constraint rather than a footnote.
* Whatever ships must be verifiable by running the artefact, not by reading its
  source.
* The 100 ms edit-tier budget is a contract (ADR-015, spec R21), so dropping to
  Python has to be shown against it rather than assumed.

## Considered Options

* **Retire the binary.** Remove it and the Rust source, and take the Python
  latency on every platform.
* **Port the query engine to Rust** and hold both implementations in step with a
  byte-for-byte artefact parity test.
* **Keep it opt-in indefinitely**, as it is since v0.44.1, and decide later.
* **Narrow its scope**: keep the binary only for the events where it is already
  byte-identical, and route the rest to Python.

## Decision Outcome

Chosen option: **retire the binary**, because the alternative is a permanent
second implementation of the one component every other caller shares, bought
with latency rather than with capability.

The Rust host and the committed artefact are removed, `run-hook.cmd` loses its
native branch, and the Python path is the only path on every platform.

**What that costs, measured rather than estimated.** `SessionStart` goes from
21 ms to 235 ms at the median on this machine. That is real, and it is the whole
argument for having built the binary. It sits inside the 500 ms budget the
manifest declares for that event and inside spec R21's 2 s ceiling, with room.
The edit tier is the tight one at 100 ms, and it is also the tier where the
binary was most wrong — one record of four — so the trade there is budget
pressure against three missing governing decisions.

**Why not narrow its scope.** Keeping the binary for the events where it already
matches sounds like the careful option and is the worst of the four: the
remaining divergence would be silent by construction, because the events that
match today are exactly the ones nobody would think to re-check. A partial
oracle is harder to reason about than none.

**Why not decide later.** Opt-in is where v0.44.1 left it, and it is a stable
resting place — nothing is broken. But an artefact that ships, cannot be trusted
and is nobody's job decays into precisely the state this ADR is written about:
last rebuilt two releases ago, diverging in ways only a comparison run reveals.

### If the latency proves unacceptable

This decision is reversible, and the reversal has a name. Restoring a native path
means porting `bin/adr_query.py`, not patching `adr-hook.rs`, and it needs the
artefact-level parity test this ADR requires — one that runs the binary and
compares its output to the Python path over the full manifest payload set. A
test that reads the Rust source cannot see a divergent build, which is exactly
how this went unnoticed: `tests/test_adr_hook_result_limit.py` asserted parity by
reading `adr-hook.rs` for a constant, and passed over a two-release-old binary.

### Confirmation

Every manifest event, on every client, returns the same records it returns today
through the Python path, on Windows as well as POSIX. The edit-tier events are
measured against their 100 ms budget through the fixture contract of ADR-015,
and the measurement is committed alongside the budget.

## Decision Contract

### Must

* Keep exactly one retrieval implementation, shared by every caller.
* Remove the native host, its committed artefact, and the dispatcher branch that
  prefers it.
* Measure the Python edit-tier path against its declared budget and commit the
  measurement.
* Verify any future native path by running the artefact, never by reading its
  source.

### Must Not

* Ship a second implementation of retrieval, ranking or authority.
* Prefer an artefact whose output has not been compared with the Python path.
* Assert parity from a source constant.
* Reintroduce a native path for a subset of events, which makes divergence
  silent exactly where nobody is looking.

### Exceptions

* A future native path is permitted when it delegates to the shared engine
  rather than reimplementing it, and carries the artefact parity test.

### Verification

* `adr-single-retrieval-engine-v1`: the gate that anchors this decision. It
  ships in `tests/test_adr_hook_dispatch_matrix.py`, so `gate` carries the name
  and `binding` is true. It asserts that no second ranking implementation
  ships: both halves of the polyglot dispatcher, on every generated tree, must
  carry no native branch, no artefact to prefer and no environment variable to
  re-enable one, while still dispatching the Python host.

  Corrected on 2026-08-24. Between 2026-08-05 and that date this section
  claimed the gate also asserted "that the edit-tier path meets its declared
  budget", and the anchor it named asserted something weaker still — that the
  native host ran only under `ADR_KIT_NATIVE_HOOK=1`, which is the opt-in state
  the Decision Outcome above explicitly rejects. A gate certifying the rejected
  option is worse than no gate, because `adr-lint` reported compliance for a
  decision that had not been carried out. The budget half is verified where it
  is actually measured, `tests/test_hook_performance.py`, together with the
  assertion that Python is the only host the benchmark can report;
  `tests/test_client_adapter_generation.py` asserts that no hook tree carries a
  compiled or Rust host at all.

## Consequences

### Positive

* One engine to fix and one engine to test, so every retrieval improvement
  reaches every platform at once.
* The class of defect this ADR is written about — an artefact diverging silently
  from the oracle — cannot recur, because there is no second artefact.
* Roughly 630 lines of Rust and 1 committed binary leave the release surface.

### Negative

* **Windows sessions get slower: 21 ms to 235 ms at the median on
  `SessionStart`, an order of magnitude.** That is the price and it is not
  mitigated away. It stays inside the 500 ms event budget and inside R21's 2 s
  ceiling.
* The 100 ms edit-tier budget becomes the binding constraint on Windows, where
  process creation alone measured 18 ms at the median. If it proves unmeetable,
  the budget is the thing to revisit, and revisiting it means superseding
  ADR-015 rather than quietly relaxing a number.
* A user who set `ADR_KIT_NATIVE_HOOK=1` after v0.44.1 loses that option.

## Pros and Cons of the Options

### Retire the binary

* Good, because one engine cannot diverge from itself.
* Good, because it removes an artefact nobody owns.
* Bad, because Windows loses an order of magnitude of hook latency.

### Port the query engine to Rust

* Good, because it keeps the latency and closes the gap.
* Bad, because retrieval then exists twice, permanently, in two languages,
  maintained by one person.

### Keep it opt-in indefinitely

* Good, because nothing breaks today.
* Bad, because a shipped artefact nobody trusts and nobody owns decays, which is
  the state that produced this ADR.

### Narrow its scope to the matching events

* Good, because it preserves latency where it is provably correct.
* Bad, because the remaining divergence is silent by construction: the events
  that match are the ones nobody re-checks.

## Open Questions

* None.

## Related Decisions

* Bounded by ADR-015's latency contract, which the Python path must be measured
  against rather than assumed to meet.
* Applies the reasoning of ADR-014, whose shared index-first engine is the single
  implementation this decision protects.
* Shares its maintenance-ceiling argument with spec R17 and R18, where the same
  trade — capability against what one maintainer can carry — is made explicitly.

## References

* `hooks/native/adr-hook.rs` — 633 lines; `rank()` has no path term and filters
  on `score > 0`.
* `bin/adr_query.py` — 764 lines, the engine a port would have to reproduce.
* `hooks/adr_hook_core.py`, the edit-tier branch calling
  `query_adr_context(..., paths=(relative,))`.
* `tests/test_adr_hook_result_limit.py` — the source-reading parity assertion
  that passed over a two-release-old binary.
* Measured 2026-08-04 on the Windows certification machine: native
  `SessionStart` p50 21 ms, p95 31 ms; Python p50 235 ms, p95 268 ms.
