---
id: TASK-199
title: >-
  Nothing refuses a required section that holds only a migration placeholder at
  accept time
status: Done
assignee:
  - '@claude'
created_date: '2026-09-06 13:48'
updated_date: '2026-09-06 15:41'
labels:
  - bug
  - migrate
  - readiness
dependencies: []
priority: medium
ordinal: 43000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Measured on a real record: docs/adr/ADR-042 with its `## References` body replaced by the exact line adr-migrate writes, `- TODO: add verifiable references.`, passes the full acceptance gate set that bin/adr accept runs (schema,completeness,audit,evidence,clarity,consistency,policy with --strict) and scores 0.87 grade A in adr-quality, with completeness at 1.0 and evidence reporting references_present: true. The same record with an empty `## References` is blocked: missing sections: ['References (present but empty)'].

That gap is deliberate at arrival. TASK-198 and PR #146 established that an imported record must not fail a blocking gate on import, because a team that hits a wall on import disables the gate; test_adr_policy.py and test_migration_discovery.py pin it. Arrival is not acceptance, though. adr-migrate's `needs content: ## <heading>` report is currently the only signal, and it is printed once, at migrate time, to whoever ran the command. Nothing carries it to the person running adr accept days later.

Readiness and grill are the surfaces where 'imported but unfinished' belongs: bin/adr-readiness already answers 'is this Proposed record ready', the guardian already caches a 24-hour readiness queue, and /adr-kit:grill already walks unresolved items one question at a time. Reporting a placeholder there costs nothing at import and still reaches the operator before the record is frozen. Doing it in completeness would re-open exactly what PR #146 took back out.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 adr-readiness reports a required section whose only content is an adr-kit TODO placeholder, naming the section
- [x] #2 The arrival policy is untouched: test_adr_policy.py and test_migration_discovery.py still pass unchanged, and adr-lint still exits 0 on such a record
- [x] #3 A regression test covers a placeholder-only section reaching adr-readiness, and asserts adr-lint stays green on the same record
- [x] #4 The guardian queue keeps such a record enrolled: reporting the placeholder must not evict it by clearing its only signal
- [x] #5 Both placeholder spellings are detected, and an empty section is not described as a placeholder
- [x] #6 adr-migrate no longer claims that adr-lint and adr accept refuse a placeholder
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Measured first, then designed. A Proposed record whose `## References` holds only `- TODO: add verifiable references.` classifies `ready-for-confirmation` with `next_command: null` and zero findings. That classification is the defect, not a symptom of it.

1. bin/adr_format.py
   - `_PLACEHOLDER_LINE_RE` matches only the `- TODO:` list item bin/adr-migrate writes, not the `<!-- TODO: ... -->` comment the /adr-kit:migrate skill writes, while bin/adr-lint:1447-1459 already handles both. test_adr_policy.py:455-482 pins the two spellings as equivalent, so the detector is wrong. Match both.
   - `unfilled_required_sections` conflates empty with placeholder: it returns ['References'] for the empty fixture too. Split the scan so a caller can tell them apart, and keep the existing signature intact for bin/adr-migrate.

2. bin/adr_readiness.py
   - New code SECTION_PLACEHOLDER_ONLY in FINDING_CODES.
   - Emit it into `human_findings`, one per section, deterministically sorted. That flips classification to `needs-human-input`, which is the honest verdict and gives the record a `next_command`.
   - Guard both silent-failure paths: `normalize_profile` raises on the legal format values 'hybrid' and 'unknown', and readiness_for_record receives records with no readable file (tests/test_adr_readiness.py:206-224). Both must yield no signal rather than a finding or an exception, because bin/adr-guardian:456-457 swallows exceptions and returns 0, so a raise here would silently freeze the queue for 24 hours.

3. bin/adr_guardian_queue.py - load-bearing, not optional
   - `signals = (linked, shipped, ready, open_questions, below_threshold)` with `if not any(signals): continue`. For this exact population (unlinked, unshipped, quality 0.87 above the 0.70 threshold, no open questions) `ready` is the only true signal. Flipping the classification without this edit EVICTS the record from the queue, making it less visible than before the fix.
   - Add a sixth signal derived from the classification, its reason inserted before the unconditional `age N days` append (line 85) so it survives the reasons[:2] cut in hooks/adr_hook_core.py:279, and add it to the `_rank` tuple so it is not pushed past QUEUE_MAX_ACTIONS = 3.

4. bin/adr-migrate:236-239 prints "adr-lint reports them as incomplete and adr accept will refuse until they are written". Measured false since c476525. Leaving that while adding an honest signal elsewhere is incoherent; correct it.

5. Tests
   - readiness: placeholder record yields the finding, names the section, classifies needs-human-input; unreadable path and hybrid/unknown format yield no signal and no exception.
   - queue: the same record stays enrolled and its reason lands within the first two.
   - format: both placeholder spellings detected; `- None.` under Related Decisions stays real content.
   - arrival policy untouched: test_adr_policy.py and test_migration_discovery.py pass unchanged, and adr-lint still exits 0 on the same record.

