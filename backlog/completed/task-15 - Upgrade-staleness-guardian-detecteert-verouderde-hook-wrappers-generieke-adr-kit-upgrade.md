---
id: TASK-15
title: >-
  Upgrade-staleness: guardian detecteert verouderde hook-wrappers + generieke
  /adr-kit:upgrade
status: Done
assignee: []
created_date: '2026-06-12 20:49'
updated_date: '2026-06-12 21:14'
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
- [x] #1 Guardian cheap tier meldt versie-lag tussen gekopieerde wrappers en geïnstalleerde plugin
- [x] #2 /adr-kit:upgrade ververst alle gekopieerde artefacten idempotent
- [x] #3 Geen false positives wanneer alles up-to-date is
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shipped in v0.27.0. Version stamps in pre-commit wrapper template and settings guardian-entry template, kept in lockstep by bump-version (with lockstep guard tests). adr-guardian check compares stamps vs installed plugin via pure file reads and nudges /adr-kit:upgrade; stale wrapper counts as a due item even when sweep tiers are fresh. New adr-guardian artifacts subcommand. /adr-kit:upgrade generalized into idempotent artifact refresh driver (Step 0); legacy v0.11-v0.12 path retained. No false positives: fresh stamps silent, foreign hooks ignored, unstamped settings entries never stale. 17 tests.
<!-- SECTION:FINAL_SUMMARY:END -->
