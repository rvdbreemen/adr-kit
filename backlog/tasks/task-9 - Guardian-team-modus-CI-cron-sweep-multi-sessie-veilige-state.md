---
id: TASK-9
title: 'Guardian team-modus: CI-cron sweep + multi-sessie-veilige state'
status: Done
assignee: []
created_date: '2026-06-12 20:06'
updated_date: '2026-06-12 20:41'
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

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shipped in v0.22.0. Weekly cheap-tier CI sweep (.github/workflows/adr-guardian-audit.yml + downstream template) with single tracking issue create/update/close lifecycle; atomic state writes (per-process temp + os.replace), corrupt-state tolerance, best-effort non-blocking lock. SKILL.md Team mode section. 13 tests.
<!-- SECTION:FINAL_SUMMARY:END -->
