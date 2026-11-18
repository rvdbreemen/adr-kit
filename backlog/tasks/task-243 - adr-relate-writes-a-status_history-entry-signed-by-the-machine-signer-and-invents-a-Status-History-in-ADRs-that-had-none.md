---
id: TASK-243
title: >-
  adr relate writes a status_history entry signed by the machine signer and
  invents a Status History in ADRs that had none
status: In Progress
assignee:
  - '@claude'
created_date: '2026-11-18T11:55:00Z'
updated_date: '2026-11-18T12:29:00Z'
labels: []
dependencies: []
ordinal: 85000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
bin/adr relate (command_relate) calls ensure_status_history() and append_status_history() on both ADRs. Its docstring and commit c2e55f2 say the link is frontmatter-only reference bookkeeping and that the body of an Accepted ADR stays untouched. In practice it (a) appends a 'Related to ADR-NNN' entry signed with the resolved signer (the machine-local lifecycle.signer, e.g. 'User: <maintainer>') although that person made no edit, and (b) on an ADR without a Status History creates the section with a 'Recovered from the record' Accepted entry that never existed. Seen in OTGW-firmware on 2026-11-18 (ADR-255 relate to ADR-101/102/142/174), where every such line had to be corrected by hand. Fix: relate writes only the related frontmatter on both sides; the body, including any Status History, stays byte-identical.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A test fails on current dev: relate on an ADR without a Status History changes its body (an invented section with a recovered entry)
- [x] #2 A test fails on current dev: relate appends a status_history entry signed by the configured signer
- [ ] #3 After the fix relate and relate --remove leave both bodies byte-identical and only change the related frontmatter; existing relate tests stay green; python -m pytest -q green
- [x] #4 CHANGELOG [Unreleased] names the fix
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-11-18 Red on dev ce18f6b: two new tests in tests/test_adr_cross_references.py fail with 'relate invented a Status History' and 'relate signed a history entry for the machine signer'. Fix: command_relate writes only the related frontmatter (bin/adr), no signer resolved; generated codex/ and copilot/ copies regenerated (build-client-adapters.py, --check clean). tests/test_adr_cross_references.py 15/15. Full python -m pytest -q: 2152 passed, 25 skipped, 1 failed: tests/test_cli_performance.py::test_lint_and_retire_meet_hard_ceiling_on_this_repo ('adr-lint p50 2412ms exceeds the 2000ms user-wait ceiling'); it fails the same way on a clean origin/dev checkout on this machine (other builds and test suites were running), and it times adr-lint/retire, which this change does not touch.
<!-- SECTION:NOTES:END -->
