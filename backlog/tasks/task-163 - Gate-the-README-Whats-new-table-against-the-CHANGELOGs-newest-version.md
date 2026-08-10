---
id: TASK-163
title: Gate the README "What's new" table against the CHANGELOG's newest version
status: To Do
assignee: []
created_date: '2026-08-09 16:12'
labels:
  - release
  - tooling
dependencies: []
references:
  - 'https://github.com/rvdbreemen/adr-kit/pull/90'
  - docs/RELEASING.md
  - scripts/check-release-version.py
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
- [ ] #1 check-release-version.py fails when the CHANGELOG's newest version has no matching row in the README's What's new table
- [ ] #2 The failure message names the missing version and points at the README section, not just "mismatch"
- [ ] #3 The gate is covered by a test that would fail if the check were removed
- [ ] #4 docs/RELEASING.md step 2 states that the row is now enforced and that the prose review still is not
<!-- AC:END -->
