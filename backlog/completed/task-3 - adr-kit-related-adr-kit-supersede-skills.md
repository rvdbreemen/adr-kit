---
id: TASK-3
title: '/adr-kit:related + /adr-kit:supersede skills'
status: Done
assignee: []
created_date: '2026-05-31 13:19'
updated_date: '2026-06-12 21:19'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Graph + supersession workflows. (3) bin/adr-related + skills/related: walk Related Decisions + supersession refs, show inbound/outbound edges (read-only), reusing adr-status/adr-context parse helpers. (4) skills/supersede: draft superseding ADR via adr-generator, flip old ADR Status (only allowed edit), wire Related both ways, verify chain via adr-related + adr-lint. Related must land before supersede.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 bin/adr-related prints inbound + outbound edges for an ADR; tests cover it; read-only
- [x] #2 skills/related wraps the bin
- [x] #3 skills/supersede drafts new ADR, flips old Status to Superseded by ADR-M, updates Related both ways, appends status_history
- [x] #4 Supersede verified against the repo's own ADR chain: bin/adr-lint stays clean, no dangling Related links
- [x] #5 pytest green, adr-lint clean, docs (README + guide + instructions), version bump, released (user sign-off)
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shipped in v0.28.0. bin/adr-related (outbound/inbound edges per reference kind, whole-token matching, dangling-link flags, 24 tests), /adr-kit:related (read-only, model-invocable), /adr-kit:supersede (graph-first guided flow, Proposed-only drafting, Status flip + status_history as only old-ADR edits, hard-stop on existing supersession pointer). Design note: the bidirectional Related link IS the Status line, preserving Accepted-ADR immutability.
<!-- SECTION:FINAL_SUMMARY:END -->
