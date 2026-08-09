---
id: TASK-82
title: 'Make quality trigger grilling, and persist the questions and answers'
status: Done
assignee: []
created_date: '2026-08-01 10:34'
updated_date: '2026-08-02 20:51'
labels:
  - spec-gap
  - R9
  - grilling
  - quality
dependencies: []
modified_files:
  - bin/adr_quality_core.py
  - bin/adr-quality
  - bin/adr_readiness.py
  - bin/adr-readiness
  - bin/adr_guardian_queue.py
  - bin/adr-guardian
  - bin/adr
  - skills/grill/SKILL.md
  - skills/guardian/SKILL.md
  - templates/adr-template.md
  - templates/adr-template.madr.md
  - templates/adr-template.nygard.md
  - templates/adr-template.canonical.md
  - tests/test_adr_quality_triggers_grilling.py
  - tests/test_adr_guardian_queue.py
  - tests/test_adr_mcp.py
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
- [x] #1 A quality score below the threshold puts an ADR into the grilling queue, and a sharp ADR does not
- [x] #2 Accepted ADRs are periodically evaluated too, so quality decay is visible rather than frozen at acceptance time
- [x] #3 Questions and their answers are persisted in a durable, schema-defined place that survives acceptance
- [x] #4 Answered questions no longer have to be deleted to satisfy the acceptance gate; unresolved and resolved are distinct states
- [x] #5 refresh-readiness is invoked by a mechanism rather than by prose, or the nudge stops depending on its cache
- [x] #6 bin/adr-quality is reachable from a shipped path
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
**AC#6/#1 — the real scorer is reachable, and it drives the queue.** `bin/adr_quality_core.py` makes the weighted four-gate scorer importable (scores unchanged by the move), so readiness reads it in-process instead of computing quality from three booleans, and `bin/adr-quality` becomes the rendering shell. Below-threshold is now a queue reason in its own right — and the absence of every reason is a reason to leave, so a Proposed ADR that is sharp, unlinked, unshipped and asking nothing drops out instead of padding the list. The readiness `quality` object carries `source`, `threshold` and `below_threshold` so a reader can tell a real score from the structural fallback.

**AC#2 — decay is visible.** `adr-quality --adr-dir --status Accepted` sweeps records that were scored once at acceptance and then frozen, exits 1 on decay, and the guardian's cheap tier runs it. The documented response is a supersession or a retirement, never a rewrite — an Accepted body is immutable.

**AC#3/#4 — the exchange survives, and no new persistence layer was needed.** `unresolved_open_questions` already skipped `[x]` and `Answered:` items, so a checked line carrying its answer survives acceptance untouched; the capability existed and nothing wrote it. `bin/adr answer ADR-NNN --question <n|text> --answer <text>` writes `- [x] <question> — **Answered <date> by <signer>:** <answer>`, resolving the signer like every other lifecycle command. It refuses an empty answer, refuses an ambiguous target while listing the choices, and preserves the blank line before the next heading. The grill skill and all four templates now document it and forbid deleting an answered question.

**AC#5 — the nudge no longer waits for a model to read a sentence.** `refresh-readiness` existed and only prose in the guardian skill ever called it, so on a fresh clone the gitignored 24 h cache stayed empty and the nudge stayed silent. `adr-guardian check` now rebuilds the queue in-process when the cache is missing or expired, skips entirely while a valid one exists (the common case costs one `stat`), and fails open in every direction — a session must never fail to start because a nudge could not be computed. Measured 227–288 ms warm, inside the 500 ms SessionStart budget; `check` still spawns nothing.

The adr_readiness MCP golden (id 8) was regenerated deliberately, with a note in the test explaining that the payload change was intentional and dated to this commit.

19 new tests in `tests/test_adr_quality_triggers_grilling.py`; full suite green (1432 passed, 13 skipped).
<!-- SECTION:FINAL_SUMMARY:END -->
