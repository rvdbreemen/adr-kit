---
id: "ADR-022"
title: "Make Open Questions Append-Only for a Proposed ADR"
status: "Accepted"
date: "2026-08-04"
binding: true
gate: "adr-open-questions-append-only-v1"
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
related:
  - "ADR-011"
topics:
  - "grilling"
  - "lint"
  - "readiness"
aliases:
  - "open questions"
  - "append-only"
components:
  - "adr-lint"
  - "adr-readiness"
  - "adr"
symbols:
  - "open_questions_resolved"
  - "ANSWERED_LINE_RE"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-022 Make Open Questions Append-Only for a Proposed ADR

## Status

Accepted, 2026-08-04.

## Status History

```yaml
status_history:
  - date: 2026-08-03
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: deleting a question scores exactly as well as answering it, and is the cheaper path
    changed_via: adr-kit
  - date: 2026-08-03
    status: Proposed
    changed_by: "User: Robert van den Breemen"
    reason: ADR-022 constrains the grilling readiness model ADR-011 established
    changed_via: adr-kit lifecycle
  - date: 2026-08-04
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Accepted by the maintainer in the spec gap-analysis review; the decision stands, its gate and binding flag follow when the implementation ships.
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

Grilling exists so that the reasoning behind a decision survives the session
that produced it. `## Open Questions` is where an unresolved point waits until
someone settles it, and `bin/adr answer` is the command that settles one,
rewriting the item as `- [x] <question> — **Answered <date> by <signer>:**
<answer>`.

Every consumer of that data checks only *unresolved* items:

* `bin/adr:600`
* `bin/adr-lint:1460-1470`
* `bin/adr_readiness.py:259-273`
* `bin/adr_guardian_queue.py:50`

and `bin/adr_readiness.py:273` records the outcome as
`open_questions_resolved: not bool(record.get("open_questions"))`.

Deleting a line therefore produces the identical result to answering it: the
readiness score rises, the acceptance gate clears, and the guardian queue stops
listing the ADR. Answering is the strictly more expensive path — it requires
knowing the answer, and it requires a signer.

So the cheapest route through the gates destroys the record of the grilling.
Nobody has to act in bad faith for this to happen; it is what the incentive
rewards, and an agent optimising for a green gate will find it. The decision
then reaches Accepted with a Status History naming who flipped the status and no
trace of what they were asked.

## Decision Drivers

* The reasoning behind an accepted decision must outlive its session — the
  premise of R0.
* Cheap must not beat correct. A gate that is easier to satisfy destructively
  than honestly is a gate that trains the wrong behaviour.
* No new artefact that can drift out of step with the ADR.
* spec R15: a blocking gate must be satisfiable by editing the record.
* An honest correction — a question that turned out to be malformed or
  irrelevant — must still be possible.

## Considered Options

* **Make `## Open Questions` append-only for a Proposed ADR**, with removal
  without an answer as a lint FAIL.
* **A per-ADR session ledger** the grill appends to as each question is asked,
  with the lint cross-checking ledger entries against answered lines.
* **Repair the score only** — teach readiness to distinguish "answered" from
  "gone" and leave the text ungated.

## Decision Outcome

Chosen option: **`## Open Questions` is append-only while an ADR is Proposed**,
because it removes the incentive at its source rather than adjusting one of the
four places that read it, and because it needs no artefact that can drift.

A question in a Proposed ADR may move from open to answered and nowhere else. A
question that disappears without a corresponding `- [x] … **Answered …** …` line
is a lint FAIL naming the question text that vanished. The existing regex at
`bin/adr:740` already recognises both forms, so this is a comparison, not a new
parser.

Readiness stops treating the two as equivalent. `open_questions_resolved`
becomes a statement about questions that were *answered*, not about the section
being empty, so an ADR cannot reach the acceptance gate by having had nothing
asked of it.

An honest retraction stays available and stays visible: answer the question with
the reason it does not apply. That is one command, it is cheaper than arguing
with a gate, and it leaves the record a future reader needs — the question was
considered and here is why it was dropped.

