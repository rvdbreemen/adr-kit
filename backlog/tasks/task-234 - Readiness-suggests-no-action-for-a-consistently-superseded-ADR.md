---
id: TASK-234
title: Readiness suggests no action for a consistently superseded ADR
status: Done
assignee: []
created_date: '2026-10-11 21:26'
updated_date: '2026-10-11 22:46'
labels:
  - readiness
dependencies: []
ordinal: 77000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
adr-readiness gives every Superseded, Deprecated or Amended record classification supersession-required with next_command /adr-kit:grill --revalidate, so six finished records (ADR-001, 003, 014, 017, 018, 020) read as open work in the CLI and MCP output. Within ADR-011's seven classes: keep the label, but suggest the revalidate command only when SUPERSESSION_STATE_INCONSISTENT fires; a consistent terminal record gets next_command null.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A Superseded record whose superseded_by and status agree has next_command null
- [x] #2 A record with SUPERSESSION_STATE_INCONSISTENT keeps /adr-kit:grill --revalidate
- [x] #3 The readiness enum and schema version are unchanged (ADR-011)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Fixed in bin/adr_readiness.py (_supersession_inconsistent); test test_revalidate_is_suggested_only_for_an_inconsistent_supersession. Found on the way, left as is: _classification returns 'accepted' for an Accepted record that names superseded_by, before the supersession branch; the SUPERSESSION_STATE_INCONSISTENT finding still reports it.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
adr-readiness suggests /adr-kit:grill --revalidate only where status and successor disagree; a consistently superseded record keeps its ADR-011 label with next_command null. Test and CHANGELOG added; full suite 2087 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
