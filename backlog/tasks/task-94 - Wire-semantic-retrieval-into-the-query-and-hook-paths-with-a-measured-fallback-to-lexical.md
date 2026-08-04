---
id: TASK-94
title: >-
  Wire semantic retrieval into the query and hook paths, with a measured
  fallback to lexical
status: In Progress
assignee: []
created_date: '2026-08-03 19:31'
updated_date: '2026-08-04 00:33'
labels:
  - retrieval
  - hooks
dependencies:
  - TASK-92
  - TASK-93
priority: high
ordinal: 1200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implementation half of the A1 decision. The vector layer exists and nothing shipped reaches it: `query_adr_context` and `hooks/adr_hook_core.py` rank lexically, so the store is a diagnostic rather than a feature. Under the spec's own reading (R6.1, "How to read this document"), a mechanism no shipped path reaches does not count as implemented.

Route chosen by the maintainer: embed the query at the moment it is asked, in a query step and in a hook. The corpus stays a build step — re-embedding 18 ADRs on every prompt would be model work on text that has not changed.

Three properties keep it inside the contract, and each needs a test rather than a promise:

1. **Budget.** R21's ceiling, with the backend's own timeout well under it. Measured, not asserted. The manifest budgets are 500 ms for `session-start` and `user-prompt-submit` and 100 ms for the pre/post-tool events — an embedding round trip does not fit the 100 ms events, so those keep reading the index only.
2. **Fail-soft.** An unreachable, slow or erroring backend falls back to lexical ranking and the output names which route answered. It never fails the hook and never blocks the prompt.
3. **Default backend.** The local runtime of R16, so the common case stays offline and key-free. A remote endpoint is the user's choice, made in the settings surface after being told the latency and privacy consequence.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `query_adr_context` embeds the query and ranks by vector similarity when the store is present and the backend answers
- [ ] #2 The hook path reaches the same engine on the 500 ms events; the 100 ms pre/post-tool events keep the index-only route
- [x] #3 An unreachable backend, a timeout and a malformed response each fall back to lexical ranking, exit 0, and label the route in the output — one test per failure mode
- [ ] #4 A latency test measures the query-embedding path against R21 and fails when it exceeds the budget, using the fixture contract of ADR-015 rather than wall-clock on a live model
- [x] #5 The retrieval route (`vector` or `lexical`) is visible to the user in the injected block, so a silent degradation is impossible
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude
created: 2026-08-04 00:33
---
**Engine half done; the hook wiring and the latency fixture remain.**

`query_adr_context` takes an optional `embedder` callable. With one, plus a store, it reorders by cosine similarity and reports `route: "vector"`; without one, `route: "lexical"` — today's behaviour unchanged. AC#1, AC#3 and AC#5 are done, with ten tests.

**The embedder is a callable rather than an import, and that decision is the load-bearing part.** `bin/adr_query.py` must stay reachable from a hook, so it imports nothing that can touch a model or the network — asserted by AST walk in `test_adr_vector_store_contract.py`, which is precisely the assertion that stops someone putting embedding *into* the hook to make it simpler. Dependency injection satisfies ADR-020 without weakening that guarantee, and it is also how the per-event budget split gets expressed: whoever can reach a backend decides whether to pass one.

**A defect the tests caught that would have shipped looking correct.** The similarity lookup read `row["id"]`, but `query_records` returns records keyed on `adr_id`. Every row scored zero and the order was left untouched — on a two-record fixture that is indistinguishable from a working vector route. The two ordering tests use opposite query vectors for exactly this reason.

**Remaining, and they are real work rather than polish:**

- **AC#2** — the hook wiring. `evaluate()` does not currently carry an embedder, so passing one from `hooks/adr-hook.py` down to `_query` means threading it through the dispatch. The entrypoint is the right place to construct it: it already spawns `adr-judge`, so it is the one hook-path module that may reach out.
- **AC#4** — the R21 latency test through ADR-015's fixture contract rather than wall-clock against a live model.
---
<!-- COMMENTS:END -->
