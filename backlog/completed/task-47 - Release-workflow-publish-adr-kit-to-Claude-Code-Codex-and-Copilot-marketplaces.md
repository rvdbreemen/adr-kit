---
id: TASK-47
title: >-
  Release workflow: publish adr-kit to Claude Code, Codex and Copilot
  marketplaces
status: Done
assignee:
  - '@claude'
created_date: '2026-07-22 18:36'
updated_date: '2026-07-22 19:54'
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
- [x] #1 RELEASING.md documents the three-client marketplace model (git-source vs local prepared-dir) and the ordered release steps
- [x] #2 release.yml triggers on v* tag push and fails unless version is identical across the 3 plugin.json, 2 versioned marketplace.json, git tag and CHANGELOG heading
- [x] #3 Workflow runs build-client-adapters --check, adr-lint --strict, adr-index --check and pytest
- [x] #4 Workflow creates a GitHub Release from the CHANGELOG section
- [x] #5 Local install-agent-envs.py --clients all step is documented as the per-machine prepared-dir publish
- [x] #6 ADR authored (Proposed) for the marketplace release/publish decision
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added a documented, enforced release process for the three coding-agent marketplaces. docs/RELEASING.md is the runbook (public repo is the marketplace; git-source vs prepared-directory; per-machine install). scripts/check-release-version.py gates six version sites against the tag. .github/workflows/release-publish.yml runs the gates on a v* tag and cuts the GitHub Release from the CHANGELOG. ADR-012 records the decision (Accepted). Proven end to end on the 0.38.0 release: workflow succeeded, Release published.
<!-- SECTION:FINAL_SUMMARY:END -->
