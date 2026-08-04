---
id: TASK-93
title: >-
  Join authority from ADR-INDEX.json at search time, so a superseded ADR can
  never be handed over as governing
status: To Do
assignee: []
created_date: '2026-08-03 19:31'
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
- [ ] #1 `search()` reads status, `superseded_by` and authority from `ADR-INDEX.json`, never from the stored entry
- [ ] #2 A test supersedes an ADR without touching its Decision, then asserts the store no longer returns it as `governing` and that `superseded_by` is populated
- [ ] #3 An entry whose `adr_id` is missing from the index is dropped from results, with a test
- [ ] #4 `adr-embed status` distinguishes 'content changed, rebuild needed' from 'index is stale, authority unavailable' — two different problems with two different fixes
- [ ] #5 No rebuild of the store is required for a supersession to take effect, and a test proves it
<!-- AC:END -->
