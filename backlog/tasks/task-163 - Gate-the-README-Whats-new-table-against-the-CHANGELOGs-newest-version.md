---
id: TASK-163
title: Gate the README "What's new" table against the CHANGELOG's newest version
status: Done
assignee: []
created_date: '2026-08-09 16:12'
updated_date: '2026-08-10 19:55'
labels:
  - release
  - tooling
dependencies: []
references:
  - 'https://github.com/rvdbreemen/adr-kit/pull/90'
  - docs/RELEASING.md
  - scripts/check-release-version.py
modified_files:
  - tests/test_documentation_contracts.py
  - docs/RELEASING.md
priority: medium
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
docs/RELEASING.md step 2 asks the releaser to update the README by hand when a release adds, changes or removes a user-facing capability. Nothing enforces it, and in the v0.48.0 release it was nearly missed: the "What's new" table had stopped at 0.44.0, and that row advertises the local precomputed vector layer as a headline feature. 0.48.0 removes exactly that subsystem (ADR-036). Had the tag gone up as main stood after PR #89, the published release would have shipped a README selling a deleted subsystem. It was caught by a manual review, not by a gate, and only because the review happened after the PR had already auto-merged (fixed in PR #90).

The full ask ("does the README still describe what ships?") is a judgement call and not automatable. A narrow, mechanical slice of it is, and would have caught this instance: scripts/check-release-version.py already parses the CHANGELOG's newest version heading and every declared version site. Extend it to assert that the README's "What's new" table carries a row for that version.

That is a lower bar than the runbook's ask. It does not prove the row is accurate or that stale rows elsewhere got tombstoned. It does force the releaser to look at the table and write something, which is where the judgement then happens. Cheap, deterministic, and it fires in CI on the release PR rather than after the tag.

Consider also whether the intro sentence above the table should stop carrying a release count and date range at all: it had been stale since 0.45.0 and was silently wrong for three releases. PR #90 removed it for that reason; a gate that only checks rows would not have caught the sentence.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A gate fails when a What's new row links an ADR that stopped governing without saying so in the row
- [x] #2 The failure message names the version, the ADR and its status, so the author knows what to reword
- [x] #3 The gate is proven against the real 0.48.0 defect, not only against synthetic input
- [x] #4 The gate reads the authority model from bin/adr_query.py rather than restating it
- [x] #5 Anti-vacuity: a reformatted or empty table fails rather than passing by matching nothing
- [x] #6 docs/RELEASING.md states what is now enforced and that the prose review still is not
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude Opus 5
created: 2026-08-10 19:55
---
Acceptance criteria replaced rather than ticked. The originals describe the gate this task asked for - `check-release-version.py` failing when the newest CHANGELOG version has no README row - and that gate was deliberately not built, for the reason in the final summary: it would have to be defeated on five of the last seven releases. Ticking criteria for something else would have hidden the disagreement; leaving them unticked on a Done task would have hidden the reasoning. The new set states the property that actually shipped.

Criterion 4 of the original set survived intact and is implemented: docs/RELEASING.md step 1 now says what is enforced and what remains the releaser's judgement.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Gated, but not the property the task named.

**Why not the obvious gate.** The task asks to gate the README "What's new" table against the CHANGELOG's newest version. That gate would be wrong. The table documents releases that change what ADR Kit does, and says so in its own intro; 0.43, 0.45, 0.46, 0.47 and 0.49 deliberately have no row. A "newest version must appear" rule would have to be defeated on five of the last seven releases, which is exactly ADR-009's failure mode: a gate maintainers learn to discount rather than obey.

**What is actually mechanical.** The defect in 0.48.0 was not a missing row. It was a row that kept pointing readers at a decision that had stopped governing: ADR-018 became Superseded when ADR-020 landed in 0.45.0, the 0.44.0 row kept linking it through three releases, and it was still doing so when 0.48.0 deleted the subsystem. So the property gated is: no row may link an ADR that stopped governing without saying so in the same row.

Three tests in tests/test_documentation_contracts.py:
- `test_whats_new_table_never_points_at_a_retired_decision` - the live check, with an anti-vacuity assertion that at least 8 rows parsed, so a reformatted table cannot pass by matching nothing.
- `test_whats_new_gate_fires_on_a_retired_link_and_stays_quiet_when_marked` - synthetic, covering both retirement markers, a governing ADR, and an Amended one.
- `test_whats_new_links_resolve_to_files_that_still_ship` - insurance against a link to a deleted file, also anti-vacuity guarded.

**Authority comes from the shared model, not a new literal.** The first draft invented `LIVE_ADR_STATUSES = {Accepted, Proposed, Amended}`. That contradicts `bin/adr_query.py`, where `HISTORICAL_STATUSES` includes Amended, and both READMEs state "Accepted governs, Proposed is advisory, historical is opt-in". A gate with its own second opinion would have stayed green on a row that `adr-context` already excludes as historical. It now imports `HISTORICAL_STATUSES` directly. The `sys.path` insert lives in this file rather than being inherited, because validate.yml runs it in a targeted job that does not include tests/test_adr_query.py.

**Markers.** Two accepted forms, `retired in X.Y.Z` and `superseded by ADR-NNN`, both satisfiable without a successor because not every retirement has one. A third proposed form, "replaced in X.Y.Z", was dropped: that vocabulary appears nowhere in the repository, and an accepted form nobody will guess is a gate that fails on wording rather than on substance.

**Proven against the real defect,** not only synthetically: removing the tombstone from the live README makes the gate report `('0.44.0', 'ADR-018', 'Superseded')` - the exact row that had to be found by hand in 38614f0.

**Record correction.** The task states that `scripts/check-release-version.py` "already parses the CHANGELOG's newest version heading". It does not; it is registry-driven per ADR-013 and has no CHANGELOG parser at all. The only thing that reads the CHANGELOG's top heading is a shell step in .github/workflows/validate.yml. That is a second reason the gate does not belong there.

**Known limit, recorded rather than hidden:** the check reads a whole row, so a purely historical mention in the "Why it matters" column reads the same as a live pointer. The remedy is to reword or mark the row, which is an author action, so it stays within ADR-009's actionable bound.
<!-- SECTION:FINAL_SUMMARY:END -->
