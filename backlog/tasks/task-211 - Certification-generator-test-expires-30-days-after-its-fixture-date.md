---
id: TASK-211
title: Certification generator test expires 30 days after its fixture date
status: In Progress
assignee: []
created_date: '2026-10-03 13:44'
updated_date: '2026-10-03 13:45'
labels:
  - tests
  - ci
dependencies: []
priority: high
type: bug
ordinal: 55000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
test_public_generator_entrypoint_validates_and_renders_support_matrix feeds tests/certification/simulated-pass.json, whose contract_date is fixed at 2026-08-19, to build-client-adapters.py --certify. validate() rejects evidence older than 30 days (scripts/build-client-adapters.py:85), so the test has failed since 2026-09-18 on every machine and in CI (seen on PR #158, ubuntu/macos/windows, and on clean dev locally). The 30-day freshness rule is the intended policy for real evidence; the test should exercise the generator, not the calendar.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The test passes regardless of today's date, without weakening the 30-day rule for real evidence
- [x] #2 A stale bundle is still rejected (covered by a test)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Fix: the test writes a copy of simulated-pass.json to tmp_path with contract_date set to today (bundle plus all three records). The 30-day rule in build-client-adapters.py is unchanged. AC#2 was already covered by test_candidate_freshness_and_windows_identity_are_binding (contract_date 2000-01-01 -> 'stale'). tests/test_client_certification.py: 16 passed locally.
<!-- SECTION:NOTES:END -->
