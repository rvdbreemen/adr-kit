---
id: TASK-82
title: 'Make quality trigger grilling, and persist the questions and answers'
status: To Do
assignee: []
created_date: '2026-08-01 10:34'
labels:
  - spec-gap
  - R9
  - grilling
  - quality
dependencies: []
priority: medium
ordinal: 87500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
spec.md R9. What ships is strong on the acceptance side and empty on the evaluation side.

**Nothing evaluates whether an ADR is good enough.** The work queue is status-based: `rank_proposed` (`bin/adr_guardian_queue.py:39,60-78`) enrols every Proposed ADR, and a perfectly sharp one is queued identically to an empty one, with quality only a tiebreaker in the sort. Readiness "quality" is three booleans (decision text present, any verified_in, no open questions — `bin/adr_readiness.py:238-247`). The real evaluator, `bin/adr-quality` (weighted four gates, exit 1 below 0.70), is doubly disconnected: no skill invokes it, and its only in-repo caller is `_assert_auto_accept_eligible` on the `accept --auto` path that nothing reaches. A low score therefore never triggers grilling. Accepted ADRs are never evaluated for sharpness at all.

**"Every question and every answer recorded" is structurally impossible as built.** The only instruction is `skills/grill/SKILL.md:40` "Record the answer in the Proposed ADR immediately". There is no transcript file, no frontmatter field, no writer, no schema slot. The one place a question can live is `## Open Questions`, which by design holds only *unresolved* items, and acceptance requires that list to be empty (`bin/adr:556-560`). So every question that was actually answered must be deleted before the ADR can be accepted. What survives is Status History: the actor and date of the transition, not the interrogation.

That matters beyond bookkeeping. The reasoning behind a decision is exactly what a future reader needs to re-evaluate it, and re-evaluation is what supersession depends on (spec R0).

**One dependency worth fixing here too:** the SessionStart grill nudge reads `docs/adr/.adr-kit-readiness.json`, written only by `adr-guardian refresh-readiness`, which is invoked by nothing but prose in `skills/guardian/SKILL.md:185`. It is gitignored with a 24 h TTL, so on a fresh clone the nudge stays silent until some model happens to run the sweep.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A quality score below the threshold puts an ADR into the grilling queue, and a sharp ADR does not
- [ ] #2 Accepted ADRs are periodically evaluated too, so quality decay is visible rather than frozen at acceptance time
- [ ] #3 Questions and their answers are persisted in a durable, schema-defined place that survives acceptance
- [ ] #4 Answered questions no longer have to be deleted to satisfy the acceptance gate; unresolved and resolved are distinct states
- [ ] #5 refresh-readiness is invoked by a mechanism rather than by prose, or the nudge stops depending on its cache
- [ ] #6 bin/adr-quality is reachable from a shipped path
<!-- AC:END -->
