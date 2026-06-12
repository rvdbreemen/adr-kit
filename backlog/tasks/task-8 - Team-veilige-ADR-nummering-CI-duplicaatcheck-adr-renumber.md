---
id: TASK-8
title: 'Team-veilige ADR-nummering: CI-duplicaatcheck + adr-renumber'
status: Done
assignee: []
created_date: '2026-06-12 20:06'
updated_date: '2026-06-12 20:41'
labels:
  - tier-1
  - teams
dependencies: []
references:
  - docs/research/2026-06-12-adr-landscape.md
  - bin/adr-lint
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Sequentiële nummering geeft race conditions bij parallelle branches/agents (twee branches claimen ADR-043). Aanpak: (a) CI-check op duplicaat-nummers (uitbreiding adr-lint consistency-gate of aparte check in de adr-lint GitHub Action), plus (b) bin/adr-renumber hulptool die een botsend ADR veilig hernummert inclusief verwijzingen in Related Decisions en supersession-links. Datum-prefix-conventie als opt-in overwogen maar afgewezen: minimaal-invasieve CI-check lost het echte pijnpunt op waar het zichtbaar wordt (merge).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 adr-lint (of CI Action) faalt op duplicate ADR-nummers met duidelijke melding
- [ ] #2 bin/adr-renumber hernummert één ADR en werkt alle kruisverwijzingen bij (Related Decisions, Superseded by)
- [ ] #3 Tests voor merge-conflictscenario: twee ADRs met zelfde nummer
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shipped in v0.23.0. Duplicate detection pre-existed in adr-lint consistency gate (always_strict); added post-merge regression tests and actionable message naming all colliding files. New bin/adr-renumber: dry-run-by-default, whole-token cross-reference rewrite, next-free = max+1, ambiguous source refuses. 9 tests.
<!-- SECTION:FINAL_SUMMARY:END -->
