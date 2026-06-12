---
id: TASK-8
title: 'Team-veilige ADR-nummering: CI-duplicaatcheck + adr-renumber'
status: To Do
assignee: []
created_date: '2026-06-12 20:06'
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
