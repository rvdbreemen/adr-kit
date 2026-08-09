---
id: "ADR-037"
title: "Keep per-ADR judge verdicts in the advisory per-machine guardian state"
status: "Accepted"
date: "2026-08-09"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
topics:
  - "guardian"
  - "judge"
  - "state"
  - "cadence"
aliases:
  - "per-ADR judged state"
  - "llm_tier.adrs"
  - "interrupted sweep keeps verdicts"
components:
  - "bin/adr-guardian"
  - "skills/guardian/SKILL.md"
symbols:
  - "llm_tier.adrs"
  - "stamp llm --adr"
  - "_compute_due_tiers"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-037 Keep per-ADR judge verdicts in the advisory per-machine guardian state

## Status

Accepted, 2026-08-09.

## Status History

```yaml
status_history:
  - date: 2026-08-09
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: "TASK-154: design decision on where per-ADR judged-state lives"
    changed_via: adr-kit
  - date: 2026-08-09
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Accepted by the maintainer in-session; TASK-154 implementation verified by 45 guardian tests and an end-to-end bench cycle (violation holds tier due, re-judge clears)
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

The guardian's llm tier records one `last_run` for the whole tier. The tier's
sweep makes one isolated model call per judged ADR (ADR-036), at a measured 20
to 28 seconds per call; a downstream repository with 68 judged ADRs runs the
sweep for roughly 25 minutes.

One timestamp cannot describe a 25-minute, 68-step process that can stop in the
middle. When a sweep is interrupted or one ADR times out, the tier either stays
due — every verdict already reached is forgotten and the next sweep pays for all
of them again — or it is stamped complete, and the ADRs that never reached a
verdict inherit a freshness they did not earn. A violation found mid-sweep has
no durable place to live either: once the tier is stamped, nothing keeps the
outcome non-clean until a re-judge clears it.

The design tension named in TASK-154: `.adr-kit-state.json` is per-machine
advisory data by contract (spec task-9: concurrent sessions may stamp, a lock
serialises transactions, the file is not a ledger), while sharing cadence across
checkouts — the CI use-case — wants a tracked file. A working prototype of the
tracked variant exists downstream (OTGW-firmware `scripts/adr-judge-weekly.py`:
tracked per-ADR stamps, verdict memory, per-ADR progress, empirical 180 s
timeout at 6.5× the measured maximum).

## Decision Drivers

* The guardian's contract is advisory: `check` always exits 0, never blocks,
  never spawns. Whatever state it keeps must not quietly become a ledger.
* ADR-025 separates what tracked configuration may select from what only a
  machine may introduce. A verdict produced by one machine's model call at one
  moment is a machine fact.
* ADR-011 splits a deterministic engine from a human-gated conversation; the
  sweep loop is skill territory, the state is engine territory.
* The repository has just removed sixteen thousand lines (ADR-036); the smallest
  mechanism that meets the need wins.

## Considered Options

* Option A: per-ADR verdicts inside the existing advisory per-machine state
  (`llm_tier.adrs`), with the tracked variant left to downstream repositories.
* Option B: a tracked per-ADR state file committed to the repository, as in the
  downstream prototype.
* Option C: both — advisory state for the guardian plus an optional tracked
  export for CI.
* Option D: do nothing; keep the single tier timestamp.

## Decision Outcome

Chosen option: **Option A**, because every property the acceptance criteria ask
for is a property of state granularity, not of state location — and location is
where the guardian's contract draws its line.

`llm_tier` gains an `adrs` map: `{"ADR-NNN": {"last_run": <iso>, "verdict":
"ok" | "violation"}}`, living in `.adr-kit-state.json` exactly as advisory and
as per-machine as the rest of that file. Three behaviours follow:

1. **Incremental stamping.** `adr-guardian stamp llm --adr ADR-NNN --verdict
   ok|violation` records one verdict the moment it exists, under the same
   cross-process lock as every other stamp. An interrupted sweep keeps
   everything it established; the skill's next sweep reads the map and re-judges
   only ADRs without a fresh `ok`. Entries for ADR files that no longer exist
   are pruned on stamp. The tier-level `stamp llm` (no `--adr`) keeps its
   meaning: a completed sweep.
2. **Violations hold the tier open.** `_compute_due_tiers` reports the llm tier
   due whenever any recorded verdict is `violation`, regardless of freshness,
   and the nudge names the count. The tier goes quiet only when a re-judge
   overwrites the entry with `ok`.
3. **Progress is the skill's job.** The guardian sweep skill judges one ADR at a
   time (`adr-judge --llm --dry-run-enforcement ADR-NNN`), prints each verdict
   with its elapsed time as it lands, and stamps it before moving on. The
   deterministic engine holds state; the conversation shows progress (ADR-011).

The tracked variant is deliberately left downstream. A repository that wants a
committed, checkout-travelling judge record — the CI gate — is making a project
decision about its own history, and the downstream prototype shows it needs no
support from this kit beyond what `--dry-run-enforcement` already provides.
Blocking CI is the judge's domain; the guardian nudges.

### Confirmation

`python -m pytest tests/test_adr_guardian.py tests/test_adr_guardian_state.py
-q` covers: an `--adr` stamp writes the entry without touching the tier
timestamp; a recorded `violation` makes the tier due despite a fresh tier
timestamp and the nudge names the count; a tier stamp preserves the map; pruning
drops entries for deleted ADR files; `--adr` without `--verdict` is refused.

## Decision Contract

### Must

* Per-ADR verdicts live in `llm_tier.adrs` in `.adr-kit-state.json`, per-machine
  and advisory, under the existing state lock.
* `stamp llm --adr` requires `--verdict` and records exactly one ADR without
  updating `llm_tier.last_run` and without appending a trend entry.
* A recorded `violation` keeps the llm tier due, and the nudge names how many
  are outstanding.
* The sweep skill stamps each ADR as its verdict lands and prints per-ADR
  progress.

### Must Not

* Do not write per-ADR judge state into a tracked file from any adr-kit command.
* Do not let a tier-level stamp erase or rewrite the per-ADR map.
* Do not treat a timeout or error as a verdict; only `ok` and `violation` stamp.

### Exceptions

* None.

### Verification

* `bin/adr-guardian` (`cmd_stamp`, `_compute_due_tiers`, `_format_guardian_block`)
* `tests/test_adr_guardian.py`, `tests/test_adr_guardian_state.py`
* `skills/guardian/SKILL.md` step 3b

## Consequences

### Positive

* An interrupted 25-minute sweep keeps every verdict it reached; the next sweep
  pays only for what is missing.
* A violation found on Tuesday still fails the sweep on Friday, on the machine
  that found it, until a re-judge clears it — the tier can no longer go quiet by
  timestamp alone.
* Progress is visible per ADR, so a long sweep is distinguishable from a hung
  one.
* No new file, no new lock, no schema migration: one key inside a structure that
  already tolerates unknown keys.

### Negative

* Verdicts do not travel between machines or checkouts. A CI runner starting
  from a clean checkout re-judges everything. Accepted: that is what the
  advisory contract means, and the tracked alternative remains available
  downstream where it is a project's own decision.
* The map grows with the judged set (a few kilobytes at hundreds of ADRs).
  Pruning on stamp bounds it to existing ADR files.
* Two sessions sweeping concurrently stamp interleaved verdicts. The lock keeps
  writes consistent; the last verdict per ADR wins, which is the same
  last-writer-wins posture the rest of the state file already has.

## Pros and Cons of the Options

### Option A

* Good, because granularity fixes the loss-of-work problem without touching the
  advisory contract.
* Good, because it is the smallest change that meets all four acceptance
  criteria of TASK-154.
* Bad, because CI gets no shared memory — by design, not by omission.

### Option B

* Good, because verdicts travel with the checkout and CI pays once per interval.
* Bad, because every sweep then writes to the working tree, sweeps on two
  machines produce merge conflicts in a generated file, and an advisory nudge
  system acquires a ledger it promised not to be (spec task-9).
* Bad, because it moves a machine fact into tracked content, against ADR-025's
  boundary.

### Option C

* Good, because each audience gets its preferred store.
* Bad, because two stores of the same fact drift, and reconciling them needs
  precedence rules that neither the guardian's contract nor ADR-025 wants to
  host. The export half also has no consumer inside this kit to keep it honest.

### Option D

* Good, because it costs nothing.
* Bad, because a 25-minute interruptible process summarised by one timestamp
  either loses work or claims work that never happened, and a mid-sweep
  violation evaporates at the next stamp.

## Open Questions

* None.

## Related Decisions

* **ADR-025** (tracked configuration selects, machines introduce): the boundary
  that keeps verdicts out of tracked files.
* **ADR-011** (deterministic engine, human-gated conversation): the split that
  puts state in the guardian and progress in the skill.
* **ADR-036** (host-only judge): fixed the one-call-per-ADR cost shape this
  design has to live with.

## References

* TASK-154, including the downstream prototype
  (OTGW-firmware `otgw-1.x.x`, `scripts/adr-judge-weekly.py`) and the measured
  call costs (20.2–27.8 s per isolated call, 9-ADR sample, 21× spread in
  Decision length).
* Spec task-9: multi-session safety of `.adr-kit-state.json`.
* `bin/adr-guardian` design-invariants block: check is read-only and always
  exits 0; stamp writes only the state file.
