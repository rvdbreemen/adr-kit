---
id: TASK-7
title: 'adr-mcp: dunne Python-stdio MCP-server rond bestaande CLI''s'
status: To Do
assignee: []
created_date: '2026-06-12 20:06'
labels:
  - tier-1
  - adoptie
  - mcp
dependencies: []
references:
  - docs/research/2026-06-12-adr-landscape.md
  - bin/adr-context
  - bin/adr-judge
  - bin/adr-status
  - bin/adr-quality
  - bin/adr-suggest
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
bin/adr-mcp: wrap bestaande CLI's als 4-6 MCP-tools: adr_context(query), adr_judge(diff), adr_status(), adr_quality(id), adr_suggest(diff). Python stdio — geen nieuwe runtime (non-goal gerespecteerd); mcp-package optioneel, anders handmatige JSON-RPC over stdio (~200 LOC). Waarde: Cursor/Windsurf/Copilot krijgen dezelfde guardrails zonder skills-formaat; subagents kunnen tools key-vrij aanroepen. Bewust dun houden — contrast met mcp-adr-analysis-server (73 tools, 29 stars) is een feature. Vereist ROADMAP-update: MCP was impliciet buiten scope.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Server start via stdio en exposeert max 6 tools die de bestaande CLI-logica hergebruiken
- [ ] #2 Geen verplichte dependencies buiten Python stdlib (mcp-package optioneel)
- [ ] #3 Getest met Claude Code en minimaal één andere client (Cursor of Cline)
- [ ] #4 README-sectie met configuratievoorbeeld per client
<!-- AC:END -->
