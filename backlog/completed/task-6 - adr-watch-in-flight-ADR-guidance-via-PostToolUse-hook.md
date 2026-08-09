---
id: TASK-6
title: 'adr-watch: in-flight ADR-guidance via PostToolUse hook'
status: Done
assignee: []
created_date: '2026-06-12 20:06'
updated_date: '2026-06-12 20:41'
labels:
  - tier-1
  - agent-guardrails
dependencies: []
references:
  - docs/research/2026-06-12-adr-landscape.md
  - bin/adr-context
  - bin/adr-judge
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
PostToolUse-hook op Edit/Write die bin/adr-context draait op het gewijzigde pad plus een lichte pattern-match tegen Enforcement-blocks van Accepted ADRs. Bij hit een compacte reminder als hook-output (bijv. "raakt ADR-007: geen directe DB-calls buiten repository-laag"). Deterministisch, key-vrij, doel <100ms. Per-sessie cache/cooldown tegen herhaal-nudges (zelfde patroon als Guardian). Dicht het guidance-gat tussen SessionStart-context en pre-commit-enforcement — kernwens uit landscape-research 2026-06-12. Hergebruik: bin/adr-context ranking, bin/adr-judge rule-parser.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Hook vuurt op Edit/Write en rapporteert relevante Accepted ADRs voor het gewijzigde pad
- [ ] #2 Geen LLM-call, geen API-key; runtime <100ms op repo met 50 ADRs
- [ ] #3 Cooldown voorkomt dubbele nudge voor zelfde ADR+file binnen een sessie
- [ ] #4 Werkt als plugin-level hook en degradeert stil buiten Claude Code
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shipped in v0.24.0. bin/adr-watch + plugin-level PostToolUse hook (Edit|MultiEdit|Write) via run-hook.cmd; path_glob + keyword matching, max 3 nudges, 4h ADR+file cooldown in shared state file, watch config block in schema. 23 tests. ~28ms warm for 50 ADRs.
<!-- SECTION:FINAL_SUMMARY:END -->
