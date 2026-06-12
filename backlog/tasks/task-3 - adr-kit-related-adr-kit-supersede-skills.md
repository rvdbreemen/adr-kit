---
id: TASK-3
title: '/adr-kit:related + /adr-kit:supersede skills'
status: To Do
assignee: []
created_date: '2026-05-31 13:19'
updated_date: '2026-06-12 21:06'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Graph + supersession workflows. (3) bin/adr-related + skills/related: walk Related Decisions + supersession refs, show inbound/outbound edges (read-only), reusing adr-status/adr-context parse helpers. (4) skills/supersede: draft superseding ADR via adr-generator, flip old ADR Status (only allowed edit), wire Related both ways, verify chain via adr-related + adr-lint. Related must land before supersede.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 bin/adr-related prints inbound + outbound edges for an ADR; tests cover it; read-only
- [ ] #2 skills/related wraps the bin
- [ ] #3 skills/supersede drafts new ADR, flips old Status to Superseded by ADR-M, updates Related both ways, appends status_history
- [ ] #4 Supersede verified against the repo's own ADR chain: bin/adr-lint stays clean, no dangling Related links
- [ ] #5 pytest green, adr-lint clean, docs (README + guide + instructions), version bump, released (user sign-off)
<!-- AC:END -->
