---
id: TASK-148
title: Consolidate the four setup entry points into one
status: To Do
assignee: []
created_date: '2026-08-09 10:35'
labels: []
dependencies:
  - TASK-144
references:
  - docs/plans/kiss-simplification-plan.md
priority: medium
ordinal: 119500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Step 4 of docs/plans/kiss-simplification-plan.md. Requires TASK-144 (the R16 dialogue must be gone first). R19 asks for one deterministic, repeatable install act; today init, setup, install-hooks and upgrade are four user-facing entry points. Collapse to one /adr-kit:setup with modes (fresh install, adopt existing ADRs, upgrade, hooks-only), preserving the R19 guarantees: deterministic, idempotent, leaves what the kit does not own untouched, works on Windows/macOS/Linux. Update skills across all three clients.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 One setup skill documented per client; the retired entry points either alias to it or are removed from skills and docs
- [ ] #2 Fresh install and re-run on an installed repo both succeed and are idempotent
- [ ] #3 python -m pytest -q passes; build-client-adapters.py --check reports changed=0
<!-- AC:END -->
