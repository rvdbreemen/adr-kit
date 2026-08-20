---
id: "ADR-041"
title: "Automatically Hand Off Unfinished Proposed ADRs to Interactive Grilling"
status: "Accepted"
date: "2026-08-20"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
related:
  - "ADR-011"
topics:
  - "auto grilling"
  - "readiness"
aliases: []
components:
  - "adr-readiness"
  - "hooks"
symbols: []
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-041 Automatically Hand Off Unfinished Proposed ADRs to Interactive Grilling

## Status

Accepted, 2026-08-20.

## Status History

```yaml
status_history:
  - date: 2026-08-20
    status: Proposed
    changed_by: Robert van den Breemen
    reason: Initial proposal
    changed_via: adr-kit
  - date: 2026-08-20
    status: Proposed
    changed_by: Robert van den Breemen
    reason: Related to automatic interactive grilling
    changed_via: adr-kit lifecycle
  - date: 2026-08-20
    status: Proposed
    changed_by: Robert van den Breemen
    reason: Related to automatic interactive grilling
    changed_via: adr-kit lifecycle
  - date: 2026-08-20
    status: Proposed
    changed_by: Robert van den Breemen
    reason: Related to automatic interactive grilling
    changed_via: adr-kit lifecycle
  - date: 2026-08-20
    status: Proposed
    changed_by: Robert van den Breemen
    reason: Related to automatic interactive grilling
    changed_via: adr-kit lifecycle
  - date: 2026-08-20
    status: Proposed
    changed_by: Robert van den Breemen
    reason: Related to automatic interactive grilling
    changed_via: adr-kit lifecycle
  - date: 2026-08-20
    status: Proposed
    changed_by: Robert van den Breemen
    reason: Related to automatic interactive grilling
    changed_via: adr-kit lifecycle
  - date: 2026-08-20
    status: Proposed
    changed_by: Robert van den Breemen
    reason: Keep ADR-011 as the governing successor relationship
    changed_via: adr-kit lifecycle
  - date: 2026-08-20
    status: Proposed
    changed_by: Robert van den Breemen
    reason: Keep ADR-011 as the governing successor relationship
    changed_via: adr-kit lifecycle
  - date: 2026-08-20
    status: Proposed
    changed_by: Robert van den Breemen
    reason: Keep ADR-011 as the governing successor relationship
    changed_via: adr-kit lifecycle
  - date: 2026-08-20
    status: Proposed
    changed_by: Robert van den Breemen
    reason: Keep ADR-011 as the governing successor relationship
    changed_via: adr-kit lifecycle
  - date: 2026-08-20
    status: Proposed
    changed_by: Robert van den Breemen
    reason: Keep ADR-011 as the governing successor relationship
    changed_via: adr-kit lifecycle
  - date: 2026-08-20
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Accepted decision after all four verification gates passed
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

ADR Kit already computes deterministic readiness and ranks a bounded Proposed
ADR queue, but the resulting grill commands are only advisory. The agent or
engineer must notice the command and invoke it manually. That loses the moment
when an unfinished decision is already in front of an interactive session.

The current implementation deliberately made that trade-off. ADR-011 says that
hooks may emit a short, fail-open grill command but never start an interview.
ADR-002 says the SessionStart nudge is visible and the developer chooses
whether to act. TASK-45.13 made the same boundary an implementation contract:
hooks and pre-commit must not start an interactive grill, run a model, or add a
full readiness sweep.

The gap is narrower than those constraints require. A user-visible interactive
session can safely receive one automatic handoff without starting work in CI,
pre-commit, a background process, or an unattended lifecycle event. The
handoff must remain separate from lifecycle authority: the grill may ask and
record human answers, but only an explicit acceptance confirmation may invoke
`adr accept --confirm`.

## Decision Drivers

* Finish incomplete decisions at the first interactive moment where the user
  can answer the question.
* Keep detection deterministic, local, bounded, and shared with readiness and
  the Proposed queue.
* Preserve the human gate for answers, acceptance, rejection, and supersession.
* Avoid repeated questions, recursive dispatch, unattended model work, and
  surprise changes to Accepted ADRs.
* Keep the certified client workflow source canonical while allowing OpenCode
  to retain its separate adapter boundary.

## Considered Options

* **Automatic interactive handoff at the next user-visible prompt.** Read the
  existing derived queue, select one eligible Proposed ADR, and dispatch the
  native grill workflow once per session.
* **Start the interview from a hook, pre-commit, CI, or a background process.**
  This would remove the manual step but would run at moments where the user
  cannot reliably see, refuse, or answer the interview.
* **Keep the current advisory-only behavior.** This preserves every existing
  boundary but leaves unfinished decisions dependent on model attention.

## Decision Outcome

Chosen option: **automatic interactive handoff at the next user-visible
prompt**, because it closes the completion gap without turning a deterministic
hook into an interactive process or weakening lifecycle authority.

The readiness engine and `adr_guardian_queue` remain the sole source of
eligibility. An eligible Proposed record is one with unresolved human input,
`ready-for-confirmation`, an active implementation link, shipped evidence while
still Proposed, or a quality score below the existing `0.70` threshold. A
mechanical readiness failure is repaired or reported first. A stale or
superseded Accepted record is never edited; only an explicit revalidation path
may route it to `--revalidate` grilling.

SessionStart may prepare or refresh the disposable queue. The actual handoff
waits for a user-visible interactive prompt. The client dispatches at most one
candidate per session, carries its deterministic reason, and suppresses
recursive re-entry while that grill is active. If a client cannot dispatch a
workflow programmatically, it displays the exact native command and fails open.
The prompt context remains bounded by the existing 4096-character hook limit,
and the queue contributes at most three prepared actions.
The existing `UserPromptSubmit` event budget remains a 450 ms p50 and 900 ms
hard timeout; automatic detection adds no subprocess or model call to that
path.

Claude, Codex, and Copilot consume the canonical workflow contract and its
generated adapters. OpenCode uses its separate native plugin surface and does
not enter the certified three-client registry.

### Confirmation

The implementation is verified by deterministic readiness and queue fixtures,
one-handoff-per-session tests, fail-open hook tests, generated-client parity
checks, and lifecycle tests proving that the grill records answers but never
accepts an ADR without an explicit same-session confirmation.

## Decision Contract

### Must

* Derive eligibility from the shared readiness report and Proposed queue; do not
  create a second detector.
* Start automatic handoff only during an interactive, user-visible session and
  dispatch at most one target per session.
* Re-run authoritative readiness when grilling starts and preserve the
  one-question-at-a-time protocol.
* Keep the exact client-native grill command visible when dispatch is
  unavailable or fails.
* Keep automatic detection model-free, network-free, bounded, and fail-open.
* Keep the handoff context at or below 4096 characters and the prepared queue at
  or below three actions.
* Preserve append-only Open Questions and use `bin/adr answer` to record human
  answers.
* Require explicit same-session confirmation before invoking
  `adr accept --confirm`.

### Must Not

* Start an interactive interview from pre-commit, CI, `PreToolUse`,
  `PostToolUse`, a background process, or an unattended lifecycle event.
* Treat a queue cache or heuristic architecture signal as lifecycle authority.
* Automatically edit or accept an Accepted ADR, or infer acceptance from
  shipped code, a pull request, or source material.
* Launch a second grill recursively while the current grill is active.
* Add OpenCode to the certified three-client registry or duplicate the
  retrieval/readiness engine in TypeScript.

### Exceptions

* An Accepted ADR may be explicitly revalidated through the existing
  `--revalidate` entry point when drift or changed forces require it.
* A client-specific native dispatcher may start the handoff only when its
  interactive session and user-visible prompt are active.

### Verification

* `tests/test_adr_readiness.py` and `tests/test_adr_guardian_queue.py` verify
  deterministic eligibility and ranking.
* `tests/test_adr_auto_grill.py`, `tests/test_adr_grill_signal.py`, and
  `tests/test_adr_hook_dispatch_matrix.py` verify advisory-only unattended
  paths and bounded handoff output.
* `tests/test_adr_lifecycle.py` and `tests/test_adr_open_questions.py` verify
  answer recording and explicit acceptance authority.
* `python scripts/build-client-adapters.py --check` verifies generated parity.

## Consequences

### Positive

* Proposed decisions reach the human while their implementation context is
  still available, without requiring the user to copy a command from a nudge.
* Detection remains deterministic and reusable across clients.
* The current fail-open enforcement floor and human lifecycle authority remain
  intact.

### Negative

* Automatic handoff can interrupt an unrelated task; one-target-per-session,
  an opt-out, and a visible reason limit that cost.
* Client APIs differ, so some clients can only receive an imperative native
  command rather than perform a guaranteed programmatic dispatch. The command
  remains the fail-open fallback.
* A new successor decision is required because the default changes from
  advisory choice to automatic interactive handoff.

## Pros and Cons of the Options

### Option A

* Good, because it closes the unfinished-ADR gap at a user-present moment and
  keeps all answers and acceptance human-controlled.
* Bad, because the client workflow must suppress duplicate and recursive
  dispatch.

### Option B

* Good, because it could run without waiting for an interactive prompt.
* Bad, because it violates the current unattended-event and fail-open
  boundaries, and could spend or interrupt work without a user present.

## Open Questions

- [x] Confirm that automatic handoff is enabled by default only for interactive, — **Answered 2026-08-20 by User: Robert van den Breemen:** Yes. Enable automatic handoff by default only during a user-visible interactive session. Keep pre-commit, CI, SessionStart, PreToolUse, PostToolUse, background, and unattended lifecycle paths advisory. Support opt-out via grill.auto_start: false or ADR_KIT_AUTO_GRILL_DISABLE=1.
  user-visible sessions, with an opt-out for teams that prefer advisory-only
  behavior.

Answer them with `bin/adr answer`, which rewrites an item as
`- [x] <question> — **Answered <date> by <signer>:** <answer>`. A checked item
is resolved, so it no longer blocks acceptance and stays in the record. Do not
delete an answered question: the reasoning is what a future reader needs in
order to re-evaluate the decision.

## Related Decisions

* **ADR-002:** supplies the existing SessionStart guardian cadence and its
  visible, per-machine state model.
* **ADR-011:** defines deterministic readiness, one-question grilling, and
  human lifecycle authority; this proposal changes its automation boundary.
* **ADR-015:** bounds deterministic user-facing latency and requires measured
  fixture coverage for new paths.
* **ADR-022:** makes Proposed Open Questions append-only and preserves the
  grilling record.
* **ADR-024:** limits missing-decision work to user-present, fail-open moments.
* **ADR-039:** keeps OpenCode as a separate native adapter surface.

## References

* `bin/adr_readiness.py:276-369`
* `bin/adr_guardian_queue.py:39-112`
* `hooks/adr_hook_core.py:712-805`
* `hooks/manifest.json:30-39`
* `skills/grill/SKILL.md:15-84`
* `docs/adr-grilling.md:101-155`
* `TASK-185`
* OpenCode plugin API: https://opencode.ai/docs/plugins/
