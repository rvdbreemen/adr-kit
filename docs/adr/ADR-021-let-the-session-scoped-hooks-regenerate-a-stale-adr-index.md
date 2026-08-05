---
id: "ADR-021"
title: "Let the Session-Scoped Hooks Regenerate a Stale ADR Index"
status: "Accepted"
date: "2026-08-04"
binding: true
gate: "adr-hook-index-refresh-v1"
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
related:
  - "ADR-007"
topics:
  - "index freshness"
  - "hooks"
  - "retrieval"
aliases:
  - "stale index"
  - "hook write"
components:
  - "lifecycle hooks"
  - "adr-index"
symbols:
  - "index_probably_fresh"
  - "IndexQueryError"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-021 Let the Session-Scoped Hooks Regenerate a Stale ADR Index

## Status

Accepted, 2026-08-04.

## Status History

```yaml
status_history:
  - date: 2026-08-03
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: an agent writing an ADR file directly turns injection dark for the rest of the session, silently
    changed_via: adr-kit
  - date: 2026-08-03
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: ADR-021 says what a consumer does when the generated index is stale
    changed_via: adr-kit lifecycle
  - date: 2026-08-04
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Accepted by the maintainer in the spec gap-analysis review; the decision stands, its gate and binding flag follow when the implementation ships.
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

An agent writes `docs/adr/ADR-NNN-something.md` with its Write tool. This is not
an edge case; it is the common case in a harness, and `/adr-kit:adr` produces it
by design.

From that moment the generated index is stale. `hooks/adr_hook_core.py` `_query`
calls `query_adr_context(..., strict_index=True)`, which raises
`IndexQueryError("generated ADR graph is stale")`, and `_query` catches it and
returns an empty list. Every subsequent hook in that session injects nothing. No
message, no warning, no exit code — hooks fail open, and silence is what
fail-open looks like from the outside.

The session most actively working on decisions is therefore the session with no
decision context. The user cannot tell, because an empty injection is
indistinguishable from "no ADR was relevant".

The obstacle to fixing it is a property, not a bug. `hooks/adr_hook_core.py`
documents itself as read-only in its own first line, and that property is why
the hot path is safe to run on every prompt in every session. Repairing the
staleness means letting a hook write.

Two measurements shape what is affordable. On this repository's nineteen ADRs:

* the freshness probe `index_probably_fresh` costs **2.8 ms**;
* a full in-process render — `load_adr_records` plus the Markdown, graph and
  context artefacts — costs **84 ms median** (69–99 ms over seven runs), about
  **4.7 ms per ADR**;
* the same work through a subprocess costs **302 ms median**.

At 4.7 ms per ADR a 100-ADR set renders in roughly 470 ms and a 200-ADR set in
roughly 940 ms. `hooks/manifest.json` budgets 500 ms for `session-start` and
`user-prompt-submit`, and 100 ms for the pre- and post-tool events.

## Decision Drivers

* An agent that writes ADRs must not thereby lose ADR context.
* The failure must never be silent again, whatever else is decided.
* The 2 s ceiling of spec R21 and the per-event budgets in the manifest are
  contracts, not targets.
* Two sessions in one repository must not corrupt the index by writing it at
  once.
* The repair must scale down gracefully: a large ADR set should degrade to a
  message, not to a timeout.

## Considered Options

* **Regenerate in the hooks that can afford it, announce in the ones that
  cannot.**
* **Regenerate in every hook**, including the 100 ms edit-tier events.
* **Never write; announce only** — render "the ADR index is stale; run
  `bin/adr-index docs/adr`" instead of silence.
* **Regenerate out of band from PostToolUse** after an ADR file is written.

## Decision Outcome

Chosen option: **the session-scoped hooks regenerate a stale index in-process;
the edit-tier hooks stay read-only and say so**, because it repairs the session
that caused the staleness at the first moment it can, and because a hook that
regenerates is only defensible where the budget can absorb it.

Concretely:

* `session-start` and `user-prompt-submit`, at 500 ms, probe for staleness and
  regenerate when they find it.
* `pre-tool-use`, `post-tool-use` and the plan-exit branch, at 100 ms, keep the
  read-only path and render the staleness message rather than empty output. At
  4.7 ms per ADR a full render cannot fit 100 ms at any realistic set size, and
  a hook that blows its budget is killed by the client, which returns the
  problem to silence.

Regeneration is **in-process**, through `bin/adr_index_core.py`, never by
spawning `bin/adr-index`: 84 ms against 302 ms, and the subprocess variant does
not fit the budget it would be running in.

Two failure modes that a write on the hot path introduces are answered here
rather than discovered later.

**Concurrency.** A lock file guards the regeneration. A session that cannot take
the lock reads what is on disk and continues; it does not wait. Waiting inside a
hook budget converts a contended index into a killed hook, and the other session
is about to write the same bytes anyway.

**Size.** Before regenerating, the hook projects the cost from the ADR count at
the measured per-ADR rate. If the projection exceeds the event budget it skips
the write and renders the staleness message. A repository large enough to break
the budget gets a nudge, which is what the read-only option would have given it
anyway.

This reverses the read-only property `adr_hook_core` states about itself. The
reversal is deliberate and bounded: exactly two events may write, exactly one
artefact set may be written, the write is idempotent because it regenerates
derived files from the Markdown that is the authority, and every other property
of the hot path — fail-open, model-free at these events, no network, no daemon —
is unchanged.

### Why not the alternatives

**Regenerating everywhere** puts an 84 ms write inside a 100 ms hard timeout, on
the platform where process creation alone measured 18 ms at the median. It would
fail first on the largest repositories, which are the ones that need it most.

**Announcing only** preserves the property intact and is the smallest change. It
was the recommended option and was rejected by the maintainer for a concrete
reason: in a harness the reader of that message is the same agent that just
wrote the file, and an agent that can act on the message can equally well have
the work done for it. The message survives as the fallback, which is where its
value actually is.

**PostToolUse out of band** fixes the cause rather than the symptom and is
attractive, but it only covers writes that pass through a tool this kit observes.
An ADR arriving by `git checkout`, by an editor, or from a subagent whose events
are not wired leaves the index stale with nothing having fired. The
session-scoped probe catches all of them because it asks about state rather than
about events. Nothing here forbids adding the PostToolUse trigger later as an
optimisation.

### Confirmation

Write an ADR file directly, submit a prompt in the same session, and assert the
new ADR is injected. Run two hooks concurrently against one repository and
assert the index is well-formed and neither exits non-zero. Set an ADR count
whose projected render exceeds the budget and assert the message is rendered and
nothing is written.

## Decision Contract

### Must

* Probe index freshness before every retrieval, at a cost bounded by the
  measured 2.8 ms probe rather than a full load.
* Regenerate in-process, never by spawning the generator.
* Restrict regeneration to `session-start` and `user-prompt-submit`.
* Render an actionable staleness message on any event that finds the index stale
  and does not regenerate it.
* Guard regeneration with a lock; a session that cannot acquire it reads what is
  present and continues without waiting.
* Skip regeneration and render the message when the projected render cost
  exceeds the event's declared budget.
* Keep every hook fail-open: any fault in this path exits 0 with whatever
  context was available.

### Must Not

* Write from `pre-tool-use`, `post-tool-use`, or the plan-exit branch.
* Block, wait, or retry on a contended lock.
* Write any artefact other than the generated index set.
* Return empty output when the index is stale — silence is the defect this
  decision exists to remove.

### Exceptions

* None.

### Verification

* `adr-hook-index-refresh-v1`: the gate this decision is to be anchored by. It
  does not exist yet, so `gate` is null and `binding` is false: a frontmatter
  that declares enforcement it cannot deliver is worse than one that admits the
  gap. Both fields flip back together when the gate ships, covering the write-
  then-prompt sequence, the concurrent-hook case, and the budget bail-out.

## Consequences

### Positive

* A session that authors ADRs keeps its ADR context.
* The failure mode that remains — a stale index the hook chose not to fix — is
  audible instead of silent.
* The repair sits in the one place that observes state rather than events, so it
  covers writes this kit never sees.

### Negative

* **The hot path can now write.** That is a real reduction in what can be said
  about `adr_hook_core` at a glance, and it is why the permitted events, the
  permitted artefacts and the lock are stated as contract rather than left to
  implementation.
* Two sessions starting together will have one of them read a briefly stale
  index, for the 84 ms the other one holds the lock. Accepted deliberately: the
  alternative is waiting inside a 500 ms budget.
* A stale index costs `session-start` and `user-prompt-submit` 84 ms they did not
  spend before — 17% of their 500 ms budget on a 19-ADR set, and the reason the
  budget projection exists at all. A fresh index costs the 2.8 ms probe, which is
  under 1%.
* The per-ADR render cost of 4.7 ms is measured on one machine and one
  repository. A slow filesystem shifts it, which is why the guard is a projection
  checked against the budget rather than a fixed ADR-count threshold.

## Pros and Cons of the Options

### Regenerate in the session-scoped hooks only

* Good, because it repairs the session that caused the problem.
* Good, because the write sits where the budget can absorb it.
* Bad, because the read-only property no longer holds unqualified.

### Regenerate in every hook

* Good, because the repair happens at the earliest possible event.
* Bad, because 84 ms does not fit a 100 ms hard timeout with process startup
  already spent.

### Announce only

* Good, because the read-only property survives untouched.
* Bad, because the reader is usually the agent that caused the staleness.

### PostToolUse out of band

* Good, because it addresses the cause.
* Bad, because it only sees writes that pass through an observed tool.

## Open Questions

* None.

## Related Decisions

* Amends the operational half of ADR-007, which generates the index but does not
  say what a consumer does when it is stale.
* Depends on ADR-020's authority join: once authority is read from the index,
  index freshness becomes a correctness property and not only a completeness one.
* Bounded by ADR-015's latency contract and spec R21.

## References

* `hooks/adr_hook_core.py` `_query` — the `IndexQueryError` swallowed into an
  empty result.
* `bin/adr_index_core.py` `index_probably_fresh`, `stale_index_artifacts` — the
  in-process probe and renderer this decision uses.
* `hooks/manifest.json` — the per-event budgets this decision partitions on.
* `tests/test_adr_index_freshness.py` — the existing evidence that hand-edited
  ADRs leave all three artefacts stale.
* `spec.md` R7, R7.3, R21.
