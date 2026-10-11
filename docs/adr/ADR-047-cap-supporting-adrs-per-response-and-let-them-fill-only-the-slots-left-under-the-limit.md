---
id: "ADR-047"
title: "Cap supporting ADRs per response and let them fill only the slots left under the limit"
status: "Accepted"
date: "2026-10-11"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
related:
  - "ADR-036"
topics:
  - "supporting ADRs"
  - "relationship expansion"
  - "retrieval ranking"
  - "selective context"
aliases:
  - "one-hop supporting ADR"
  - "MAX_SUPPORTING_RESULTS"
  - "issue 190"
components:
  - "bin/adr_query.py"
symbols:
  - "MAX_SUPPORTING_RESULTS"
  - "query_adr_context"
  - "_related_ids"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-047 Cap supporting ADRs per response and let them fill only the slots left under the limit

## Status

Accepted, 2026-10-11.

## Status History

```yaml
status_history:
  - date: 2026-10-11
    status: Proposed
    changed_by: "User: Claude"
    reason: Initial proposal
    changed_via: adr-kit
  - date: 2026-10-11
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Accepted decision after all four verification gates passed
    changed_via: adr-kit lifecycle
  - date: 2026-10-11
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: "ADR-047 amends ADR-036: at most two one-hop supporting ADRs per response, filling only the slots under limit"
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

ADR-014's Decision Outcome said: "A primary result may expand to at most two
one-hop supporting ADRs." That reads as a cap per primary result. The query
engine does something else:

* `MAX_SUPPORTING_RESULTS = 2` (`bin/adr_query.py:45`) caps the **whole
  response**. The expansion loop stops once two supporting ADRs have been
  collected across all primaries (`:548-565`).
* Supporting ADRs are appended only while the response is shorter than `limit`
  (`:566-568`). They fill slots that scored matches left free, and never
  displace one.
* Only resolved `related` links expand a result. Neighbours are taken from the
  highest-ranked primary first, in ADR-number order (`_related_ids`, `:386-395`),
  and carry score 0 with the match reason "one-hop supporting ADR".

ADR-014 is no longer in force. ADR-018 superseded it on 2026-08-01, ADR-020
superseded ADR-018, and the chain ends at ADR-036, which is Accepted. ADR-036's
item 4 keeps "lexical scoring over the generated index plus one-hop graph
neighbours" but states no cap. Since 2026-08-01 the cap the engine enforces has
had no Accepted record, and its only written statement, in a superseded record,
reads differently.

On 2026-10-09 an external user asked about exactly this in GitHub issue #190:
is the limit intentional, what would widening it change, and why are lower ADR
numbers preferred?

The 2026-10-11 defect sweep (TASK-222, DEF-28) measured the answer on ADR Kit's
own set at commit `f2f6fe2`:

* Of 43 ADRs, 36 have more than two `related` neighbours; the median is 6.
* Across 7 queries (the three retrieval probes plus four others) at `limit` 1,
  2, 3 and 5, raising the cap from 2 to 4, or removing it, changed 0 of the 28
  answers. The binding constraint is `limit`, not the cap.
* Example: "mcp server tools" at `limit` 5 returns ADR-016, ADR-039 and ADR-040
  as primaries, and ADR-010 and ADR-011 as supporting ADRs. Those are the two
  lowest-numbered neighbours of ADR-016 that are not already shown.

The engine enforces a rule that no Accepted record states, and the superseded
record that does state it reads differently. Markdown is the authority that
agents and people read, so the gap misleads them. Which reading is right, and
which record should carry it?

## Decision Drivers

* An Accepted record must describe what the engine does; agents act on the
  record.
* A rule the engine enforces needs an Accepted home. ADR-014's lapsed with its
  supersession, and ADR-036 left the cap unstated.
* An Accepted ADR is never rewritten. A refinement is an amending record.
* Issue #190 deserves an accurate answer.
* Retrieval behaviour should not change without a measured reason. The
  measurement shows the current behaviour is not a constraint in practice.

## Considered Options

* Record the per-response, fill-to-limit cap the engine has, as an amendment of
  ADR-036.
* Change the engine to a cap per primary result, as ADR-014 read.
* Redesign neighbour selection, ranking neighbours by relevance or allowing
  them beyond `limit`.
* Do nothing.

## Decision Outcome

Chosen option: **record the cap the engine has, as an amendment of ADR-036**,
because that behaviour is what the 2026-07-23 human decision meant, the
measurement shows it does not withhold context in practice, and ADR-036 is the
Accepted record whose item 4 decides the one-hop expansion.

ADR-036's one-hop graph neighbours (item 4, Retrieval) are bounded as follows:

* A response contains at most two supporting ADRs in total
  (`MAX_SUPPORTING_RESULTS = 2`), whatever the number of primaries.
* Supporting ADRs only fill slots left under `limit`. They never displace a
  scored match and never make a response longer than `limit`.
* Only resolved `related` links expand a result. Historical neighbours stay
  out unless `include_history` is set.
* Neighbours of the highest-ranked primary come first, in ADR-number order: the
  stable ADR-ID tie-breaker the engine has used since ADR-014. A supporting ADR
  has no query score; it is listed with score 0 and the match reason "one-hop
  supporting ADR".

No engine change follows from this record, and ADR-036's decision text stays as
it is.

**Proposed by:** Claude (agent) at the request of User: Robert van den Breemen,
from the 2026-10-11 defect sweep and GitHub issue #190. **Decision Maker:** User:
Robert van den Breemen confirmed on 2026-10-11 that the 2026-07-23 decision
meant two supporting ADRs per response (Open Question 1) and, once ADR-014
turned out to be superseded, that this record amends ADR-036 (Open Question 2).

### Confirmation

* `tests/test_adr_query.py::test_relationship_expansion_is_one_hop_and_capped_at_two`
  already covers one primary with three neighbours: two supporting ADRs, in ID
  order, with score 0.
* Two tests are added with this record:
  * two primaries that each have neighbours return at most two supporting ADRs
    in total;
  * a response whose `limit` is filled by primaries returns no supporting ADR.

## Decision Contract

### Must

* The query engine caps supporting ADRs at two per response.
* Supporting ADRs only fill slots left under `limit`.
* Supporting ADRs carry score 0 and the match reason "one-hop supporting ADR".

### Must Not

* Let a supporting ADR displace a scored match, or make a response longer than
  `limit`.
* Read the superseded ADR-014's sentence "A primary result may expand to at
  most two one-hop supporting ADRs" as the rule in force.

### Exceptions

* None.

### Verification

* The three tests named under Confirmation.

## Consequences

### Positive

* The cap has an Accepted record again, the record matches the engine, and
  issue #190 can be answered from it.
* No retrieval behaviour changes, and no project's probes move.

### Negative

* Ordering neighbours by ADR number favours older records, as issue #190
  observed. Ranking neighbours by relevance is a possible follow-up, recorded
  here and not decided.
* A caller who wants more connected context has to raise `limit` or follow each
  result's `related_ids` with `adr-related` / `adr_related`.

## Pros and Cons of the Options

### Record the cap as an amendment of ADR-036

* Good, because nothing that works changes, and the rule gets an Accepted,
  truthful record.
* Bad, because the per-response cap is less generous than a per-primary reading
  would be when the limit has room.

### Change the engine to a cap per primary

* Good, because ADR-014's sentence would become literally true.
* Bad, because it changes retrieval output without a measured need, it
  contradicts what the decision maker meant, and it would rest on a superseded
  record.

### Redesign neighbour selection

* Good, because it could address the lower-number preference that #190 noticed.
* Bad, because it is a new ranking decision that needs its own evidence.

### Do nothing

* Good, because nothing changes.
* Bad, because the cap keeps resting on a superseded record that reads
  differently.

## Open Questions

- [x] Did the 2026-07-23 human decision mean at most two supporting ADRs per response (what the engine does), or two per primary result (what ADR-014's Decision Outcome says)? — **Answered 2026-10-11 by User: Robert van den Breemen:** Two per response. The engine is right: at most two supporting ADRs per response, only in slots left under limit. ADR-014's Decision Outcome sentence is wrong, and because an Accepted ADR is not rewritten, this amending record corrects it. The answer to issue #190 explains these semantics.
- [x] ADR-014 turned out to be Superseded: ADR-018 replaced it on 2026-08-01, and the chain ends at ADR-036, whose item 4 keeps one-hop graph neighbours without a cap. Does this record amend ADR-036 instead of ADR-014 (recommended), stand alone without an amendment, or stay Proposed? — **Answered 2026-10-11 by User: Robert van den Breemen:** Amend ADR-036. ADR-036 is the Accepted record whose item 4 decides the one-hop expansion, so the cap belongs there; ADR-014 stays cited as the record where the cap was first decided. The decision itself does not change: at most two supporting ADRs per response, filling only the slots under limit.

## Related Decisions

* Amends ADR-036 (Retire the vector layer and run the judge on the host model
  only): bounds the one-hop graph neighbours of its item 4 (Retrieval); every
  other part of ADR-036 is unchanged.
* ADR-014 (Use the generated ADR graph as the selective-context query engine),
  Superseded by ADR-018 on 2026-08-01: where the cap was first decided, in the
  Open Questions item answered on 2026-07-23.
* ADR-004 (Layered ADR context injection): the injection tiers that consume
  these results.

## References

* `bin/adr_query.py:45`, `:386-395`, `:548-568`.
* ADR-036, Decision Outcome item 4 (Retrieval).
* ADR-014 (Superseded), Decision Outcome and the Open Questions item answered on
  2026-07-23.
* <https://github.com/rvdbreemen/adr-kit/issues/190>.
* 2026-10-11 defect sweep (TASK-222): DEF-28.
