---
id: "ADR-030"
title: "Recalibrate the Hook Latency Budgets to the Python Host That Actually Ships"
status: "Accepted"
date: "2026-08-05"
binding: true
gate: "adr-hook-python-budgets-v1"
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
topics:
  - "hooks"
  - "latency"
  - "performance budget"
  - "measurement"
aliases:
  - "hook budget recalibration"
  - "hook latency"
  - "python host budgets"
components:
  - "hooks/manifest.json"
  - "hook latency budgets"
  - "hook benchmark"
symbols:
  - "latency_budget_ms"
  - "hook_benchmark"
  - "measure"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-030 Recalibrate the Hook Latency Budgets to the Python Host That Actually Ships

## Status

Accepted, 2026-08-05.

## Status History

```yaml
status_history:
  - date: 2026-08-05
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: The declared budgets were calibrated for the native binary ADR-029 retired; seven of eight events cannot meet them on the Python path.
    changed_via: adr-kit
  - date: 2026-08-05
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: "Maintainer accepted: the budgets must describe the Python host that ships, not the binary ADR-029 retired."
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

`hooks/manifest.json` declares a p50, p95 and hard timeout for each of the eight
lifecycle events. Seven of the eight are unachievable, and have been since
ADR-029 retired the native hook binary.

Measured on Windows 11 / CPython 3.12.9, warm filesystem, 29 ADRs, 12 timed
samples per event after one warmup — the same method `hooks/hook_benchmark.py`
uses:

| event | measured p50 | declared p50 | declared hard | verdict |
|---|---|---|---|---|
| session-start | 262.9 ms | 50 | 500 | FAIL |
| user-prompt-submit | 275.4 ms | 75 | 500 | FAIL |
| pre-tool-use | 297.3 ms | 25 | 100 | FAIL |
| post-tool-use | 411.8 ms | 25 | 100 | FAIL |
| plan-exit | 454.3 ms | 25 | 100 | FAIL |
| pr-create | 283.9 ms | 400 | 5000 | pass |
| subagent-start | 370.1 ms | 30 | 250 | FAIL |
| pre-compact | 417.2 ms | 30 | 500 | FAIL |

The one event that passes is the one whose budget violates ADR-015's 2000 ms
ceiling, which is a separate decision (ADR-031). Every event that complies with
ADR-015 fails its own budget.

**The budgets were not arbitrary — they were exactly right for a host that no
longer runs.** Same machine, same payloads, native binary versus Python:

| event | native `adr-hook.exe` p50 | Python `adr-hook.py` p50 | ratio |
|---|---|---|---|
| PreToolUse | 20.2 ms | 273.6 ms | 13.5x |
| SessionStart | 24.6 ms | 269.6 ms | 11.0x |

20 ms sits comfortably inside the declared 25 ms p50 and 100 ms hard timeout.
ADR-029 retired that host: `run-hook.cmd` now runs it only under
`ADR_KIT_NATIVE_HOOK=1`, because measured against the Python oracle the binary
returned one of four governing ADRs before an edit. The budgets were left
describing a path that no longer ships.

Three of the events cannot be fixed by optimising the hook. `python -c pass`
measures **182.6 ms p50** on this machine; the process has not reached the first
line of `adr-hook.py` when the 100 ms hard timeout has already expired.

The visible cost is that `bin/adr-doctor` is permanently degraded.
`bin/adr_doctor_probes.py:325` reports healthy only when `all_targets_met`, and
that is false on every platform — including Windows, since the benchmark follows
the dispatcher and the dispatcher no longer prefers the binary. A health check
that is always red is a health check nobody reads, so the signal is gone exactly
when something real breaks.

## Decision Drivers

* A budget that no shipping configuration can meet is not a budget; it is a
  permanently failing assertion that trains people to ignore the report.
* The kit's own latency contract (ADR-015) is a *fixture* contract precisely so
  measurements survive slow runners — the numbers are supposed to describe
  reality, not intent.
* The interpreter floor is a hard physical bound on three of the events, and it
  is machine-dependent, so it must be recorded with its measurement rather than
  as a bare constant.
* Whatever is chosen must stay inside ADR-015's 2000 ms ceiling, which every
  recalibrated event comfortably does.

## Considered Options

* **Recalibrate the budgets to the Python host**, from measurement, with the
  evidence recorded next to the numbers.
* **Raise only the benchmark's subprocess kill timeout**, leaving the declared
  budgets untouched.
* **Reinstate the native binary** as the default host, which would make the
  existing budgets true again.

## Decision Outcome

Chosen option: **recalibrate the budgets to the Python host**, because it is the
only option under which the declared numbers describe the software that ships.

Each event's budget is derived from its measured p95 plus the 20 % CI variance
the corpus already declares, rounded up to a readable number, with the hard
timeout set above the interpreter floor plus the hook's own work. The
measurement, the machine, and the date are recorded as evidence in the fixture,
so the next person adjusting a number knows what it is made of.

The interpreter floor becomes a named constant carrying its measurement, because
it is a property of the machine and not of this kit — 124 ms was recorded on
2026-07-26 and this machine measures 182.6 ms.

Reinstating the binary was rejected on two grounds: it reverses ADR-029, whose
argument is that a second retrieval engine cannot be kept at parity, and the
binary demonstrably returned the wrong governing ADR when measured against the
Python oracle. Correct-but-slow beats fast-but-wrong for a governance hook.

Raising only the kill timeout was rejected because it removes the timeout
failures without touching the p50 and p95 targets, so `adr-doctor` stays
degraded — it hides the symptom and keeps the defect.

### Confirmation

`tests/test_hook_performance.py` asserts every declared budget against the
measured corpus, and `bin/adr-doctor --deep` reports `healthy` on a clean
checkout on every supported platform rather than permanently `degraded`.

## Decision Contract

### Must

* Every event in `hooks/manifest.json` must carry a `latency` block whose
  numbers were produced by measurement against the host that ships by default.
* The fixture must record the machine, the interpreter version and the date the
  measurement was taken, next to the numbers it produced.
* The measured interpreter start floor must be a named constant carrying the
  measurement that produced it.
* Every recalibrated budget must remain at or below ADR-015's 2000 ms ceiling.

### Must Not

* No budget may be set to a number that the default host cannot meet on a
  supported platform.
* No budget may be justified by the native binary's performance while
  `run-hook.cmd` runs that binary only under `ADR_KIT_NATIVE_HOOK=1`.

### Exceptions

* `pr-create` is out of scope here; its budget is settled by ADR-031.

### Verification

* `adr-hook-python-budgets-v1`

## Consequences

### Positive

* `bin/adr-doctor` reports a real signal again, so a genuine regression is
  visible instead of being lost in a permanent red.
* The numbers become falsifiable: a change that makes a hook slower now fails a
  gate instead of passing one that was already failing.
* The measurement is recorded, so the next adjustment starts from evidence.

### Negative

* The declared budgets get roughly an order of magnitude larger, which is a real
  loss of ambition and should be read as what it is: the price of retiring the
  compiled host. Mitigation is that the numbers are now true, and a true number
  can be improved against.
* The floor is machine-dependent, so a slower CI runner can still miss a target.
  The 20 % CI variance in the corpus exists for this and is applied to every
  recalibrated number.
* Re-measuring requires a quiet machine: the spread between an idle and a loaded
  run was 2.2x, so a certification pass cannot be improvised alongside other
  work.

## Pros and Cons of the Options

### Recalibrate to the Python host

* Good, because the declared numbers describe the software that actually runs.
* Good, because it restores `adr-doctor` as a usable signal.
* Bad, because the budgets get much larger, and a larger budget catches less.

### Raise only the kill timeout

* Good, because it is a one-line change with no contract implications.
* Bad, because the p50 and p95 targets still fail, so `adr-doctor` stays
  degraded and the health signal stays dead.
* Bad, because it leaves eight declared numbers describing a retired host.

### Reinstate the native binary

* Good, because the existing budgets become achievable again with no edit.
* Bad, because it reverses ADR-029 and reintroduces the second retrieval engine
  that ADR is about.
* Bad, because the binary returned one of four governing ADRs before an edit
  when measured against the Python oracle.

## Open Questions

* None.

## Related Decisions

* ADR-029 retired the native hook binary, which is what made these budgets
  false.
* ADR-015 sets the 2000 ms ceiling every recalibrated budget stays under.
* ADR-031 settles `pr-create`, the one event this ADR leaves alone.

## References

* `hooks/manifest.json` — the eight declared `latency` blocks.
* `hooks/hook_benchmark.py` — the measurement method.
* `bin/adr_doctor_probes.py:325` — where `all_targets_met` becomes the health
  verdict.
* `tests/fixtures/hooks/reference-corpus.json` — `python_floor_ms_p50: 124`,
  measured 2026-07-26.
* `docs/adr/ADR-029-retire-the-native-hook-binary-rather-than-maintain-a-second-retrieval-engine.md`

## Enforcement

```json
{
  "forbid_pattern": [],
  "forbid_import": [],
  "require_pattern": []
}
```
