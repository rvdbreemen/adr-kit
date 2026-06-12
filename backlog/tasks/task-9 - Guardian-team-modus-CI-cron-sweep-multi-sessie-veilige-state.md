---
id: TASK-9
title: 'Guardian team-modus: CI-cron sweep + multi-sessie-veilige state'
status: To Do
assignee: []
created_date: '2026-06-12 20:06'
labels:
  - tier-2
  - lifecycle
  - teams
dependencies: []
references:
  - docs/research/2026-06-12-adr-landscape.md
  - bin/adr-guardian
  - .github/workflows/adr-retire-audit.yml
  - docs/adr/ADR-002-adr-guardian-session-start-staleness-detector.md
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Guardian-state (.adr-kit-state.json) is per-machine en niet multi-sessie-veilig; teamleden zien elkaars stamps niet. Aanpak: (a) wekelijkse CI-cron die de volledige cheap-tier sweep draait (drift + retire + lint) en een issue opent bij findings — uitbreiding van bestaande .github/workflows/adr-retire-audit.yml; (b) file-locking of atomic-write voor de lokale state file bij parallelle Claude Code-sessies. LLM-tier blijft opt-in en lokaal (ADR-001 posture).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 CI-workflow draait cheap-tier sweep wekelijks en opent/actualiseert één issue bij findings
- [ ] #2 State file schrijfveilig bij twee gelijktijdige sessies (atomic write of lock)
- [ ] #3 Documentatie: wanneer SessionStart-nudge vs CI-cron gebruiken
<!-- AC:END -->
