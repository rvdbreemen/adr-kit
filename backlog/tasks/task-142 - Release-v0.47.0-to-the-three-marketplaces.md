---
id: TASK-142
title: Release v0.47.0 to the three marketplaces
status: In Progress
assignee: []
created_date: '2026-08-07 07:24'
updated_date: '2026-08-07 07:25'
labels: []
dependencies: []
ordinal: 113500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Cut v0.47.0 from `dev` into `main` per `docs/RELEASING.md` and ADR-012.

Carries the work of the 2026-08-06 backlog sweep and the C4 documentation refresh:

- **ADR-035** — `adr-suggest` now runs by default, on the same terms ADR-017 set for the judge. The opt-in rested on ADR-001, which ADR-017 superseded without carrying its reasoning to the second entry point. User-facing behaviour change, hence the minor bump.
- **ADR-034** — the hook manifest declares `network_allowed` per event rather than for the whole set; `pr-create` and `user-prompt-submit` override it with a stated reason.
- Two features that were wired, tested and dead end to end are now alive: ADR-024's pull-request nudge (the guard read `stdout` while `adr-suggest` writes to `stderr`) and `ADR_KIT_SUGGEST_DISABLE` (honoured by one caller only).
- The generated client-support matrix stopped granting a fail-closed edit tier that ADR-004 lists under its rejected alternatives.
- Eleven ADRs stopped explaining why their gate was null after it had shipped.
- One bump writer instead of two, and the CHANGELOG compare-link block is now a declared version site.

This is the first release whose compare-link block is written by the canonical tool rather than backfilled by hand.
<!-- SECTION:DESCRIPTION:END -->
