---
id: TASK-11
title: Aanmelden bij adr.github.io/adr-tooling catalogus
status: Done
assignee: []
created_date: '2026-06-12 20:06'
updated_date: '2026-06-12 22:44'
labels:
  - tier-3
  - adoptie
dependencies: []
references:
  - docs/research/2026-06-12-adr-landscape.md
  - 'https://adr.github.io/adr-tooling/'
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
De canonieke ADR-tooling-catalogus (laatst bijgewerkt 2026-05-11) bevat nul AI-agent-tools — geverifieerd in landscape-research 2026-06-12. PR naar adr/adr.github.io om adr-kit op te nemen; adr-kit wordt daarmee de eerste AI-agent-native tool in de catalogus. Quick win voor vindbaarheid en de v1.0-adoptiecriteria (5 externe installaties). Categorie-keuze: catalogus is template-georganiseerd, dus aanmelding wint aan kracht na v0.22 (MADR/Nygard-compat, task-5).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 PR ingediend bij adr/adr.github.io met correcte categorisering
- [ ] #2 README-badge of -vermelding zodra gemerged
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
PR submitted: https://github.com/adr/adr.github.io/pull/104 (adds adr-kit to the Any template section of _posts/2024-10-28-adr-tooling.md, alphabetically after ADG; entry covers agent enforcement, drift/staleness detection, context ranking, MCP server, MADR/Nygard import). Prerequisites completed first: 31 commits + 11 tags pushed to origin, 11 GitHub Releases created (v0.21.0 through v0.30.1). AC#2 (README badge/mention) pending until the PR merges; adr-kit would be the first AI-agent tool in the catalog.
<!-- SECTION:FINAL_SUMMARY:END -->