### The limit, stated rather than discovered

The check compares the section against its previous state, so it needs the
previous state, which means it needs git. Outside a repository, or on a file
with no history, it degrades to **advisory** and says so.

That is a real hole: a determined author can delete a question in the same
commit that creates the file. It is named here rather than papered over, because
a check that silently passes where it cannot see is worse than one that reports
its own blind spot. The hole is small in practice — the grill writes questions
in one commit and they are answered in later ones — and closing it would require
the ledger this decision rejected.

### Confirmation

Delete an open question from a Proposed ADR and expect a FAIL quoting the
question. Answer the same question with `bin/adr answer` and expect a PASS. Run
both outside a git repository and expect an advisory rather than either verdict.
Assert that readiness reports a deleted question differently from an answered
one.

## Decision Contract

### Must

* Treat the disappearance of an open question from a Proposed ADR, without a
  matching answered line, as a lint FAIL.
* Quote the vanished question text in the finding, so the fix is obvious.
* Distinguish "answered" from "absent" in the readiness signal.
* Degrade to advisory, with a stated reason, where the previous state cannot be
  read.
* Keep `bin/adr answer` the supported way to close a question.

### Must Not

* Introduce a second artefact recording the grilling exchange.
* Block on an Accepted ADR — this constraint governs the Proposed window, where
  the questions are live.
* Treat an empty `## Open Questions` section as evidence that questions were
  resolved.
* Pass silently where the check cannot see.

### Exceptions

* Outside a git repository, or where the ADR has no recorded prior state, the
  finding is advisory.

### Verification

* `adr-open-questions-append-only-v1`: the gate this decision is to be anchored
  by. It does not exist yet, so `gate` is null and `binding` is false: a
  frontmatter that declares enforcement it cannot deliver is worse than one
  that admits the gap. Both fields flip back together when the gate ships,
  covering the delete case, the answer case, and the no-history case.

## Consequences

### Positive

* Answering becomes the cheapest path through the gate, which is the whole point.
* The reasoning behind an acceptance survives in the one file that already
  carries the decision.
* No new file, and one comparison added to a parser that already recognises both
  line forms.
* All 4 existing consumers keep reading the same section; none needs a new data
  source.

### Negative

* An author correcting a badly worded question has to answer it rather than
  delete it. That is one extra command, and it produces a record rather than a
  gap, so it is a cost worth paying.
* The check is blind in a repository with no history, which is stated in the
  contract as an advisory rather than hidden.
* Four call sites read open-questions data and all four have to agree on the new
  distinction; a fifth added later that keeps the old test would reintroduce the
  incentive quietly.

## Pros and Cons of the Options

### Append-only, deletion is a FAIL

* Good, because it removes the incentive rather than compensating for it.
* Good, because it adds no artefact.
* Bad, because it needs git history to see the previous state.

### A per-ADR session ledger

* Good, because it preserves the entire interrogation, including questions that
  never reached the ADR.
* Bad, because a second artefact can drift, and a hand-edited ADR desynchronises
  it immediately.

### Repair the score only

* Good, because it is the smallest change and needs no lint code.
* Bad, because deleting the record remains possible; it merely stops paying.

## Open Questions

* None.

## Related Decisions

* Extends ADR-011, which established the human-gated grilling workflow and the
  readiness model this constrains.
* Applies ADR-009's principle that a heuristic must be bounded to where a finding
  is actionable: this one is bounded to Proposed ADRs and to a comparison the
  tool can actually make.
* Governed by spec R15's requirement that a blocking gate be satisfiable by
  editing the record — here, by answering the question.

## References

* `bin/adr_readiness.py:273` — `open_questions_resolved: not bool(...)`, the line
  that makes deletion and answering equivalent.
* `bin/adr:740` — the regex that already recognises both the open and the
  answered form.
* `bin/adr:600`, `bin/adr-lint:1460-1470`, `bin/adr_guardian_queue.py:50` — the
  other three consumers that read only unresolved items.
* `spec.md` R9.1, R9.3, R15.
