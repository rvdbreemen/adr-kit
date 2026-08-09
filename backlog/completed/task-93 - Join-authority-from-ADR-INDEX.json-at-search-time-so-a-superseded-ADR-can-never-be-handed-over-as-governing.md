---
id: TASK-93
title: >-
  Join authority from ADR-INDEX.json at search time, so a superseded ADR can
  never be handed over as governing
status: Done
assignee: []
created_date: '2026-08-03 19:31'
updated_date: '2026-08-04 00:18'
labels:
  - retrieval
  - correctness
dependencies:
  - TASK-92
priority: high
ordinal: 1100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implementation half of the A2 decision. The vector store keeps a frozen copy of status and `superseded_by` that a supersession never invalidates, so `search()` can label a retired decision `governing`. That is the authority separation ADR-014 and ADR-018 both spend paragraphs on, defeated by a stale field.

Route chosen: the store answers *which* ADRs, `ADR-INDEX.json` answers *what they are worth*. On every search, join status and `superseded_by` from the index by `adr_id` and derive authority there. Nothing about the frozen copy is trusted for authority; the embedded text stays as it is.

Consequence to handle rather than discover: this makes retrieval correctness depend on index freshness, which is why TASK-95 (the stale-index route) is a sibling and not an optional extra. An entry whose `adr_id` is absent from the index is a record that no longer exists — drop it from the results rather than returning it unlabelled.

Blocks TASK-94: wiring semantic retrieval into the hook before this lands would ship a path that hands superseded decisions to an agent as binding.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `search()` reads status, `superseded_by` and authority from `ADR-INDEX.json`, never from the stored entry
- [x] #2 A test supersedes an ADR without touching its Decision, then asserts the store no longer returns it as `governing` and that `superseded_by` is populated
- [x] #3 An entry whose `adr_id` is missing from the index is dropped from results, with a test
- [x] #4 `adr-embed status` distinguishes 'content changed, rebuild needed' from 'index is stale, authority unavailable' — two different problems with two different fixes
- [x] #5 No rebuild of the store is required for a supersession to take effect, and a test proves it
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
`search()` joins status, `superseded_by` and authority from `ADR-INDEX.json` on every call. The vectors find; the index decides.

**The defect is reproduced by the test before it is fixed by it.** `test_a_supersession_takes_effect_without_a_rebuild` asserts `staleness(...)["stale"] is False` first — that is the premise, not an accident — and only then that the search no longer returns the record as governing. Without that first assertion the test would pass on a store that simply happened to be rebuilt.

**Three properties the join had to get right, each tested:**

- An entry whose id the index does not carry is **dropped**, not returned unlabelled. A vector for a deleted ADR is a leftover.
- A missing or unreadable index returns `None`, which is distinguishable from "the index says this record is retired". Collapsing those would make an unreadable index silently empty every result — which reads to a user exactly like a repository with no decisions.
- Omitting the argument falls back to the stored copy, so the standalone diagnostic still works where no index has been generated.

**AC#4 splits the report rather than adding a state to one.** `adr-embed status` now carries an `authority` field alongside `drift`: `current`, `unavailable` (no readable index) or `orphaned-entries`. Content drift wants `adr-embed build`; a missing index wants `bin/adr-index`. One number for both would send the user to the wrong command.

Implements the second half of ADR-020. TASK-94 — embedding the query on the shipped paths — is the first half and remains open.

Full suite: 1548 passed, 13 skipped.
<!-- SECTION:FINAL_SUMMARY:END -->
