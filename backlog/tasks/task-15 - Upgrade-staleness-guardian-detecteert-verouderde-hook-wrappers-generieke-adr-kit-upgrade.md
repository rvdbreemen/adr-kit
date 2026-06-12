---
id: TASK-15
title: >-
  Upgrade-staleness: guardian detecteert verouderde hook-wrappers + generieke
  /adr-kit:upgrade
status: To Do
assignee: []
created_date: '2026-06-12 20:49'
labels:
  - tier-2
  - lifecycle
  - adoptie
dependencies: []
references:
  - bin/adr-guardian
  - skills/upgrade/SKILL.md
  - skills/install-hooks/SKILL.md
  - templates/githooks/pre-commit
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Plugin-level hooks verversen automatisch bij plugin-update, maar gekopieerde artefacten bevriezen: project-scoped hook-entry in .claude/settings.json, git pre-commit wrapper (.githooks/pre-commit), GitHub Action pins (@vX), pre-commit framework rev. Niets detecteert dat een gekopieerde wrapper achterloopt op de geïnstalleerde plugin. Fix: (a) guardian cheap tier vergelijkt gekopieerde artefacten met nieuwste cache-versie en nudge't "hook wrapper is from v0.18, plugin is v0.26: run /adr-kit:install-hooks"; (b) /adr-kit:upgrade generaliseren van eenmalige v0.11-naar-v0.12-migratie naar generieke refresh-driver voor alle geïnstalleerde artefacten. Bron: upgrade-kanalenanalyse door task-6-agent (zie diens eindrapport, 2026-06-12).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Guardian cheap tier meldt versie-lag tussen gekopieerde wrappers en geïnstalleerde plugin
- [ ] #2 /adr-kit:upgrade ververst alle gekopieerde artefacten idempotent
- [ ] #3 Geen false positives wanneer alles up-to-date is
<!-- AC:END -->
