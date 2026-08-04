---
id: TASK-95
title: >-
  Let the hook regenerate a stale ADR index, under a lock and only on the events
  that can afford it
status: In Progress
assignee: []
created_date: '2026-08-03 19:31'
updated_date: '2026-08-03 20:53'
labels:
  - hooks
  - adr
  - decision
dependencies: []
priority: high
ordinal: 1300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
When an agent writes `docs/adr/ADR-NNN.md` directly — the common case in a harness — the generated index goes stale, `query_adr_context(..., strict_index=True)` raises `IndexQueryError("generated ADR graph is stale")`, and `adr_hook_core._query` swallows it into `[]`. ADR injection then goes dark for the rest of the session with no message.

**Decided (maintainer, 2026-08-03).** The hook regenerates the index itself. This reverses the read-only property `hooks/adr_hook_core.py` documents in its own first line, so the ADR has to say so and carry the consequence rather than bury it.

Measured on this repository (18 ADRs), which shapes the design:

- freshness probe via `index_probably_fresh`: **2.8 ms**
- full in-process render (`load_adr_records` + markdown + graph + context): **84 ms median** (69-99 ms), about **4.7 ms per ADR**
- the same work through a subprocess: **302 ms median** — so in-process, never spawned

At that rate a 100-ADR set renders in ~470 ms and a 200-ADR set in ~940 ms. The 100 ms `pre-tool-use` and `post-tool-use` budgets cannot hold it at any realistic size, so those events keep reading and render the staleness message instead. `session-start` and `user-prompt-submit` carry 500 ms budgets and do the regeneration.

Two failure modes that a write on the hot path introduces, both of which the ADR must answer: two sessions regenerating at once (a lock file, and the loser reads rather than waits), and a set large enough to blow the budget (measure first, bail out to the message when the projection exceeds the budget).

Amends ADR-007. Spec: R7, R7.3, R21.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An ADR records the decision, names the read-only property it reverses, and states the concurrency and size limits it accepts
- [ ] #2 `session-start` and `user-prompt-submit` regenerate a stale index in-process, never by spawning `bin/adr-index`
- [ ] #3 `pre-tool-use` and `post-tool-use` keep reading only and render 'the ADR index is stale; run bin/adr-index docs/adr' rather than silence
- [ ] #4 A lock guards concurrent regeneration; a second session that cannot take the lock reads what is there instead of waiting, with a test that runs two at once
- [ ] #5 Regeneration is skipped and the message rendered when the projected render time exceeds the event budget, so a large ADR set degrades to a nudge rather than a timeout
- [ ] #6 An end-to-end test writes an ADR file, submits a prompt, and asserts the new ADR is injected in the same session
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude
created: 2026-08-03 20:53
---
Decision recorded: ADR-021, Proposed, passes all gates.

It states what the task asked for and one thing the task did not anticipate. The measurements now in the record: probe 2.8 ms, in-process render 84 ms median (69-99 ms, ~4.7 ms/ADR), subprocess 302 ms. Those numbers are what partition the events — 500 ms for `session-start` and `user-prompt-submit` regenerate, 100 ms for the edit tier does not, because 4.7 ms/ADR cannot fit 100 ms at any realistic set size.

The unanticipated part: the PostToolUse route the task listed as an alternative was rejected for a reason worth keeping. It only covers writes that pass through an observed tool, so an ADR arriving by `git checkout`, from an editor, or from a subagent whose events are not wired leaves the index stale with nothing having fired. The session-scoped probe asks about state rather than events, so it catches all of them. PostToolUse stays available later as an optimisation, not as the mechanism.

Remaining: AC#2 through AC#6 are implementation, blocked on nothing but time.
---
<!-- COMMENTS:END -->
