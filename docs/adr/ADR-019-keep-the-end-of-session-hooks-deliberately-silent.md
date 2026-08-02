---
id: "ADR-019"
title: "Keep the End-of-Session Hooks Deliberately Silent"
status: "Proposed"
date: "2026-08-02"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
topics:
  - "end-of-session silence"
  - "hook cost"
  - "unrecorded decisions"
aliases:
  - "Stop hook"
  - "SessionEnd hook"
  - "end-of-session summary"
components:
  - "adr-audit"
symbols:
  - "NOOP_EVENTS"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-019 Keep the End-of-Session Hooks Deliberately Silent

## Status

Proposed, 2026-08-02.

## Status History

```yaml
status_history:
  - date: 2026-08-02
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: TASK-86 requires the Stop/SessionEnd silence to be a recorded decision rather than an undocumented no-op
    changed_via: adr-kit
```

## Context and Problem Statement

`Stop`, `SubagentStop` and `SessionEnd` are accepted by the hook runner and
answered with nothing. They sit in `NOOP_EVENTS` (`hooks/adr_hook_core.py`) and
are registered by no client in `hooks/manifest.json`. Nothing anywhere said why.

That silence is load-bearing in a way worth naming. The question these events
would answer — *work finished; were architectural decisions made that nobody
recorded?* — is precisely the question spec R2's second clause needs a home
for. Its absence is not a missing feature so much as a missing sentence, and a
future reader finding three no-ops with no explanation will reasonably assume
the work was simply never done.

The constraint that produced the silence is real and specific. Every hook in
this kit today is deterministic, model-free, offline, and inside the two-second
budget ADR-015 makes a test fixture contract. Answering "were decisions made?"
over an entire session means reading the session, and reading a session for
architectural significance is a judgement call — which is a model call.

There is a second constraint that matters more than it first appears: a session
does not end when the user is watching. `SessionEnd` fires as the terminal
closes. A hook that spends money there spends it on an event nobody sees fire,
produces output nobody reads, and cannot ask before spending. Every other
paying path in this toolkit — the LLM judge, the guardian's LLM tier — is
either opt-in or asks first, and neither property survives at session end.

## Decision Drivers

* Hooks are the deterministic layer; ADR-004 makes the pre-edit tier the only
  fail-closed one, and every other tier degrades rather than blocks.
* ADR-015 fixes a two-second budget for the hook path as a contract, not a goal.
* Spending must be visible and refusable, per ADR-001's opt-in posture and
  ADR-017's per-ADR isolation.
* An undocumented no-op is indistinguishable from an unfinished feature.

## Considered Options

* Keep the silence, and record why.
* Add a deterministic end-of-session summary that lists changed surfaces
  without judging them.
* Allow one bounded model call at session end.

## Decision Outcome

Chosen option: **keep the silence, and record why** — this ADR is the record.
`Stop`, `SubagentStop` and `SessionEnd` stay in `NOOP_EVENTS`, each with a
comment stating its reason, and no client registers them.

The question they would answer is not abandoned; it moves to a place where the
user is present and can refuse. `/adr-kit:audit` (TASK-84) answers "are we
still on course?" on demand, over a diff or the whole codebase, and
`adr-suggest` already detects a diff that introduces an unrecorded decision.
Both run when someone asks, which is the property session end cannot offer.

### Confirmation

`NOOP_EVENTS` carries a per-entry rationale comment, and
`tests/test_adr_hook_noop_events.py` asserts the three end-of-work events stay
silent and that the comment is present. A future change that wires one of them
up will fail that test and have to come back here first.

## Decision Contract

### Must

* `stop`, `subagentstop` and `sessionend` return empty output and exit 0.
* `NOOP_EVENTS` carries a reason per entry, in the source, not only here.
* The unrecorded-decision question stays available on demand through
  `/adr-kit:audit` and `adr-suggest`.

### Must Not

* No hook may spend money on an event the user cannot see fire and cannot
  refuse.
* No end-of-session hook may be registered by any client while this ADR stands.

### Exceptions

A deterministic end-of-session summary — one that only *lists* changed surfaces
without judging significance — does not need a model and would not violate the
cost rule. It is excluded here for a different reason: it produces output at
the moment the user has stopped reading. If a client ever exposes a session-end
surface the user actually sees, that is a new fact and this decision should be
superseded rather than stretched.

### Verification

`bin/adr-hook.py --event Stop` produces no output and exits 0.

## Consequences

### Positive

* The silence is now a decision a reader can evaluate, not a gap they must
  guess about.
* The hook path keeps its single most useful property: it never costs anything
  and never blocks on a model.
* The cost rule stays simple and checkable — every paying path in adr-kit is
  either opt-in or asks first.

### Negative

* "Were decisions made this session?" now requires someone to ask. A session
  that ends without anyone asking records nothing, and that is a real gap, not
  a mitigated one.
* Spec R2's second clause has no automatic home, and this ADR does not give it
  one.

## Pros and Cons of the Options

### Keep the silence (chosen)

* Good, because it preserves the free, fast, deterministic character of every
  hook.
* Good, because the question survives in `/adr-kit:audit`, where a user is
  present.
* Bad, because nothing fires automatically at the moment the evidence is
  freshest.

### Deterministic end-of-session summary

* Good, because it costs nothing and needs no model.
* Bad, because listing changed files without judging significance is close to
  what `git status` already says, and the judgement is the valuable half.
* Bad, because it writes at the moment attention has left.

### One bounded model call at session end

* Good, because it is the only option that actually answers the question
  automatically.
* Bad, because it would be the first hook to spend, on an unseen event, with no
  way to ask first — which contradicts the opt-in posture of ADR-001 and the
  cost transparency of ADR-017.

## Related Decisions

* **ADR-004 Layered ADR Context Injection:** defines the injection tiers this
  decision declines to extend.
* **ADR-015 Two-Second Latency Budget:** the budget an end-of-session model
  call could not meet.
* **ADR-017 Run the LLM Judge by Default on the Host Agent Model:** the cost
  posture this decision keeps intact.

## References

* `hooks/adr_hook_core.py` (`NOOP_EVENTS`)
* `hooks/manifest.json`
* `bin/adr-audit`, `skills/audit/SKILL.md`
* `docs/client-support.md`
