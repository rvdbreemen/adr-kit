---
id: "ADR-047"
title: "Cap supporting ADRs per response and let them fill only the slots left under the limit"
status: "Proposed"
date: "2026-10-11"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
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

Proposed, 2026-10-11.

## Status History

```yaml
status_history:
  - date: 2026-10-11
    status: Proposed
    changed_by: "User: Claude"
    reason: Initial proposal
    changed_via: adr-kit
```

## Context and Problem Statement

ADR-014's Decision Outcome says: "A primary result may expand to at most two
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

The record and the engine disagree. Markdown is the authority that agents and
people read, so the disagreement misleads them. Which one is right?

## Decision Drivers

* The Accepted record must describe what the engine does; agents act on the
  record.
* An Accepted ADR is never rewritten. A correction is an amending record.
* Issue #190 deserves an accurate answer.
* Retrieval behaviour should not change without a measured reason. The
  measurement shows the current behaviour is not a constraint in practice.

## Considered Options

* Amend the record to the per-response, fill-to-limit behaviour the engine has.
* Change the engine to a cap per primary result, as the record reads.
* Redesign neighbour selection, ranking neighbours by relevance or allowing
  them beyond `limit`.
* Do nothing.

## Decision Outcome

Chosen option: **amend the record to the behaviour the engine has**, because
that behaviour is what the 2026-07-23 human decision meant, and the measurement
shows it does not withhold context in practice.

The supporting expansion of ADR-014 is read as follows:

* A response contains at most two supporting ADRs in total
  (`MAX_SUPPORTING_RESULTS = 2`), whatever the number of primaries.
* Supporting ADRs only fill slots left under `limit`. They never displace a
  scored match and never make a response longer than `limit`.
* Only resolved `related` links expand a result. Historical neighbours stay
  out unless `include_history` is set.
* Neighbours of the highest-ranked primary come first, in ADR-number order: the
  stable ADR-ID tie-breaker that ADR-014 names. A supporting ADR has no query
  score; it is listed with score 0 and the match reason "one-hop supporting
  ADR".

No engine change follows from this record. When this record is Accepted,
ADR-014's status line reads `Amended by ADR-047`; ADR-014's decision text stays
as it is.

**Proposed by:** Claude (agent) at the request of User: Robert van den Breemen,
from the 2026-10-11 defect sweep and GitHub issue #190. **Decision Maker:** User:
Robert van den Breemen confirmed on 2026-10-11 that the 2026-07-23 decision
meant two supporting ADRs per response (Open Question 1).

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
* Read ADR-014's sentence "A primary result may expand to at most two one-hop
  supporting ADRs" as a cap per primary result.

### Exceptions

* None.

### Verification

* The three tests named under Confirmation.

## Consequences

### Positive

* The record matches the engine, and issue #190 can be answered from it.
* No retrieval behaviour changes, and no project's probes move.

### Negative

* Ordering neighbours by ADR number favours older records, as issue #190
  observed. Ranking neighbours by relevance is a possible follow-up, recorded
  here and not decided.
* A caller who wants more connected context has to raise `limit` or follow each
  result's `related_ids` with `adr-related` / `adr_related`.

## Pros and Cons of the Options

### Amend the record

* Good, because nothing that works changes, and the record becomes truthful.
* Bad, because the per-response cap is less generous than a per-primary reading
  would be when the limit has room.

### Change the engine to a cap per primary

* Good, because the existing sentence would become literally true.
* Bad, because it changes retrieval output without a measured need, and it
  contradicts what the decision maker meant.

### Redesign neighbour selection

* Good, because it could address the lower-number preference that #190 noticed.
* Bad, because it is a new ranking decision that needs its own evidence.

### Do nothing

* Good, because nothing changes.
* Bad, because the Accepted record keeps telling readers something the engine
  does not do.

## Open Questions

- [x] Did the 2026-07-23 human decision mean at most two supporting ADRs per response (what the engine does), or two per primary result (what ADR-014's Decision Outcome says)? — **Answered 2026-10-11 by User: Robert van den Breemen:** Two per response. The engine is right: at most two supporting ADRs per response, only in slots left under limit. ADR-014's Decision Outcome sentence is wrong, and because an Accepted ADR is not rewritten, this amending record corrects it. The answer to issue #190 explains these semantics.

## Related Decisions

* Amends ADR-014 (Use the generated ADR graph as the selective-context query
  engine): corrects the reading of its supporting-expansion sentence; every
  other part of ADR-014 is unchanged.
* ADR-004 (Layered ADR context injection): the injection tiers that consume
  these results.

## References

* `bin/adr_query.py:45`, `:386-395`, `:548-568`.
* ADR-014, Decision Outcome and the Open Questions item answered on 2026-07-23.
* <https://github.com/rvdbreemen/adr-kit/issues/190>.
* 2026-10-11 defect sweep (TASK-222): DEF-28.
