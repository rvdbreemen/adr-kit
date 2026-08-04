---
id: TASK-118
title: Reconcile the pr-create runner budget with ADR-015's 2000 ms ceiling
status: To Do
assignee: []
created_date: '2026-08-04 05:24'
labels:
  - adr
  - hooks
  - consistency
dependencies: []
priority: high
ordinal: 97500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ADR-015 fixes a 2000 ms ceiling for hook latency. `hooks/manifest.json` declares `runner_timeout_sec: 5` for `pr-create`, which is 5000 ms and was never amended against that ceiling.

Both numbers are defensible on their own: the guard genuinely needs more than two seconds to run git plus a judge, and ADR-015 genuinely wants hooks to stay out of the user's way. What is not defensible is having both on record with nothing forcing them to agree.

Decide which one moves. Either amend ADR-015 (a new ADR, since it is Accepted) to carve out the pull-request moment as a deliberately slower, user-initiated event, or bring `pr-create` back under 2000 ms and accept that the judge cannot run an LLM pass there.

Evidence: `docs/adr/ADR-015-*.md`, `hooks/manifest.json` (`pr-create` entry), CHANGELOG 0.44.1 "The pull-request guard was killed after one second".
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The declared pr-create budget and the ADR-governed latency ceiling agree, or the divergence is recorded in an accepted ADR that names pr-create explicitly
- [ ] #2 A test or gate fails when the two drift apart again
<!-- AC:END -->
