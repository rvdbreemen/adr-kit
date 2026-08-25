---
id: TASK-183
title: Release adr-kit v0.53.0
status: In Progress
assignee: []
created_date: '2026-08-19 22:03'
labels:
  - release
dependencies: []
priority: medium
type: task
ordinal: 27000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Release v0.53.0 per docs/RELEASING.md and ADR-012. Carries ADR-040 (Accepted): MCP server grows from five to seven tools (adr_lint, adr_related), agent guide rewritten for autonomous operation, doctor/installer smoke on the seven-tool contract. Depends on PR #115 (feat/mcp-lint-related into dev). Minor bump: new user-facing capability, no breaking changes.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 PR #115 merged into dev
- [ ] #2 bump-version.py 0.53.0 + adapters regenerated; no hand-edited versions
- [ ] #3 CHANGELOG 0.53.0 section at release-note quality; README reflects seven MCP tools
- [ ] #4 All local gates pass (check-release-version, adapters --check, adr-lint --strict, adr-index --check, full pytest)
- [ ] #5 Release PR into main green; maintainer merges
- [ ] #6 Tag v0.53.0 pushed after maintainer confirmation; release-publish.yml green
- [ ] #7 Merge-back PR into dev opened
- [ ] #8 Local prepared-directory marketplaces re-registered for all three clients
<!-- AC:END -->
