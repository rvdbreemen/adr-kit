---
id: TASK-10
title: Supersession-workflow verharden + audit trail judge-overrides
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
  - backlog/tasks/task-3 - Release-v0.20.0-adr-kit-related-adr-kit-supersede.md
  - bin/adr-judge
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Aanvulling op geplande /adr-kit:supersede (task-3): supersession-ambiguïteit onder multi-agent-belasting oplossen en een audit trail toevoegen voor judge-overrides. Wanneer een commit doorgaat ondanks (of na aanpassing van) een Enforcement-violation, wordt dat vastgelegd in de Status History van het betrokken ADR (changed_via: adr-judge override, reason verplicht). Geeft teams traceerbaarheid: wie heeft welke guardrail wanneer omzeild en waarom.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Override van een judge-FAIL vereist expliciete reden en landt in Status History van het ADR
- [ ] #2 Supersede-flow detecteert en blokkeert dubbele gelijktijdige supersession van hetzelfde ADR
- [ ] #3 adr-lint audit-gate valideert override-entries
<!-- AC:END -->