6. Gates: regenerate codex/ and copilot/ (drift gate, tests/conftest.py:4-9); check whether the byte-compared MCP golden frame 8 covers a record that now emits the item, and regenerate in the same commit if so. No exit-1 path may be added to bin/adr-readiness: bin/adr-audit:328-329 forwards the code and bin/adr-guardian:1088-1093 reads non-zero as "skip the refresh".

Out of scope, filed separately: `age N days` is always 0 because readiness emits `evaluated_on` while the queue reads `date`; bin/adr-migrate:184-185 computes the before-delta with the target profile; a migration-created `## Related Decisions` holding `- None.` is never reported.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A Proposed record whose `## References` held only the line `bin/adr-migrate` writes classified `ready-for-confirmation` with `next_command: null` and no finding at all. That verdict was the defect, not a side effect of it.

Why nothing caught it: TASK-198 decided the completeness gate must not refuse such a record on arrival, because a team that hits a wall on import disables the gate. That decision is right and stands. What was missing is that nothing said anything later either: the migrator prints `needs content: ## <heading>` once, to whoever ran the command, and the person accepting the record days afterwards never sees it.

Changes:
- `bin/adr_readiness.py` emits `SECTION_PLACEHOLDER_ONLY` per section, naming it, into `human_findings`. The record moves to `needs-human-input` and gains a `/adr-kit:grill` next_command. No exit-1 path was added, deliberately: `bin/adr-audit` forwards the code verbatim and `bin/adr-guardian` reads non-zero as "skip the refresh", so an exit code here would silently freeze the queue.
- `bin/adr_guardian_queue.py` gained a `needs_human` signal. This half is load-bearing, not a nicety: enrollment is gated on `signals = (linked, shipped, ready, open_questions, below_threshold)` and for this exact population (unlinked, unshipped, quality 0.87 above the 0.70 threshold, no open questions) `ready` was the only true signal. Measured: flipping the classification without this produced 0 candidates, so the honest report would have made the record LESS visible than silence. Its reason sits before the unconditional `age N days` entry so it survives the `reasons[:2]` cut in the SessionStart block.
- `bin/adr_format.py`: `_PLACEHOLDER_LINE_RE` matched the `- TODO:` list item `bin/adr-migrate` writes but never the `<!-- TODO: -->` comment the `/adr-kit:migrate` skill writes, while `bin/adr-lint` has always stripped comments before counting and `test_adr_policy.py` pins the two as equivalent. A skill-migrated record was reported as finished. The helper also conflated empty with placeholder, so `placeholder_required_sections` now returns the narrower set and readiness cannot describe an empty heading as a placeholder.
- `bin/adr-migrate` printed "adr-lint reports them as incomplete and adr accept will refuse until they are written". Measurement contradicts both halves. It now says what actually happens and where the signal is.

Measured, not assumed:
- 212 real records (43 here, 169 in the OTGW corpus) and 238 ADR-shaped files including every fixture: zero new findings outside the two fixtures that genuinely carry a TODO, and zero sections whose only body is a non-TODO HTML comment, which is what makes the comment-stripping widening safe.
- Before: `ready-for-confirmation`, `next_command: null`, no findings. After: `needs-human-input`, `/adr-kit:grill ADR-042`, one finding naming `## References`. Queue: 0 candidates without the signal, 1 with it, reason at index 0.

Deliberate behaviour worth knowing: the scan runs regardless of status, so an already-Accepted record carrying a placeholder emits the finding while its classification stays `accepted` and `next_command` stays null. Readiness reports facts; classification delivers the verdict. Zero real records hit this today.

ACs #4 to #6 were added mid-flight, not scoped up front. The queue signal in particular came out of measuring the eviction, not out of the original plan: reporting the placeholder honestly turned out to remove the record from the queue, and that only showed up by running it.

Tests: 8 readiness cases (both spellings, the empty/placeholder split, an unreadable path, and the hybrid/unknown formats that make `normalize_profile` raise), 3 queue cases pinning the eviction, 4 detector cases. Full suite in four batches: 1887 passed, 12 skipped. `test_adr_policy.py` and `test_migration_discovery.py` pass unchanged, which is AC #2. Adapter drift gate green.

One test fails locally and is not a regression: `test_cli_performance.py::test_lint_and_retire_meet_hard_ceiling_on_this_repo`. `adr-retire` with no arguments walks the working tree, and this checkout carries 1094 untracked files under `graphify-out/` that CI never sees. Proven four ways: alternating A/B timing of both CLIs shows HEAD at or below the parent commit; a fresh worktree of the parent passes; copying this branch's `bin/` into that worktree also passes; and the failing tool is the one that walks the tree.

Follow-ups filed rather than folded in: TASK-200 (the queue's age signal is always 0 because readiness emits `evaluated_on` while the queue reads `date`), TASK-201 (adr-migrate computes its before-delta with the target profile), TASK-202 (a machine-written `- None.` under Related Decisions is never reported), TASK-203 (let the guardian's LLM tier judge whether a section that is present and not a placeholder actually says anything).
<!-- SECTION:FINAL_SUMMARY:END -->
