---
id: TASK-96
title: >-
  Make Open Questions append-only, so deleting a question costs more than
  answering it
status: In Progress
assignee: []
created_date: '2026-08-03 19:32'
updated_date: '2026-08-03 20:53'
labels:
  - adr
  - lint
  - grilling
  - decision
dependencies: []
priority: high
ordinal: 1400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Every consumer of open-questions data checks only *unresolved* items — `bin/adr:600`, `bin/adr-lint:1460-1470`, `bin/adr_readiness.py:259-273`, `bin/adr_guardian_queue.py:50` — and `bin/adr_readiness.py:273` records `open_questions_resolved: not bool(record.get("open_questions"))`.

Deleting a question therefore raises the quality score and clears the acceptance gate exactly as answering it does, while `bin/adr answer` is the strictly more expensive path. The cheapest route through the gates destroys the record of the grilling. Nobody has to act in bad faith for this to happen; it is what the incentive rewards.

**Decided (maintainer, 2026-08-03).** For a Proposed ADR, `## Open Questions` is append-only: a question may go from open to answered and nowhere else. A question that disappears without a matching `- [x] … **Answered <date> by <signer>:** …` line is a lint FAIL. No new artefact, and it reuses the regex already at `bin/adr:740`.

Limit to state in the ADR: the check needs the previous version of the file, so it needs git. Outside a repository — or on a file with no history — it degrades to advisory rather than pretending to know. That is a real hole and naming it is better than a check that silently passes.

Extends or supersedes ADR-011. Spec: R9.1, R9.3.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An ADR records the append-only rule, why the incentive existed, and the git dependency that bounds the check
- [ ] #2 A question removed from a Proposed ADR without a matching answered line is a lint FAIL, with the question text quoted in the message
- [ ] #3 `bin/adr answer` remains the supported way to close one, and a test proves the answered form passes
- [ ] #4 Readiness stops treating deletion and answering as equivalent: the score distinguishes 'answered' from 'gone'
- [ ] #5 Outside a git repository the check is advisory and says so, rather than passing silently
- [ ] #6 A test deletes a question and expects FAIL; a test answers it and expects PASS
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude
created: 2026-08-03 20:53
---
Decision recorded: ADR-022, Proposed, passes all gates.

One thing the ADR settles that the task left implicit: how an author retracts a question that turned out to be malformed. Answering it with the reason it does not apply — one command, and it leaves the record a future reader needs rather than a gap. Without that route the append-only rule would be an unsatisfiable precondition for anyone who mis-worded a question, which spec R15 forbids.

The git dependency is in the Decision Contract as an explicit advisory degradation, with the hole named: an author can still delete a question in the same commit that creates the file. Closing that would need the session ledger the decision rejected, so it is accepted rather than mitigated.

Remaining: AC#2 through AC#6 are implementation.
---
<!-- COMMENTS:END -->
