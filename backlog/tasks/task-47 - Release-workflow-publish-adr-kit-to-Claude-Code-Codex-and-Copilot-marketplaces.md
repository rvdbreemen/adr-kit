---
id: TASK-47
title: >-
  Release workflow: publish adr-kit to Claude Code, Codex and Copilot
  marketplaces
status: In Progress
assignee:
  - '@claude'
created_date: '2026-07-22 18:36'
updated_date: '2026-07-22 18:49'
labels:
  - release
  - tooling
dependencies: []
priority: high
ordinal: 48500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The three coding-agent marketplaces resolve from the public rvdbreemen/adr-kit repo (Claude .claude-plugin/marketplace.json, Codex .agents/plugins/marketplace.json, Copilot .github/plugin/marketplace.json). 0.37.0 shipped to main but no documented/automated release process ties version consistency, adapter drift-check, gates, tag, GitHub Release and the per-machine local install together, so the local prepared marketplace lagged at 0.36.0. Add a RELEASING runbook + a tag-triggered GitHub Actions release workflow that guarantees the publish is consistent across all three clients on the public repo.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 RELEASING.md documents the three-client marketplace model (git-source vs local prepared-dir) and the ordered release steps
- [ ] #2 release.yml triggers on v* tag push and fails unless version is identical across the 3 plugin.json, 2 versioned marketplace.json, git tag and CHANGELOG heading
- [ ] #3 Workflow runs build-client-adapters --check, adr-lint --strict, adr-index --check and pytest
- [ ] #4 Workflow creates a GitHub Release from the CHANGELOG section
- [ ] #5 Local install-agent-envs.py --clients all step is documented as the per-machine prepared-dir publish
- [ ] #6 ADR authored (Proposed) for the marketplace release/publish decision
<!-- AC:END -->
